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
from typing import TypedDict, NotRequired

class InputRowContext(TypedDict):
    edit_meeting: EditMeeting
    days: list[str]
    buildings: list[Building]
    time_intervals: list[tuple[timedelta, timedelta]]

class UpdateMeetingsContext(TypedDict):
    title: str
    meetings: QuerySet[Meeting]
    edit_meetings: list[EditMeeting]
    open_slots: list[TimeSlot]
    number_icons: list[NumberIcon]
    in_edit_mode: bool
    edit_room: Room
    edit_building: Building | None


# TODO look at this code for possibility of editing rows that do not have building
class DisplayRow(View):
    # may not even ever want this endpoint
    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        meeting_pk = request.GET.get("meeting")
        counter = request.GET.get("outerCounter")
        meeting = Meeting.objects.get(pk=meeting_pk)

        edit_meeting = EditMeeting.from_meeting(meeting, counter)

        context = {
            'editing_meeting': edit_meeting
        }

        return render(request, 'display_row.html', context=context)

    def delete(self, request: HttpRequest) -> HttpResponse:
        DELETE = QueryDict(request.body)
        changed_section = DELETE.get('outerSection')
        changed_counter = DELETE.get('outerCounter')

        edit_meetings = EditMeeting.create_all(DELETE)
        edit_meeting = None
        for i, (section_pk, counter) in enumerate(zip(DELETE.getlist('section'), DELETE.getlist('counter'))):
            if (changed_section == section_pk) and (counter == changed_counter):
                edit_meeting = edit_meetings[i]


        return render(request, 'display_row.html', context=context | update_meeting_context)

    def post(self, request: HttpRequest) -> HttpResponse:
        pass

