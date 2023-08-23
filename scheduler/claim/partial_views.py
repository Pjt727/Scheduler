from django.http import HttpRequest, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import *
from request.models import *
from django.db.models import Q
from datetime import time, timedelta, datetime
from .utils import *
from django.views.decorators.http import require_http_methods
import json


@login_required
@require_http_methods(["GET"])
def get_course_search(request: HttpRequest) -> HttpResponse:
    term_pk = request.GET.get("term")
    term = Term.objects.get(pk=term_pk)

    department_pk = request.GET.get("department")
    subject_pk = request.GET.get("subject")
    course_query = request.GET.get("course_query")

    # TODO Maybe remedy sort of glitch since we do not know when input was just changed this code cannot be fixed as is
    #   problem/feature: changing department to any wont work if subject is not any since it will repopulate the subject's department
    subjects = Subject.objects.filter(courses__sections__term=term_pk).distinct()
    if subject_pk == "any" and department_pk == "any":
        department = None
        subject = None
    elif department_pk == "any":
        subject = Subject.objects.get(pk=subject_pk)
        department = subject.department
        department_pk = department.pk
    elif subject_pk == "any":
        department = Department.objects.get(pk=department_pk)
        subject = None
    else:
        subject = Subject.objects.get(pk=subject_pk)
        department = Department.objects.get(pk=department_pk)

    if department is not None:
        subjects = subjects.filter(department=department)

    courses, has_results = Course.search(course_query, term_pk, department_pk, subject_pk)
    courses = courses.order_by('title')
    # TODO implement if can be made faster
    # courses = Course.sort_with_prof(courses, professor=request.user.professor)

    context = {
        'terms': Term.objects.all(),
        'selected_term': term,
        'departments': Department.objects.all(),
        'selected_department': department,
        'subjects': subjects.distinct().all(),
        'selected_subject': subject,
        'course_query': course_query,
        'courses': courses.all()[:Course.SEARCH_INTERVAL],

        'has_results': has_results
    }

    return render(request, 'course_search.html', context=context)

@login_required
@require_http_methods(["GET"])
def get_course_options(request: HttpRequest, offset: int) -> HttpResponse:
    term_pk = request.GET.get("term")
    term = Term.objects.get(pk=term_pk)

    department_pk = request.GET.get("department")
    subject_pk = request.GET.get("subject")
    course_query = request.GET.get("course_query")

    courses, has_results = Course.search(course_query, term, department_pk, subject_pk)
    courses = courses.order_by('title')
    # TODO implement if can be made faster
    # courses = Course.sort_with_prof(courses, professor=request.user.professor)

    context = {
        'courses': courses.all()[offset : offset+Course.SEARCH_INTERVAL],
        'offset': offset,
        'next_offset': offset + Course.SEARCH_INTERVAL,
        'has_results': has_results
    }

    return render(request, 'course_options.html', context=context)

@login_required
@require_http_methods(["GET"])
def add_course_pill(request: HttpRequest, course: int) -> HttpResponse:
    
    courses = request.GET.getlist("course", [])

    if str(course) in courses:
        return render(request, 'course_pill.html')

    course = Course.objects.get(pk=course)

    context = {
        "course": course
    }

    return render(request, 'course_pill.html', context=context)


@login_required
@require_http_methods(["GET"])
def get_meetings(request: HttpRequest) -> HttpResponse:
    
    term = request.GET.get('term')
    term = Term.objects.get(pk=term)
    professor = Professor.objects.get(user=request.user)
    meetings = professor.meetings.filter(section__term=term)

    data = {
        "professor": professor,
        "title": term,
        "meetings": meetings,
        "unscheduled_sections": professor.sections.filter(meetings__isnull=True).all(),
    }

    return render(request, "get_meetings.html", context=data)




