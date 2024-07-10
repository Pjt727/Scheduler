from django.contrib.auth.decorators import login_required
from django.db.utils import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from request.models import *

from .models import *


@login_required
@require_http_methods(["GET"])
def get_course_search(request: HttpRequest) -> HttpResponse:
    term_pk = request.GET.get("term")

    department_pk = request.GET.get("department")
    if department_pk == "any":
        department = None
    else:
        department = Department.objects.get(pk=department_pk)
    subject_pk = request.GET.get("subject")
    if subject_pk == "any":
        subject = None
    else:
        subject = Subject.objects.get(pk=subject_pk)
    course_query = request.GET.get("course_query")
    is_department_change = request.GET.get("isDepartmentChange") == "True"

    subjects = Subject.objects.filter(courses__sections__term=term_pk).distinct()
    if is_department_change:
        subject = None
    else:
        department = None if subject is None else subject.department

    if department is not None:
        subjects = subjects.filter(department=department)

    # update the user preferencesi
    professor: Professor = request.user.professor  # pyright: ignore
    # dont really need this bc it is expected that professor already has a preference
    #   from loading the page
    preferences = Preferences.get_or_create_from_professor(professor)
    preferences.claim_department = department
    preferences.claim_subject = subject
    preferences.claim_term = Term.objects.get(pk=term_pk)
    preferences.save()

    context = {
        "departments": Department.objects.all(),
        "selected_department": department,
        "subjects": subjects.distinct().all(),
        "selected_subject": subject,
        "course_query": course_query,
    }

    return render(request, "department_subject.html", context=context)


@login_required
@require_http_methods(["GET"])
def get_course_results(request: HttpRequest, offset: int) -> HttpResponse:
    data = request.GET
    term_pk = data.get("term")
    term = Term.objects.get(pk=term_pk)

    department_pk = request.GET.get("department")
    if department_pk == "any":
        department = None
    else:
        department = Department.objects.get(pk=department_pk)
    subject_pk = data.get("subject")
    if subject_pk == "any":
        subject = None
    else:
        subject = Subject.objects.get(pk=subject_pk)

    course_query = data.get("course_query")
    add_course_url = data["add_course_url"]
    courses, has_results = Course.search(course_query, term.pk, department, subject)
    courses = courses.order_by("title")
    # TODO implement if can be made faster
    # courses = Course.sort_with_prof(courses, professor=request.user.professor)

    context = {
        "courses": courses.all()[offset : offset + Course.SEARCH_INTERVAL],
        "offset": offset,
        "get_more": len(courses) > (offset + Course.SEARCH_INTERVAL),
        "next_offset": offset + Course.SEARCH_INTERVAL,
        "has_results": has_results,
        "add_course_url": add_course_url,
    }

    return render(request, "course_results.html", context=context)


@login_required
@require_http_methods(["GET"])
def add_course_pill(request: HttpRequest, course: int) -> HttpResponse:
    professor: Professor = request.user.professor  # pyright: ignore
    course_obj = Course.objects.get(pk=course)
    try:
        pref_course = PreferencesCourse(
            preferences=professor.preferences, course=course_obj
        )
        pref_course.save()
    except IntegrityError:
        # the pref_course probably already existed
        pass

    context = {
        "courses": map(lambda p: p.course, professor.preferences.claim_courses.all()),
    }

    return render(request, "course_pills.html", context=context)


@login_required
@require_http_methods(["DELETE"])
def remove_course_pill(request: HttpRequest, course: int) -> HttpResponse:
    # mainly doing it this way to ensure that empty course selections are
    #    properly maintained
    professor: Professor = request.user.professor  # pyright: ignore
    data = QueryDict(request.body)  # pyright: ignore
    courses = data.getlist("course", [])
    courses_objs = list(Course.objects.filter(id__in=courses).exclude(id=course).all())

    pref_courses = PreferencesCourse.objects.filter(
        preferences=professor.preferences, course=course
    )
    pref_course = pref_courses.first()
    if pref_course:
        pref_course.delete()

    context = {
        "courses": courses_objs,
    }
    return render(request, "course_pills.html", context=context)