class InputRow(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        GET = request.GET
        changed_section = GET.get('outerSection')
        changed_counter = GET.get('outerCounter')

        edit_meetings = EditMeeting.create_all(GET)


        return render(request, 'input_row.html', context = context | update_meeting_context)

    # Very important that each input always have a value or the ordering could throw off everything
    @method_decorator(login_required)
    def put(self, request: HttpRequest) -> HttpResponse:
        data = QueryDict(request.body)

        changed_section = data.get('outerSection')
        changed_counter = data.get('outerCounter')
        # Only really need to make the one that is being made
        #   a fair amount of db calls may want to change it
        edit_meetings = EditMeeting.create_all(data)

        sections_to_exclude = data.getlist('sectionGrouper')

        edit_meeting = None

        problems = edit_meeting.room_problems(sections_to_exclude)
        problems.extend(edit_meeting.professor_problems(sections_to_exclude))


        return render(request, 'display_row.html', context=context | update_meeting_context)

    @method_decorator(login_required)
    def post(self, request: HttpRequest) -> HttpResponse:
        
        pass


@login_required
@require_http_methods(["GET"])
def update_time_intervals(request: HttpRequest) -> HttpResponse:
    data = request.GET
    day = data.get('day')
    start_end_time = data.get('startEndTime')
    start_time, end_time = start_end_time.split(',')
    start_time = time.fromisoformat(start_time)
    end_time = time.fromisoformat(end_time)

    duration = timedelta(hours=start_time.hour, minutes=start_time.minute) - \
        timedelta(hours=end_time.hour, minutes=end_time.minute)
    time_intervals = TimeBlock.get_time_intervals(duration, day)

    context = {
        "time_intervals": time_intervals,
        "start_time": start_time,
        "end_time": end_time,
    }

    return render(request, 'time_intervals.html', context=context)

@login_required
@require_http_methods(["PUT"])
def update_meetings(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body)
    context = get_update_meeting_context(data)
    return render(request, 'get_meetings.html', context=context)

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
@require_http_methods(["GET"])
def add_rows(request: HttpRequest) -> HttpResponse:
    data = request.GET
    edit_meetings = EditMeeting.create_all(data)
    section_pk = data.get('selectedSection')
    section = Section.objects.get(pk=section_pk)
    # TODO better professor guessing
    recommended = EditMeeting.recommend_meetings(edit_meetings, section.primary_professor, section)
    edit_meeting_to_display = list(filter(lambda e: not e.is_deleted,edit_meetings))
    edit_meeting_to_display.extend(recommended)

    context: UpdateMeetingsContext = {
        'recommended': recommended,
        'edit_meetings': edit_meeting_to_display,
        'title': "Editing Meetings",
        'number_icons': TimeBlock.get_number_icons(),
        'in_edit_mode': True,
    }

    return render(request, 'display_rows.html', context=context)

@login_required
@require_http_methods(["GET"])
def add_section(request: HttpRequest) -> HttpResponse:
    data = request.GET
    section_pk = data.get('section')
    sections = data.getlist('sectionGrouper')
    if section_pk in sections:
        return HttpResponse(request)
    section = Section.objects.get(pk=section_pk)
    context = { 
        'section': section,
        'is_added': True,
    }
    return render(request, 'section.html', context=context)


@login_required
@require_http_methods(["PUT"])
def toggle_visibility(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body)
    changed_section = data.get('outerSection')
    visible_sections: list[str] = []

    toggled_visibility = None
    for section, visibility in zip(data.getlist('sectionGrouper'), data.getlist('isVisible')):
        visibility = visibility == 'true'
        if section == changed_section:
            toggled_visibility = not visibility
            if toggled_visibility:
                visible_sections.append(section)
            continue
        if visibility: visible_sections.append(section)
    assert toggled_visibility is not None

    edit_meetings = EditMeeting.create_all(data)
    edit_meetings = filter(
        lambda e: (not e.is_deleted) and (str(e.section.pk) in visible_sections),
        edit_meetings)


    context: UpdateMeetingsContext = {
        'server_trigger': True,
        'is_visible': toggled_visibility,
        'edit_meetings': list(edit_meetings),
        'title': "Edit Meetings",
        'number_icons': TimeBlock.get_number_icons(),
        'in_edit_mode': True,

    }
    return render(request, 'toggle_visibility.html', context=context)


@login_required
@require_http_methods(["POST"])
def soft_submit(request: HttpRequest) -> HttpResponse:
    data = request.POST
    edit_meetings = EditMeeting.create_all(data)
    edit_meetings = list(filter(lambda e: not e.is_deleted, edit_meetings))
    group_problems = EditMeeting.get_group_problems(edit_meetings)
    section_problems: list[tuple[Section, list[Problem]]] = []
    section_edit_meetings: dict[Section, list[EditMeeting]] = {}
    for meeting in edit_meetings:
        if section_edit_meetings.get(meeting.section) is not None:
            section_edit_meetings[meeting.section].append(meeting)
            continue
        section_edit_meetings[meeting.section] = [meeting]
        
    sections_to_exclude = section_edit_meetings.keys()
    for section, meetings in section_edit_meetings.items():
        section_problems.append(
            (section, EditMeeting.get_section_problems(meetings, sections_to_exclude=sections_to_exclude),))
    
    context = {
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
    e_meetings = EditMeeting.create_all(data)

    bundle = EditRequestBundle(requester=request.user.professor)
    bundle.save()

    section_edit_meetings: dict[Section, list[EditMeeting]] = {}
    for meeting in e_meetings:
        if section_edit_meetings.get(meeting.section) is not None:
            section_edit_meetings[meeting.section].append(meeting)
            continue
        section_edit_meetings[meeting.section] = [meeting]
    
    message_bundle = EditMeetingMessageBundle(
        status=EditMeetingMessageBundle.REQUESTED,
        sender = request.user.professor,
        request=bundle,
        request_pk=bundle.pk
    )
    message_bundle.save()
    for section, edit_meetings in section_edit_meetings.items():
        try:
            edit_section_request = EditSectionRequest(section=section,bundle=bundle)
        except IntegrityError:
            return HttpResponse()
        edit_section_request.save()
        for edit_meeting in edit_meetings:
            meeting_request = edit_meeting.save_as_request(edit_section_request)
            meeting_request.freeze(message_bundle)
    
    return HttpResponseClientRedirect(reverse('message_hub'))

@login_required
@require_http_methods(["POST"])
@atomic
def soft_approve(request: HttpRequest) -> HttpResponse:
    data = request.POST
    request_bundle_pk = data.get('requestBundle')
    request_bundle = EditRequestBundle.objects.get(pk=request_bundle_pk)
    professor: Professor = request.user.professor
    # should never happen unless someone messes with the requests 
    if not professor.is_department_head:
        return HttpResponseForbidden("You must be a department head to approve a request!")

    edit_meetings: list[EditMeeting] = []
    section_edit_meetings: dict[Section, list[EditMeeting]] = {}
    for edit_section in request_bundle.edit_sections.all():
        section_edit_meetings[edit_section.section] = []
        for i, edit_meeting_request in enumerate(edit_section.edit_meetings.all(), start=1):
            edit_meeting = edit_meeting_request.reformat(i)
            edit_meetings.append(edit_meeting)
            section_edit_meetings[edit_section.section].append(edit_meeting)
    
    group_problems = EditMeeting.get_group_problems(edit_meetings)
    sections_to_exclude = section_edit_meetings.keys()
    
    section_problems: list[tuple[Section, list[Problem]]] = []
    for section, meetings in section_edit_meetings.items():
        section_problems.append(
            (section, EditMeeting.get_section_problems(meetings, sections_to_exclude=sections_to_exclude),))

    context = {
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
    request_bundle_pk = data.get('requestBundle')
    request_bundle = EditRequestBundle.objects.get(pk=request_bundle_pk)
    professor: Professor = request.user.professor
    # should never happen unless someone messes with the requests 
    if not professor.is_department_head:
        return HttpResponseForbidden("You must be a department head to approve a request!")
    message_bundle = EditMeetingMessageBundle(
        status=EditMeetingMessageBundle.ACCEPTED,
        sender=professor,
        recipient=request_bundle.requester,
        request_pk=request_bundle.pk
    )
    message_bundle.save()
    for edit_section in request_bundle.edit_sections.all():
        for edit_meeting in edit_section.edit_meetings.all():
            message = edit_meeting.freeze(message_bundle)
            message.save()

    request_bundle.realize()
    request_bundle.delete()
    messages.success(request, ("Successfully approved the request"), extra_tags="success")
    return HttpResponseClientRedirect(reverse('message_hub'))


@login_required
@require_http_methods(["PUT"])
def read_bundle(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body)
    message_bundle_pk = data.get('messageBundle')
    message_bundle = EditMeetingMessageBundle.objects.get(pk=message_bundle_pk)
    message_bundle.is_read = True
    message_bundle.save()
    return HttpResponse()



@login_required
@require_http_methods(["PUT"])
def cancel_request(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body)
    message_bundle_pk = data.get('messageBundle')
    message_bundle = EditMeetingMessageBundle.objects.get(pk=message_bundle_pk)
    professor: Professor = request.user.professor
    request_bundle = message_bundle.request

    if professor != request_bundle.requester:
        return HttpResponseForbidden("You did make the request so you cannot cancel it!")

    message_bundle = EditMeetingMessageBundle(
        status=EditMeetingMessageBundle.CANCELED,
        sender=professor,
        request_pk=request_bundle.pk)
    message_bundle.save()
    for edit_section in request_bundle.edit_sections.all():
        for edit_meeting in edit_section.edit_meetings.all():
            message = edit_meeting.freeze(message_bundle)
            message.save()
    request_bundle.delete() 
    messages.success(request, ("Successfully cancelled the request"), extra_tags="success")

    return HttpResponseClientRedirect(reverse('message_hub'))