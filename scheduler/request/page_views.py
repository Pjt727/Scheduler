from django.http import HttpRequest, HttpResponse
from django.shortcuts import render 
from django.contrib.auth.decorators import login_required
from .models import *
from claim.models import *
from .partial_views1 import InputRowContext, UpdateMeetingsContext

@login_required
def edit_section(request: HttpRequest, section: int) -> HttpResponse:
    section: Section = Section.objects.get(pk=section)
    edit_meetings = EditMeeting.from_section(section)
    first_edit_meeting = next(iter(edit_meetings), None)
    
    page_context = {
        "professor": Professor.objects.get(user=request.user),
        "section": section,
    }

    input_row_context: InputRowContext = {
        "days": Day.CODE_TO_VERBOSE.items(), 
        "buildings": Building.objects.all(),
    }

    editing_room = first_edit_meeting.room

    # CHANGE THE VALUE TO TRUE ONCE DONE WITH CHANGES
    other_meetings, open_slots = first_edit_meeting.get_open_slots(
        edit_meetings, [str(section.pk)], False)
    calendar_meeting_context: UpdateMeetingsContext = {
        "edit_meetings": edit_meetings,
        "building": None, # building is always none if room is none in this case
        "edit_room": editing_room,
        "number_icons": TimeBlock.get_number_icons,
        "title": f"Conflicts for {editing_room}",
        "in_edit_mode": True,
        "meetings": other_meetings,
        "open_slots": open_slots,
    }

    context = page_context | input_row_context | calendar_meeting_context

    return render(request, 'edit_section.html', context=context)


@login_required
def message_hub(request: HttpRequest) -> HttpResponse:
    professor: Professor = request.user.professor

    unread_bundles = professor.sent_bundles.filter(is_read=False) | \
        professor.receive_bundles.filter(is_read=False)
    
    read_bundles = professor.sent_bundles.filter(is_read=True) | \
        professor.receive_bundles.filter(is_read=True)
    context = {
        'professor': professor,
        'unread_bundles': unread_bundles.all(),
        'read_bundles': read_bundles.all(),
    }

    return render(request, 'messages.html', context=context)