@login_required
@require_http_methods(["GET"])
def get_meetings(request: HttpRequest, professor_pk: int) -> HttpResponse:

    term = request.GET.get("term")
    term = Term.objects.get(pk=term)
    requester = Professor.objects.get(user=request.user)
    professor = Professor.objects.get(pk=professor_pk)
    meetings = professor.meetings.filter(section__term=term).order_by("section__pk")
    sections_without_meetings = (
        professor.sections.exclude(meetings__professor=professor)
        .filter(term=term)
        .all()
    )
    if requester == professor:
        title = f"Your {term}"
    else:
        title = f"{professor} - {term}"

    data = {
        "professor": professor,
        "title": title,
        "meetings": meetings,
        "sections_without_meetings": sections_without_meetings,
    }

    return render(request, "p_my_meetings.html", context=data)


@login_required
@require_http_methods(["GET"])
def get_meeting_details(request: HttpRequest) -> HttpResponse:
    meeting = request.GET.get("meeting")  # pyright: ignore
    in_edit_mode = request.GET.get("inEditMode") == "True"
    meeting: Meeting = Meeting.objects.get(pk=meeting)

    is_shared_section = meeting.section.meetings.exclude(
        professor=meeting.section.primary_professor
    ).exists()

    data = {
        "section": meeting.section,
        "meeting": meeting,
        "is_shared_section": is_shared_section,
        "in_edit_mode": in_edit_mode,
    }
    return render(request, "meeting_details.html", context=data)


@login_required
@require_http_methods(["GET"])
def section_search(request: HttpRequest) -> HttpResponse:
    courses = request.GET.getlist("course", [])
    only_search_on_courses = request.GET.get("isCourseSearch") is None

    subject = None
    department = None
    if only_search_on_courses:
        department = request.GET.get("department")
        subject = request.GET.get("subject")

    if not isinstance(courses, list):
        courses = [courses]

    term = request.GET["term"]

    # TODO implement
    # exclusion_times = data.get('exclusion_times', [])
    does_fit = request.GET.get("fits", False)
    is_available = request.GET.get("available", False)

    sort_column = request.GET.get("sortColumn")
    sort_type = request.GET.get("sortType")
    start_slice = int(request.GET.get("startSlice", 0))
    end_slice = int(request.GET.get("endSlice", Section.SEARCH_INTERVAL))
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
    if only_search_on_courses:
        if subject == "any" and department != "any":
            section_qs = Section.objects.filter(
                term=term, course__department=department
            )
        elif subject != "any":
            section_qs = Section.objects.filter(term=term, course__subject=subject)
        else:
            section_qs = Section.objects.filter(term=term)
    elif not courses:
        return render(request, "sections.html", context=context)
    else:
        section_qs = Section.objects.filter(term=term, course__in=courses)

    # exclude meetings with professors
    if is_available:
        sections_with_any_open_meetings = Q(meetings__professor__isnull=True)
        sections_with_any_open_primaries = Q(primary_professor__isnull=True)

        section_qs = section_qs.filter(
            sections_with_any_open_meetings | sections_with_any_open_primaries
        )

    # Exclude all meetings that overlap with professor meetings
    if does_fit:
        section_qs = section_qs.exclude(professor.section_in_meetings(term))

    section_qs = Section.sort_sections(
        section_qs=section_qs.distinct(), sort_column=sort_column, sort_type=sort_type
    )
    original_length = len(section_qs)
    sections = section_qs[start_slice:end_slice]
    context["sections"] = sections
    context["end_slice"] = min(end_slice, original_length)
    context["original_length"] = original_length

    return render(request, "sections.html", context=context)


@login_required
@require_http_methods(["GET"])
def get_claim_info(request: HttpRequest, section_pk: int) -> HttpResponse:
    section = Section.objects.get(pk=section_pk)
    has_primary = section.primary_professor != None
    available = section.meetings.filter(professor=None).first() != None
    can_claim = (not has_primary) or (available)

    context = {
        "section": section,
        "can_claim": can_claim,
    }

    return render(request, "claim_info.html", context=context)


@login_required
@require_http_methods(["PUT"])
def claim_section(request: HttpRequest, section_pk: int) -> HttpResponse:
    professor: Professor = request.user.professor  # pyright: ignore
    section = Section.objects.get(pk=section_pk)
    data = QueryDict(request.body)  # pyright: ignore
    if section.primary_professor is None:
        section.primary_professor = professor
        section.save()
    claimed_meetings: list[Meeting] = []
    meetings = section.meetings
    for meeting in meetings.all():
        if meeting.professor is None and str(meeting.pk) in data:
            meeting.professor = professor
            meeting.save()
            claimed_meetings.append(meeting)

    context = {
        "claimed_section": section,
        "claimed_meetings": claimed_meetings,
    }

    return render(request, "claim_message.html", context=context)
