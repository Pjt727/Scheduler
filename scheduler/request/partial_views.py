from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, QueryDict, HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.transaction import atomic
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views import View
from django.urls import reverse 
from django_htmx.http import HttpResponseClientRedirect
from claim.models import *
from .models import *
from datetime import time
from typing import TypedDict

# TODO OPEN SLOTS CAN SIMPLY HAVE A VIEW INTO THE DIFFERENT SECTIONS THAT ARE CURRENTLY IN IT

class UpdateMeetingsContext(TypedDict):
    title: str
    meetings: QuerySet[Meeting] | None
    edit_meetings: list[EditMeeting] | None
    open_slots: list[TimeSlot] | None
    number_icons: list[NumberIcon]
    in_edit_mode: bool
    building: str | None
    edit_room: str | None

class InputRowContext:
    durations: list[timedelta]
    days: list
    buildings: list[Building]
    time_intervals: list[tuple[timedelta, timedelta]]


def get_update_meeting_context(edit_meetings: list[EditMeeting] | None = None,
                               building: Building | None = None,
                               room: Room | None = None, duration: timedelta | None = None,
                               other_meetings: QuerySet[Meeting] | None = None,
                               open_slots: list[TimeSlot] | None = None) -> UpdateMeetingsContext:
    building_pk = None if building == None else building.pk
    room_pk = None if room == None else room.pk
    if room is not None:
        title = f"Conflicts in {room} with duration {str(duration)[:-3]}"
    elif building is not None:
        title = f"Conflicts in {building} any room with duration {str(duration)[:-3]}"
    else:
        title = f"No conflicts to show! Add meetings to the section."
        open_slots = []

    context: UpdateMeetingsContext = {
        "title": title,
        "meetings": other_meetings,
        "edit_meetings": edit_meetings,
        "building": building_pk, # building is always none if room is none in this case
        "edit_room": room_pk,
        "number_icons": TimeBlock.get_number_icons(),
        "in_edit_mode": True,
        "open_slots": open_slots,
    }
    return context

# Please refactor there is too many redundant if's
def generate_update_meeting_context(data: QueryDict, edit_meetings: list[EditMeeting] | None = None,
                                    edit_meeting: EditMeeting | None = None,
                                    added_section: Section | None = None) -> UpdateMeetingsContext:
    if edit_meetings is None:
        edit_meetings, _ = EditMeeting.create_all(data)
    sections: set[Section] = set()
    section_pks = data.getlist("sectionGrouper") 
    assert section_pks is not None
    for pk in section_pks:
        sections.add(Section.objects.get(pk=pk))
    if added_section is not None:
        sections.add(added_section)
    first_edit_meeting = next(iter(edit_meetings), None)
    first_section_pk = data.get('sectionGrouper')
    first_section = Section.objects.get(pk=first_section_pk)
    term = first_section.term
    if data.get("thisDuration"):
        start_end_time = str(data.get("thisDuration"))
        hours, minutes = start_end_time.split(':')
        total_seconds = int(hours) * (60 * 60)
        total_seconds += int(minutes) * 60
        duration = timedelta(seconds=total_seconds)
    elif edit_meeting is not None:
        duration = edit_meeting.duration
    elif first_edit_meeting is not None:
        duration = first_edit_meeting.duration
    else:
        duration = TimeBlock.ONE_BLOCK


    building = data.get("thisBuilding")
    if building == "any":
        building = Building.recommend(first_section.course, term=term)
    elif building is not None:
        building = Building.objects.get(pk=building)
    elif edit_meeting is not None:
        building = edit_meeting.building
    elif first_edit_meeting is not None:
        building = first_edit_meeting.building
    else:
        building = Building.recommend(first_section.course, term=term)

    room = data.get("thisRoom")
    if room == "any":
        room = None
    elif room is not None:
        room = Room.objects.get(pk=room)
    elif edit_meeting is not None:
        room = edit_meeting.room
    elif first_edit_meeting is not None:
        room = first_edit_meeting.room

    professor = data.get("thisProfessor")
    if professor == "None" or professor == "":
        professor = None
    if professor is not None:
        professor = Professor.objects.get(pk=professor)
    elif edit_meeting is not None:
        professor = edit_meeting.professor
    elif first_edit_meeting is not None:
        professor = first_edit_meeting.professor
    other_meetings = None
    open_slots = None
    conflicting_courses = set(data.getlist('conflicting_course'))
    # TODO change this condition
    if building:
        other_meetings, open_slots = EditMeeting.get_open_slots(
            term=term,
            building=building,
            room=room,
            professor=professor,
            department=first_section.course.subject.department,
            sections_to_exclude=sections,
            conflicting_courses=conflicting_courses,
            duration=duration,
        )
    edit_meetings_or_none = None
    if data.get("thisRefreshEditMeetings") == "true":
        edit_meetings_or_none = edit_meetings
    return get_update_meeting_context(
            edit_meetings=edit_meetings_or_none,
            building=building,
            room=room,
            duration=duration,
            other_meetings=other_meetings,
            open_slots=open_slots)


