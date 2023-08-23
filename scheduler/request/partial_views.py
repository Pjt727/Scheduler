from django.http import HttpRequest, HttpResponse, QueryDict
import math
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views import View
from claim.models import *
from .models import *
from datetime import time
from typing import TypedDict, NotRequired

class RowContext(TypedDict):
    meeting_pk: None | str
    section_pk: str
    building: Building
    room: Room
    day: str
    professor: None | str
    counter: str
    problems: list[Problem]
    start_time: time
    end_time: time

class UpdateMeetingsContext(TypedDict):
    title: str
    meetings: QuerySet[Meeting]
    edit_meetings: list[EditMeeting]
    edit_meeting: EditMeeting
    open_slots: list[TimeSlot]
    number_icons: list[NumberIcon]

class InputRowContext(RowContext):
    days: list
    buildings: list[Building]

class DisplayRowContext(RowContext):
    is_deleted: bool




# TODO look at this code for possibility of editing rows that do not have building
class DisplayRow(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        meeting_pk = request.GET.get("meeting")
        counter = request.GET.get("outerCounter")
        meeting = Meeting.objects.get(pk=meeting_pk)

        room = meeting.room
        context: DisplayRowContext = {
            "is_deleted": False,
            "meeting_pk": meeting.pk,
            "section_pk": meeting.section.pk,
            "start_time": meeting.time_block.start_end_time.start,
            "end_time": meeting.time_block.start_end_time.end, 
            "day": meeting.time_block.day,
            "building": None if room is None else room.building,
            "room": meeting.room,
            "counter": counter,
            "professor": meeting.professor,
        }

        return render(request, 'display_row.html', context=context)

    def delete(self, request: HttpRequest) -> HttpResponse:
        DELETE = QueryDict(request.body)

        start_time = DELETE.get("startTime")
        start_time = time.fromisoformat(start_time)

        end_time = DELETE.get("endTime")
        end_time = time.fromisoformat(end_time)

        room = DELETE.get("room")
        building = DELETE.get("building")
        original = DELETE.get("original")
        professor = DELETE.get("professor")
        context: DisplayRowContext = {
            "is_deleted": True,
            "meeting_pk": None if original == 'None' else original,
            "section_pk": DELETE.get("section"),
            "start_time": start_time,
            "end_time": end_time,
            "day": DELETE.get("day"),
            "building": None if building == "any" else Building.objects.get(pk=building),
            "room": None if room is None else Room.objects.get(pk=room),
            "counter": DELETE.get("counter"),
            "professor": None if professor == 'None' else Professor.objects.get(pk=professor)
        }

        return render(request, 'display_row.html', context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        pass

class InputRow(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        GET = request.GET
        changed_section = GET.get('outerSection')
        changed_counter = GET.get('outerCounter')
        enforce_department_constraints = GET.get('enforceDepartmentConstraints') is not None

        edit_meetings = EditMeeting.create_all(GET)

        edit_meeting = None
        for i, (section_pk, counter) in enumerate(zip(GET.getlist('section'), GET.getlist('counter'))):
            if (changed_section == section_pk) and (counter == changed_counter):
                edit_meeting = edit_meetings[i]
        assert edit_meeting is not None

        sections_to_exclude = GET.getlist('sectionGrouper')
        other_meetings, open_slots = edit_meeting.get_open_slots(edit_meetings, sections_to_exclude, enforce_department_constraints)
        
        # I really want a composition of these types but i guess this works?
        context: InputRowContext | UpdateMeetingsContext = {
            "meeting_pk": edit_meeting.meeting.pk,
            "section_pk": edit_meeting.section.pk,
            "start_time": edit_meeting.start_time,
            "end_time": edit_meeting.end_time,
            "day": edit_meeting.day,
            "building": edit_meeting.building,
            "room": edit_meeting.room,
            "counter": edit_meeting.counter,
            "professor": edit_meeting.professor,
            "days": Day.DAY_CHOICES,
            "buildings": Building.objects.all(),
            "meetings": other_meetings,
            "edit_meetings": edit_meetings,
            "edit_meeting": edit_meeting,
            "open_slots": open_slots,
            "title": f"Conflicts for #{edit_meeting.counter}, {edit_meeting.section}.",
            "number_icons":  TimeBlock.get_number_icons()
        }


        return render(request, 'input_row.html', context=context)

    # Very important that each input always have a value or the ordering could throw off everything
    @method_decorator(login_required)
    def put(self, request: HttpRequest) -> HttpResponse:
        data = QueryDict(request.body)
        print(data)

        changed_section = data.get('outerSection')
        changed_counter = data.get('outerCounter')
        # Only really need to make the one that is being made
        #   a fair amount of db calls may want to change it
        edit_meetings = EditMeeting.create_all(data)

        sections_to_exclude = data.getlist('sectionGrouper')

        edit_meeting = None
        for i, (section_pk, counter) in enumerate(zip(data.getlist('section'), data.getlist('counter'))):
            if (changed_section == section_pk) and (counter == changed_counter):
                edit_meeting = edit_meetings[i]
        assert edit_meeting is not None

        problems = edit_meeting.room_problems(sections_to_exclude)
        problems.extend(edit_meeting.professor_problems(sections_to_exclude))
        print(edit_meeting.room)

        context: RowContext = {
            "meeting_pk": edit_meeting.meeting.pk,
            "section_pk": edit_meeting.section.pk,
            "building": edit_meeting.building,
            "room": edit_meeting.room,
            "day": edit_meeting.day,
            "professor": edit_meeting.professor,
            "counter": edit_meeting.counter,
            "problems": problems
        }

        if any(map(lambda p: p.type == Problem.DANGER, problems)):
            context: InputRowContext
            context["start_time"] = edit_meeting.start_time
            context["end_time"] = edit_meeting.end_time
            context["days"] = Day.DAY_CHOICES
            context["buildings"] = Building.objects.all()
            context["number_icons"] =  TimeBlock.get_number_icons()
            return render(request, 'input_row.html', context=context)

        context: DisplayRowContext | UpdateMeetingsContext
        context["is_deleted"] = False
        context["start_time"] = edit_meeting.start_time
        context["end_time"] = edit_meeting.end_time
        context["edit_meetings"] = edit_meetings
        context["title"] = "Editing Meetings"

        return render(request, 'display_row.html', context=context)

@login_required
@require_http_methods(["PUT"])
def update_meetings(request: HttpRequest) -> HttpResponse:
    data = QueryDict(request.body)
    print(data)
    sections_to_exclude = data.getlist('sectionGrouper')
    changed_counter = data.get('outerCounter')
    changed_section = data.get('outerSection')
    enforce_department_constraints = data.get('enforceDepartmentConstraints') is not None
    edit_meetings = EditMeeting.create_all(data)
    edit_meeting = None
    for i, (section_pk, counter) in enumerate(zip(data.getlist('section'), data.getlist('counter'))):
        if (changed_section == section_pk) and (counter == changed_counter):
            edit_meeting = edit_meetings[i]
    context = {
        'edit_meetings': edit_meetings,
        'title': "Editing Meetings",
        'number_icons': TimeBlock.get_number_icons()
    }
    # edit_meeting should be none when the user is currently not editing a row
    if edit_meeting is None:
        return render(request, 'get_meetings.html', context=context)
    
    other_meetings, open_slots = edit_meeting.get_open_slots(edit_meetings, sections_to_exclude, enforce_department_constraints)
    context['meetings'] = other_meetings
    context['edit_meeting'] = edit_meeting
    context['open_slots'] = open_slots
    context['title'] = f"Conflicts for #{edit_meeting.counter}, {edit_meeting.section}."


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
@require_http_methods(["POST"])
def group_warnings(request: HttpRequest) -> HttpResponse:

    return