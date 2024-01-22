from django.http import HttpRequest, HttpResponse
from django.shortcuts import render 
from django.contrib.auth.decorators import login_required
from .models import *
from claim.models import *
from .partial_views import get_update_meeting_context
from django.db.models import Max

@login_required
def edit_section(request: HttpRequest, section_pk: int) -> HttpResponse:
    section: Section = Section.objects.get(pk=section_pk)
    edit_section = EditSectionRequest.objects \
            .filter(section=section) \
            .filter(bundle__request_message__isnull=False) \
            .filter(bundle__request_message__response__isnull=True) \
            .first()


    sections_to_exclude: set[Section] = set()
    edit_meetings: list[EditMeeting] = []
    og_edit_meetings = []
    if edit_section is not None:
        edit_bundle = edit_section.bundle
        for section_bundle in edit_bundle.edit_sections.all():
            s = section_bundle.section
            sections_to_exclude.add(s)
            og_e_ms = EditMeeting.from_section(s)
            og_edit_meetings.extend(og_e_ms)
            # can do this in one query instead
            edit_meetings.extend(section_bundle.data_edit_meetings())
    else:
        sections_to_exclude.add(section)
        edit_meetings = EditMeeting.from_section(section)

    first_edit_meeting: EditMeeting | None = next(iter(edit_meetings), None)
    page_conetext = {
            "og_edit_meetings": og_edit_meetings,

            # used for when there are no edit_meetings
            "empty_sections": sections_to_exclude,
            }
    input_row_context = {
            "days": Day.CODE_TO_VERBOSE.items(), 
            "buildings": Building.objects.all(),
            }
    if first_edit_meeting is None:
        none_calendar_context = get_update_meeting_context()
        context = page_conetext | input_row_context | none_calendar_context  
        return render(request, 'edit_section.html', context=context)

    
    duration = first_edit_meeting.end_time_d() - first_edit_meeting.start_time_d()

    first_building = first_edit_meeting.building
    if first_building is None:
        first_building = Building.recommend(
                first_edit_meeting.section.course, first_edit_meeting.section.term)

    other_meetings, open_slots = EditMeeting.get_open_slots(
        section.term,
        first_building,
        first_edit_meeting.room,
        first_edit_meeting.professor,
        sections_to_exclude,
        duration
    )

    calendar_meeting_context = get_update_meeting_context(
            edit_meetings=edit_meetings,
            building=first_edit_meeting.building,
            room=first_edit_meeting.room,
            duration=duration,
            other_meetings=other_meetings,
            open_slots=open_slots)

    context = page_conetext | input_row_context | calendar_meeting_context

    return render(request, 'edit_section.html', context=context)


@login_required
def message_hub(request: HttpRequest) -> HttpResponse:
    professor: Professor = request.user.professor # pyright: ignore

    current_bundles = professor.requested_bundles \
            .filter(response__is_read=False)

    current_bundles_sorted = current_bundles \
            .annotate(max_date=Max('date_sent', 'response__date_sent')) \
            .order_by('max_date')

    # sorting does not work as expected
    past_bundles = professor.requested_bundles \
            .exclude(pk__in=current_bundles) \
            .annotate(max_date=Max('date_sent', 'response__date_sent')) \
            .order_by('max_date')

    context = {
        'professor': professor,
        'current_bundles': current_bundles_sorted.all(),
        'past_bundles': past_bundles.all(),
    }

    return render(request, 'messages.html', context=context)