# TODO look at this code for possibility of editing rows that do not have building
class DisplayRow(View):
    def delete(self, request: HttpRequest) -> HttpResponse:
        data = QueryDict(request.body) # pyright: ignore
        edit_meetings, edit_meeting = EditMeeting.create_all(data)
        display_meeting_context = {
            "edit_meeting": edit_meeting
        }
        edit_meeting.is_deleted = True
        edit_meetings.remove(edit_meeting)
        edit_meetings = list(filter(lambda e: not e.is_deleted, edit_meetings))
        update_meeting_context = generate_update_meeting_context(data, edit_meetings)

        context = display_meeting_context | update_meeting_context

        return render(request, 'display_row.html', context=context)

    def put(self, request: HttpRequest) -> HttpResponse:
        data = QueryDict(request.body) # pyright: ignore
        edit_meetings, edit_meeting = EditMeeting.create_all(data)
        display_meeting_context = {
            "edit_meeting": edit_meeting,
            "days": Day.CODE_TO_VERBOSE.items(), 
            "buildings": Building.objects.all(),
            "durations": TimeBlock.DURATIONS,
        }
        edit_meeting.is_deleted = False
        edit_meetings = list(filter(lambda e: not e.is_deleted, edit_meetings))

        update_meeting_context = generate_update_meeting_context(data, edit_meetings)

        context = display_meeting_context | update_meeting_context

        return render(request, 'input_row.html', context=context)


