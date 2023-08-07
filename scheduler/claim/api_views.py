from django.http import HttpRequest, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from django.db.models import Q
from datetime import time, timedelta, datetime
from .utils import *
from django.views.decorators.http import require_http_methods
import json

POST_ERR_MESSAGE = "Only post requests are allowed!"
GET_ERR_MESSAGE = "Only get requests are allowed!"

## api 
@login_required
@require_http_methods(["GET"])
def get_meetings(request: HttpRequest) -> JsonResponse:
    response_data = {}
    
    term = request.GET.get('term')
    term = Term.objects.get(pk=term)
    professor = Professor.objects.get(user=request.user)
    meetings = professor.meetings.filter(section__term=term)

    data = {
        "professor": professor,
        "term": term,
        "meetings": meetings,
        "unscheduled_sections": professor.sections.filter(meetings__isnull=True).all(),
    }

    get_meetings_template = render(request, "get_meetings.html", data).content.decode()


    response_data['ok'] = True
    response_data['get_meetings_template'] = get_meetings_template

    return JsonResponse(response_data)


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
    total_seconds_added = 0 if total_seconds_added < timedelta(seconds=0) else total_seconds_added

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
def get_meeting_details(request: HttpRequest) -> JsonResponse:
    response_data = {}
    
    meeting = request.GET.get('meeting')
    in_edit_mode = request.GET.get('in_edit_mode') == 'true'
    meeting: Meeting = Meeting.objects.get(pk=meeting)

    is_shared_section = meeting.section.meetings.exclude(professor=meeting.section.primary_professor).exists()

    data = {
        'section': meeting.section,
        'meeting': meeting,
        'is_shared_section': is_shared_section,
        'in_edit_mode': in_edit_mode 
    }
    meeting_details_template = render(request, 'meeting_details.html', context=data).content.decode()

    response_data['ok'] = True
    response_data['meeting_details_html'] = meeting_details_template

    return JsonResponse(response_data)

@login_required
@require_http_methods(["GET"])
def course_search(request: HttpRequest) -> JsonResponse:
    response_data = {}
    
    department = request.GET.get('department')
    subject = request.GET.get('subject')
    query = request.GET.get('search')
    count = int(request.GET.get('count'))
    term = request.GET.get('term')

    courses_qs = Course.objects.filter(sections__term=term).distinct()
    if department != 'any': courses_qs = courses_qs.filter(subject__department=department)
    if subject != 'any': courses_qs = courses_qs.filter(subject=subject)
    if query:
        items_q = Q()
        for item in query.split():
            item = item.replace('&nbsp;', '') # remove white space
            items_q &= Q(code__icontains=item) | Q(title__icontains=item)
        courses_qs = courses_qs.filter(items_q)

    courses = []
    bottom: bool = courses_qs.all().count() <= count
    for course in courses_qs.all().order_by('title')[:count]:
        courses.append({'pk': course.pk, 'title': course.title, 'code': course.code, 'subject': course.subject.code,})
    
    response_data['ok'] = True
    response_data['bottom'] = bottom
    response_data['courses'] = courses

    return JsonResponse(response_data)
    
@login_required
@require_http_methods(["POST"])
def section_search(request: HttpRequest) -> JsonResponse:
    response_data = {}

    data: dict = json.loads(request.body)

    term = data.get('term')
    courses = data.get('courses')
    if not courses:
        response_data['ok'] = True
        response_data['section_html'] = ''
        return JsonResponse(response_data)
    
    exclusion_times = data.get('exclusion_times', [])
    does_fit = data.get('does_fit', False)
    is_available = data.get('is_available', False)

    sort_column = data.get('sort_column')
    sort_type = data.get('sort_type')
    start_slice = data.get('start_slice')
    end_slice = data.get('end_slice')

    professor = Professor.objects.get(user=request.user)
    section_qs = Section.objects.filter(term=term, course__in=courses)

    if is_available:
        section_qs = section_qs.filter(meetings__professor__isnull=True)


    if exclusion_times:
        exclusion_query = Q()
        for exclusion_time in exclusion_times:
            day = exclusion_time['day']
            start_time = time.fromisoformat(exclusion_time['start_time'])
            end_time = time.fromisoformat(exclusion_time['end_time'])

            exclusion_query |= Q(meetings__time_block__day=day,
                                meetings__time_block__start_end_time__start__lte=end_time,
                                meetings__time_block__start_end_time__end__gte=start_time)
        section_qs = section_qs.exclude(exclusion_query)

    # Exclude all meetings that overlap with professor meetings
    if does_fit:
        #TODO make it also take into consideration if the start and end date
        professor_meetings = professor.meetings.filter(section__term=term)
        exclusion_query = Q()
        for meeting in professor_meetings.all():
            exclusion_query |= Q(meetings__time_block__day=meeting.time_block.day,
                                meetings__time_block__start_end_time__start__lte=meeting.time_block.start_end_time.end,
                                meetings__time_block__start_end_time__end__gte=meeting.time_block.start_end_time.start)

        section_qs = section_qs.exclude(exclusion_query)
    
    section_qs = Section.sort_sections(section_qs=section_qs, sort_column=sort_column, sort_type=sort_type)
    original_length = len(section_qs)
    section_qs = section_qs[start_slice:end_slice]

    sections_template = render(request, "sections.html", {
        "sections": section_qs,
        "claim": True,
        "sort_column": sort_column,
        "sort_type": sort_type,
        "sort_column": sort_column,
        "sort_type": sort_type,
        "start_slice": start_slice,
        "end_slice": min(end_slice, original_length),
        "original_length": original_length  
    }).content.decode()

    response_data['ok'] = True
    response_data['section_html'] = sections_template
    return JsonResponse(response_data)

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

    edit_rows: list[EditMeeting] = []
    for row in request.POST.get('edit_rows'):
        edit_meeting = EditMeeting.create(row)
        edit_rows.append(edit_meeting)

    section: Section = request.POST.get('section')
    new_edit_rows = section.get_recommendations(edit_rows)

    edit_rows_html = []
    for row in new_edit_rows:
        data = {
            'start_time': row.start_time,
            'end_time': row.end_time,
            'day': row.day,
            'counter': row.counter,
            'buildings': Building.objects.all(),
            'building': row.building,
            'meeting': row.meeting,
            'room': row.room,
        }

        edit_rows_html.append(render(request, 'edit_meeting_row.html', context=data).content.decode())
    
    response_data['ok'] = True
    response_data['edit_rows_html'] = edit_rows_html

    return JsonResponse(response_data)


    