from django.http import HttpRequest, HttpResponse
from django.shortcuts import render 
from django.contrib.auth.decorators import login_required
from .models import *
from claim.models import *
from .partial_views import InputRowContext, get_update_meeting_context

@login_required
def edit_section(request: HttpRequest, section: int) -> HttpResponse:
    section: Section = Section.objects.get(pk=section)
    edit_meetings = EditMeeting.from_section(section)
    first_edit_meeting: EditMeeting = next(iter(edit_meetings), None)
    
    duration = first_edit_meeting.end_time_d() - first_edit_meeting.start_time_d()
    page_context = {
        "professor": Professor.objects.get(user=request.user),
        "section": section,
        "duration": duration,
        "building": first_edit_meeting.building.pk,
        "room": first_edit_meeting.room.pk,
    }

    input_row_context: InputRowContext = {
        "days": Day.CODE_TO_VERBOSE.items(), 
        "buildings": Building.objects.all(),
    }

    sections_to_exclude = [str(section.pk)]

    other_meetings, open_slots = EditMeeting.get_open_slots(
        section.term,
        first_edit_meeting.building,
        first_edit_meeting.room,
        first_edit_meeting.professor,
        sections_to_exclude,
        duration
    )

    print(first_edit_meeting)
    print(first_edit_meeting.get_time_intervals())
    calendar_meeting_context = get_update_meeting_context(
            edit_meetings=edit_meetings,
            building=first_edit_meeting.building,
            room=first_edit_meeting.room,
            duration=duration,
            other_meetings=other_meetings,
            open_slots=open_slots)

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