class InputRow(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        data = QueryDict(request.body) # pyright: ignore
        edit_meetings, edit_meeting = EditMeeting.create_all(data)
        display_meeting_context = {
            "editing_meeting": edit_meeting
        }
        update_meeting_context = generate_update_meeting_context(data, edit_meetings)
        context = update_meeting_context | display_meeting_context
        return render(request, 'input_row.html', context = context | update_meeting_context)



@login_required
@require_http_methods(["GET"])
def update_time_intervals(request: HttpRequest) -> HttpResponse:
    data = request.GET
    day = data.get('day')
    assert day is not None
    duration_input = data.get('duration')
    assert duration_input is not None
    hours, minutes = duration_input.split(':')
    duration = timedelta(hours=int(hours), minutes=int(minutes))
    time_intervals = TimeBlock.get_time_intervals(duration, day)

    current_start_time_input = data.get('startTime')
    assert current_start_time_input is not None
    hour, minute = current_start_time_input.split(':')
    current_start_time = time(hour=int(hour), minute=int(minute))

    context = {
            "time_intervals": time_intervals,
            "start_time": current_start_time,
    }
    response = render(request, 'time_intervals.html', context=context)
    
    return response


@login_required
@require_http_methods(["PUT"])
def update_duration(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body)
    edit_meetings, edit_meeting = EditMeeting.create_all(data)
    
    time_intervals = TimeBlock.get_time_intervals(edit_meeting.duration, edit_meeting.day)
    
    
    start_time_in_interval = any(map(
        lambda i: i[0] == edit_meeting.start_time, time_intervals))
    if start_time_in_interval:
        start_time = edit_meeting.start_time
    else:
        start_time = next(iter(time_intervals))[0]
        edit_meeting.start_time = start_time

    page_context = {
            "time_intervals": time_intervals,
            "start_time": start_time,
    }

    print(edit_meeting.start_time)
    print(edit_meeting.duration)
    update_meeting_context = generate_update_meeting_context(data, edit_meetings, edit_meeting)
    context = page_context | update_meeting_context

    response = render(request, 'time_intervals.html', context=context)
    
    return response

@login_required
@require_http_methods(["PUT"])
def update_meetings(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body) # pyright: ignore
    context = generate_update_meeting_context(data)
    return render(request, 'get_meetings_builder.html', context=context)

@login_required
@require_http_methods(["GET"])
def update_rooms(request: HttpRequest) -> HttpResponse:
    building_pk = request.GET.get("building")
    
    room_options = '<option value="any">Any Room</option><optgroup>'
    for room in Room.objects.filter(building=building_pk).all():
        room_options += f'<option value="{room.pk}">{room.number}</option>'
    room_options += '</optgroup>'
    return HttpResponse(room_options)


@login_required
@require_http_methods(["POST"])
def add_rows(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body) # pyright: ignore
    edit_meetings, _ = EditMeeting.create_all(data)
    section_pk = data.get('selectedSection')
    section = Section.objects.get(pk=section_pk)
    recommended = EditMeeting.recommend_meetings(edit_meetings, section.primary_professor, section)
    edit_meeting_to_display = list(filter(lambda e: not e.is_deleted,edit_meetings))
    edit_meeting_to_display.extend(recommended)

    update_meetings_context = generate_update_meeting_context(
            data, edit_meeting_to_display, edit_meeting=recommended[0])
    input_rows_context = { 
                          "section": section,
                          "recommended": recommended, 
                          "days": Day.CODE_TO_VERBOSE.items(), 
                          "buildings": Building.objects.all(),
                          "durations": TimeBlock.DURATIONS,
    }
    context = update_meetings_context | input_rows_context

    return render(request, 'input_rows.html', context=context)

@login_required
@require_http_methods(["PUT"])
def add_section(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body) # pyright: ignore 
    section_pk = data.get('addedSection')
    sections = data.getlist('sectionGrouper')
    if section_pk in sections:
        return HttpResponse(request)
    section = Section.objects.get(pk=section_pk)
    added_sections = EditMeeting.from_section(section)
    section_context = { 
                       'section_meetings': added_sections,
                       'section': section,
                       'is_added': True,
                       'days': Day.CODE_TO_VERBOSE.items(), 
                       'buildings': Building.objects.all(),
                       'durations': TimeBlock.DURATIONS
    }

    edit_meetings, _ = EditMeeting.create_all(data)
    edit_meetings.extend(added_sections)
    update_meeting_context = generate_update_meeting_context(data, edit_meetings, added_section=section)

    context = section_context | update_meeting_context
    return render(request, 'section.html', context=context)


@login_required
@require_http_methods(["POST"])
def soft_submit(request: HttpRequest) -> HttpResponse:
    data = request.POST
    edit_meetings, _ = EditMeeting.create_all(data)

    is_changed = False
    for edit_meeting in edit_meetings:
        is_changed = is_changed or edit_meeting.is_changed()
    print(is_changed)

    edit_meetings = list(filter(lambda e: not e.is_deleted, edit_meetings))
    group_problems = EditMeeting.get_group_problems(edit_meetings)
    section_problems: list[tuple[Section, list[Problem]]] = []
    section_edit_meetings: dict[Section, list[EditMeeting]] = {}
    for meeting in edit_meetings:
        if section_edit_meetings.get(meeting.section) is not None:
            section_edit_meetings[meeting.section].append(meeting)
            continue
        section_edit_meetings[meeting.section] = [meeting]
        
    sections_to_exclude = list(section_edit_meetings.keys())
    for section, meetings in section_edit_meetings.items():
        section_problems.append(
            (section, EditMeeting.get_section_problems(meetings, sections_to_exclude=sections_to_exclude),))
    
    context = {
            'is_changed': is_changed,
            'group_problems': group_problems,
            'section_problems': section_problems,
            'exclude_group_problems': (len(sections_to_exclude) == 1) and (len(group_problems) == 0),
            }

    return render(request, 'problems_group.html', context=context)


@login_required
@require_http_methods(["POST"])
@atomic
def hard_submit(request: HttpRequest) -> HttpResponse:
    data = request.POST
    e_meetings, _ = EditMeeting.create_all(data)
    message = data.get("message")

    professor: Professor = request.user.professor # pyright: ignore

    bundle = EditRequestBundle()
    bundle.save()

    section_edit_meetings: dict[Section, list[EditMeeting]] = {}
    for meeting in e_meetings:
        if section_edit_meetings.get(meeting.section) is not None:
            section_edit_meetings[meeting.section].append(meeting)
            continue
        section_edit_meetings[meeting.section] = [meeting]
    
    message_bundle = EditMeetingMessageBundleRequest(
            message= message,
            requester = professor,
            request=bundle,
            )
    message_bundle.save()
    for section, edit_meetings in section_edit_meetings.items():
        try:
            edit_section_request = EditSectionRequest(section=section,bundle=bundle)
        except IntegrityError:
            return HttpResponse()
        edit_section_request.save()
        for edit_meeting in edit_meetings:
            edit_meeting.save_as_request(edit_section_request)
    
    return HttpResponseClientRedirect(reverse('message_hub'))

@login_required
@require_http_methods(["POST"])
@atomic
def soft_approve(request: HttpRequest) -> HttpResponse:
    data = request.POST
    request_bundle_pk = data.get('messageBundle')
    request_bundle = EditMeetingMessageBundleRequest.objects.get(pk=request_bundle_pk)
    professor: Professor = request.user.professor # pyright: ignore
    # TODO ensure that professor is department head

    edit_meetings: list[EditMeeting] = []
    section_edit_meetings: dict[Section, list[EditMeeting]] = {}
    for edit_section in request_bundle.request.edit_sections.all():
        section_edit_meetings[edit_section.section] = []
        for i, edit_meeting_request in enumerate(edit_section.edit_meetings.all(), start=1):
            edit_meeting = edit_meeting_request.reformat(i)
            edit_meetings.append(edit_meeting)
            section_edit_meetings[edit_section.section].append(edit_meeting)
    
    group_problems = EditMeeting.get_group_problems(edit_meetings)
    sections_to_exclude = section_edit_meetings.keys()
    
    section_problems: list[tuple[Section, list[Problem]]] = []
    for section, meetings in section_edit_meetings.items():
        problems = EditMeeting.get_section_problems(
                meetings, sections_to_exclude=list(sections_to_exclude))
        section_problems.append((section, problems))

    context = {
            'is_approve': True,
            'group_problems': group_problems,
            'request_bundle_pk': request_bundle_pk,
            'section_problems': section_problems,
            'exclude_group_problems': (len(sections_to_exclude) == 1) and (len(group_problems) == 0),
    }

    return render(request, 'problems_group.html', context=context)

@login_required
@require_http_methods(["POST"])
@atomic
def hard_approve(request: HttpRequest) -> HttpResponse:
    data = request.POST
    message = data.get("message")
    request_bundle_pk = data.get('messageBundle')
    print(request_bundle_pk)
    request_bundle = EditMeetingMessageBundleRequest.objects.get(pk=request_bundle_pk)
    professor: Professor = request.user.professor # pyright: ignore
    # TODO add department checks
    response_bundle = EditMeetingMessageBundleResponse(
            status=EditMeetingMessageBundleResponse.ACCEPTED,
            message=message,
            sender=professor,
            request_bundle=request_bundle.request,
            request=request_bundle,
            )
    response_bundle.save()
    request_bundle.request.realize()

    # can change to reloading message components 
    messages.success(request, ("Successfully approved the request"), extra_tags="success")
    return HttpResponseClientRedirect(reverse('message_hub'))

@login_required
@require_http_methods(["PUT"])
def deny_request(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body) # pyright: ignore
    message = data.get("message")
    request_bundle_pk = data.get('messageBundle')
    print(request_bundle_pk)
    request_bundle = EditMeetingMessageBundleRequest.objects.get(pk=request_bundle_pk)
    professor: Professor = request.user.professor # pyright: ignore
    # TODO add department checks
    response_bundle = EditMeetingMessageBundleResponse(
            status=EditMeetingMessageBundleResponse.DENIED,
            message=message,
            sender=professor,
            request_bundle=request_bundle.request,
            request=request_bundle,
            )
    response_bundle.save()

    # can change to reloading message components 
    messages.success(request, ("Successfully denied the request"), extra_tags="success")
    return HttpResponseClientRedirect(reverse('message_hub'))

@login_required
@require_http_methods(["PUT"])
def cancel_request(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body) # pyright: ignore
    message_bundle_pk = data.get('messageBundle')
    request_bundle = EditMeetingMessageBundleRequest.objects.get(pk=message_bundle_pk)
    professor: Professor = request.user.professor # pyright: ignore

    if professor != request_bundle.requester:
        return HttpResponseForbidden("You did make the request so you cannot cancel it!")

    request_bundle.delete() 
    messages.success(request, ("Successfully cancelled the request"), extra_tags="success")

    return HttpResponseClientRedirect(reverse('message_hub'))


@login_required
@require_http_methods(["PUT"])
def read_bundle(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body) # pyright: ignore
    message_bundle_pk = data.get('messageBundle')
    message_bundle = EditMeetingMessageBundleResponse.objects.get(pk=message_bundle_pk)
    message_bundle.is_read = True
    message_bundle.save()
    return HttpResponse()

@login_required
@require_http_methods(["GET"])
def add_conflicting_course_pill(request: HttpRequest, course: int) -> HttpResponse:
    course_obj = Course.objects.get(pk=course)
    context = {
            "course": course_obj,
    }
    return render(request, 'course_pill.html', context=context)

@login_required
@require_http_methods(["DELETE"])
def remove_conflicting_course_pill(request: HttpRequest, course: int) -> HttpResponse:
    data = QueryDict(request.body) # pyright: ignore
    courses = data.getlist("course", [])
    courses_objs = list(Course.objects.filter(id__in=courses).exclude(id=course).all())

    context = {
        "courses": courses_objs,
    }
    return render(request, 'course_pills.html', context=context)