@login_required
@require_http_methods(["GET"])
def get_meetings_edit_section(request: HttpRequest) -> JsonResponse:
    response_data = {}

    is_input: bool = request.GET.get('is_input') == 'true'

    sections = request.GET.get('sections').split(',')
    primary_section = request.GET.get('primary_section')
    
    if is_input:
        try:
            sections = Section.objects.filter(pk__in=sections)
            primary_section: Section = sections.get(pk=primary_section)
        except Section.DoesNotExist:
            response_data['ok'] = False
            response_data['error'] = "Section data not found"

        if sections.exclude(term=primary_section.term):
            response_data['ok'] = False
            response_data['error'] = "To edit in the same group sections must be in the same term"
    else:
        primary_section = Section.objects.get(pk=sections[0])

    room = request.GET.get('room')
    building = request.GET.get('building')
    if building is not None:
        building = Building.objects.get(pk=building)
    
    meetings = Meeting.objects.none()

    if primary_section.primary_professor:
        meetings |= primary_section.primary_professor.meetings.filter(section__term=primary_section.term)
    
    if room and (room != 'any'):
        room: Room = Room.objects.get(pk=room)
        meetings |= Meeting.objects.filter(room=room, section__term=primary_section.term).exclude(time_block__in=meetings.values('time_block'))

    meetings = meetings.exclude(section__in=sections)
    meetings = meetings.distinct()

    if not is_input:
        data = {
            "meetings": meetings,
            "term": primary_section.term,
        }
        get_meetings_template = render(request, "get_meetings.html", data).content.decode()

        response_data['ok'] = True
        response_data['get_meetings_template'] = get_meetings_template

        return JsonResponse(response_data)

    # Timing is complicated...
    total_seconds_added = 0

    open_time_slots = []
    total_seconds = int(request.GET.get('total_seconds'))
    total_seconds = timedelta(seconds=total_seconds)
    total_seconds_added = total_seconds - timedelta(hours=1, minutes=15)
    total_seconds_added = timedelta() if total_seconds_added < timedelta() else total_seconds_added

    overlaps_meeting = Q()
    for meeting in meetings.all():
        start_time_d = meeting.time_block.start_end_time.start_delta() - total_seconds_added
        start_time = time(hour=start_time_d.seconds // 3600, minute=(start_time_d.seconds % 3600) // 60)

        overlaps_meeting |= Q(day=meeting.time_block.day,
            start_end_time__start__lte=meeting.time_block.start_end_time.end,
            start_end_time__end__gte=start_time)

    open_time_block_candidates =  TimeBlock.objects.filter(number__isnull=False).exclude(overlaps_meeting).filter().all()

    for candidate in open_time_block_candidates:
        start_time: time = candidate.start_end_time.start
        start_time_d = timedelta(hours=start_time.hour, minutes=start_time.minute) + total_seconds
        end_time_to_exist = time(hour=start_time_d.seconds // 3600, minute=(start_time_d.seconds % 3600 ) // 60)
        tm = TimeBlock.objects.filter(number__isnull=False)
        
        tm = tm.filter(day=candidate.day, start_end_time__end=end_time_to_exist) 


        if not tm.exists():
            continue

        enforce_department_constraints = request.GET.get('enforce_department_constraints') == 'true'
        exceeds_department_allocation = False
        if enforce_department_constraints:
            exceeds_department_allocation = will_exceed_department_allocation(
                start_time=start_time,
                end_time=end_time_to_exist,
                day=candidate.day,
                department=primary_section.course.subject.department,
                term=primary_section.term
            )


        if room == 'any':
            open_rooms = building.get_available_rooms(
                start_time=start_time,
                end_time=end_time_to_exist,
                day=candidate.day,
                term=primary_section.term,
                include_general=exceeds_department_allocation
            )
            if not open_rooms.exists(): continue
        else:
            if exceeds_department_allocation and room.is_general_purpose: continue


        open_time_slots.append({
            'start': start_time.strftime('%H:%M'),
            'end': end_time_to_exist.strftime('%H:%M'),
            'day': candidate.day,
            'time_block': candidate,
            'number': tm.first().number
        })
        

    data = {
        "meetings": meetings,
        "term": primary_section.term,
        "open_time_blocks": open_time_slots
    }
    get_meetings_template = render(request, "get_meetings.html", data).content.decode()

    response_data['ok'] = True
    response_data['get_meetings_template'] = get_meetings_template

    return JsonResponse(response_data)

@login_required
@require_http_methods(["GET"])
def get_edit_section(request: HttpRequest) -> JsonResponse:
    response_data = {}
    section = request.GET.get('section')
    section = Section.objects.get(pk=section)
    response_data['ok'] = True

    data = {
        'section': section,
        "days": Day.CODE_TO_VERBOSE.items(), 
        "buildings": Building.objects.all()
    }
    response_data['edit_section_html'] = render(request, 'section_edit.html', context=data).content.decode()

    return JsonResponse(response_data)


@login_required
@require_http_methods(["GET"])
def get_rooms_edit_section(request: HttpRequest) -> JsonResponse:
    response_data = {}
    
    building = request.GET.get('building')
    building = Building.objects.get(pk=building)
    rooms = building.rooms.distinct().values_list('pk', 'number')

    response_data['ok'] = True
    response_data['rooms'] = tuple(rooms)
    
    return JsonResponse(response_data)
    
    
@login_required
@require_http_methods(["GET"])
def get_meeting_details(request: HttpRequest) -> HttpResponse:
    meeting = request.GET.get('meeting')
    in_edit_mode = request.GET.get('inEditMode') == 'true'
    meeting: Meeting = Meeting.objects.get(pk=meeting)

    is_shared_section = meeting.section.meetings.exclude(professor=meeting.section.primary_professor).exists()

    data = {
        'section': meeting.section,
        'meeting': meeting,
        'is_shared_section': is_shared_section,
        'in_edit_mode': in_edit_mode 
    }
    return render(request, 'meeting_details.html', context=data)


    
@login_required
@require_http_methods(["GET"])
def section_search(request: HttpRequest) -> HttpResponse:

    courses = request.GET.getlist("course", [])
    if not isinstance(courses, list):
        courses = [courses]

    term = request.GET.get('term')
    
    # TODO implement
    # exclusion_times = data.get('exclusion_times', [])
    does_fit = request.GET.get('fits', False)
    is_available = request.GET.get('available', False)

    sort_column = request.GET.get('sortColumn')
    sort_type = request.GET.get('sortType')
    start_slice = int(request.GET.get('startSlice', 0))
    end_slice = int(request.GET.get('endSlice', Section.SEARCH_INTERVAL))
    original_length = 0 
    context = {
        "refresh_url": reverse(request.resolver_match.view_name),
        "sections": [],
        "claim": True,
        "sort_column": sort_column,
        "sort_type": sort_type,
        "start_slice": start_slice,
        "end_slice": min(end_slice, original_length),
        "original_length": original_length,
        "search_interval": Section.SEARCH_INTERVAL,
    }

    if not courses:
        return render(request, "sections.html", context=context)

    professor = Professor.objects.get(user=request.user)
    section_qs = Section.objects.filter(term=term, course__in=courses)

    if is_available:
        section_qs = section_qs.filter(meetings__professor__isnull=True)

    # TODO also move implementation
    # if exclusion_times:
    #     exclusion_query = Q()
    #     for exclusion_time in exclusion_times:
    #         day = exclusion_time['day']
    #         start_time = time.fromisoformat(exclusion_time['start_time'])
    #         end_time = time.fromisoformat(exclusion_time['end_time'])

    #         exclusion_query |= Q(meetings__time_block__day=day,
    #                             meetings__time_block__start_end_time__start__lte=end_time,
    #                             meetings__time_block__start_end_time__end__gte=start_time)
    #     section_qs = section_qs.exclude(exclusion_query)

    # Exclude all meetings that overlap with professor meetings

    if does_fit:
        section_qs = section_qs.exclude(professor.section_in_meetings())
    
    section_qs = Section.sort_sections(section_qs=section_qs, sort_column=sort_column, sort_type=sort_type)
    original_length = len(section_qs)
    print(start_slice, end_slice)
    print(original_length)
    sections = section_qs[start_slice:end_slice]
    context["sections"] = sections
    context["end_slice"] = min(end_slice, original_length)
    context["original_length"] = original_length


    return render(request, "sections.html", context=context)


@login_required
@require_http_methods(["GET"])
def submit_claim(request: HttpRequest) -> JsonResponse:
    response_data = {}
    
    data: dict = json.loads(request.body)
    meeting_ids: list[str] = data.get("meetings", [])
    # no selected meetings check
    if not meeting_ids:
        response_data['error'] = "There must be at least one meeting time selected."
        response_data['ok'] = False
        return JsonResponse(response_data)

    meetings: list[Meeting] = []
    # meeting does not exist check
    for id in meeting_ids:
        try:
            meeting = Meeting.objects.get(pk=id)
        except Meeting.DoesNotExist:
            response_data['error'] = "Could not find one of those meetings. (Try again)"
            response_data['ok'] = False
            return JsonResponse(response_data)
        meetings.append(meeting)
    
    # meeting is already taken check
    if any([meeting.professor != None for meeting in meetings]):
            response_data['error'] = "A professor has already claimed one of those meeting(s)."
            response_data['ok'] = False
            return JsonResponse(response_data)

    professor: Professor = Professor.objects.get(user=request.user)
    # meeting does not fit in schedule check
    for meeting in meetings:
        for prof_meeting in professor.meetings.filter(section__term=meeting.section.term, time_block__day=meeting.time_block.day):
            # TODO account for 
            meeting_start = meeting.time_block.start_end_time.start
            prof_meeting_end = prof_meeting.time_block.start_end_time.end

            meeting_end = meeting.time_block.start_end_time.end
            prof_meeting_start = prof_meeting.time_block.start_end_time.start
            if meeting_start <= prof_meeting_end and meeting_end >= prof_meeting_start:
                response_data['error'] = f"Meeting {meeting} interferes with your meeting {prof_meeting}."
                response_data['ok'] = False
                return JsonResponse(response_data)

    # change the meetings' professor
    for meeting in meetings:
        meeting.professor = professor
        meeting.save()

    response_data['success_message'] = "Successfully claimed all meetings."
    response_data['ok'] = True
    return JsonResponse(response_data)


@login_required
@require_http_methods(["POST"])
def add_rows(request: HttpRequest) -> JsonResponse:
    response_data = {}

    data: dict = json.loads(request.body)
    edit_rows_raw = data.get('edit_rows', [])
    section_pk = data['section']
    section: Section = Section.objects.get(pk=section_pk)
    edit_rows: list[EditMeeting] = []
    for row in edit_rows_raw:
        is_deleted =  row['isDeleted'] == "true"
        edit_meeting = EditMeeting.create(row, is_deleted=is_deleted, primary_professor=section.primary_professor)
        edit_rows.append(edit_meeting)
    section.get_recommendations(edit_rows)

    edit_rows_html = []
    for row in edit_rows:
        data = {
            'start_time': row.start_time,
            'end_time': row.end_time,
            'day': row.day,
            'days': Day.DAY_CHOICES,
            'counter': row.counter,
            'buildings': Building.objects.all(),
            'building': row.building,
            'meeting': row.meeting,
            'room': row.room,
            'section': section,
            'is_deleted': row.is_deleted,
        }

        edit_rows_html.append(render(request, 'row_edit.html', context=data).content.decode())
    
    response_data['ok'] = True
    response_data['edit_rows_html'] = edit_rows_html

    return JsonResponse(response_data)


@login_required
@require_http_methods(["POST"])
def get_warnings(request: HttpRequest) -> JsonResponse:
    response_data = {}

    data: dict = json.loads(request.body)
    section_rows = data.get('section_rows', [])
    section_edit_meetings: list[tuple[Section, list[EditMeeting]]] = []
    section_pks: list[str] = []
    are_changes = False
    for section_pk, edit_rows in section_rows:
        edit_meetings = []
        section_pks.append(section_pk)
        section = Section.objects.get(pk=section_pk)
        for row in edit_rows:
            # TODO add some logic for deleting rows?
            if row['isDeleted'] == "true": continue
            edit_meeting = EditMeeting.create(row)
            if edit_meeting.is_changed(): are_changes = True
            edit_meetings.append(edit_meeting)
        section_edit_meetings.append( (section, edit_meetings) )

    if not are_changes:
        response_data["are_problems"] = True
        response_data["section_problems_html"] = "There are no changes"
        return JsonResponse(response_data)


    are_problems = False
    section_problems: list[tuple[Section, list[tuple[str, str]]]] = []
    for section, edit_meetings in section_edit_meetings:
        problems = section.get_warnings(edit_meetings, section_pks=section_pks)

        if problems: are_problems = True
        section_problems.append( (section, problems,) )

    group_problems = EditMeeting.get_warnings(section_edit_meetings)
    are_problems = are_problems or bool(group_problems)
    response_data["are_problems"] = are_problems
    context = {
        'section_problems': section_problems,
        'group_problems': group_problems
    }
    if are_problems:
        response_data["section_problems_html"] = render(request, 'problem_rows.html', context=context).content.decode()

    return JsonResponse(response_data)


@login_required
@require_http_methods(["POST"])
def submit_section_changes(request: HttpRequest) -> JsonResponse:
    response_data = {}

    
    data: dict = json.loads(request.body)
    section_rows = data.get('section_rows', [])
    section_edit_meetings: list[tuple[Section, list[EditMeeting]]] = []
    section_objects = []
    section_pks: list[str] = []
    made_changes = False
    for section_pk, edit_rows in section_rows:
        edit_meetings = []
        section_pks.append(section_pk)
        section = Section.objects.get(pk=section_pk)
        section_objects.append(section)
        for row in edit_rows:
            # TODO add some logic for deleting rows?
            if row['isDeleted'] == "true": continue
            edit_meeting = EditMeeting.create(row)
            if edit_meeting.is_changed(): made_changes = True
            edit_meetings.append(edit_meeting)
        section_edit_meetings.append( (section, edit_meetings) )
    
    if not made_changes:
        response_data['adding'] = False
        response_data['message'] = "There were no changes made!"

    are_problems = False
    for section, edit_meetings in section_edit_meetings:
        problems = section.get_warnings(edit_meetings, section_pks=section_pks)

        if any(map(lambda p: p[0] == "danger", problems)):
            response_data['adding'] = False
            response_data['message'] = f"{section} has dangerous warnings."
            return JsonResponse(response_data)

    group_problems = EditMeeting.get_warnings(section_edit_meetings)
    are_problems = are_problems or group_problems

    response_data['adding'] = True
    sections = ", ".join(map(lambda s: str(s), section_objects))
    
    update_meeting_message_bundle = EditMeetingMessageBundle(
        status = EditMeetingMessageBundle.REQUESTED,
        sender = request.user.professor
    )
    update_meeting_message_bundle.save()
    edit_request_bundle = EditRequestBundle(
        requester = request.user.professor
    )
    edit_request_bundle.save()
    for section, edit_meetings in section_edit_meetings:
        edit_section_request = EditSectionRequest(
            is_primary = section.pk == section_pks[0],
            section = section,
            bundle=edit_request_bundle,
        )
        edit_section_request.save()
        for edit_meeting in edit_meetings:
            edit_meeting_request = EditMeetingRequest(
                start_time = edit_meeting.start_time,
                end_time = edit_meeting.end_time,
                day = edit_meeting.day,
                building = edit_meeting.building,
                room = edit_meeting.room,
                professor = edit_meeting.professor,
                original = edit_meeting.meeting,
                edit_section = edit_section_request,
            )
            edit_meeting_request.save()
            edit_meeting_request.freeze(bundle=update_meeting_message_bundle)
    response_data['message'] = f"{sections} changes were successfully changed."

    return JsonResponse(response_data)

    
