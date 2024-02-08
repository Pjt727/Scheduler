from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from .models import *
from request.models import *
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET"])
def get_course_search(request: HttpRequest) -> HttpResponse:
    term_pk = request.GET.get("term")
    term = Term.objects.get(pk=term_pk)

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
    print(request.GET.get("isDepartmentChange") )

    subjects = Subject.objects.filter(courses__sections__term=term_pk).distinct()
    if is_department_change:
        subject = None
    else:
        department = None if subject is None else subject.department

    if department is not None:
        subjects = subjects.filter(department=department)

    courses, has_results = Course.search(course_query, term_pk, department, subject)
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
def get_course_results(request: HttpRequest, offset: int) -> HttpResponse:
    term_pk = request.GET.get("term")
    term = Term.objects.get(pk=term_pk)

    department_pk = request.GET.get("department")
    assert department_pk is not None
    subject_pk = request.GET.get("subject")
    assert subject_pk is not None
    course_query = request.GET.get("course_query")

    courses, has_results = Course.search(course_query, term.pk, department_pk, subject_pk)
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

    course_obj = Course.objects.get(pk=course)

    context = {
        "course": course_obj
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
def get_meeting_details(request: HttpRequest) -> HttpResponse:
    meeting = request.GET.get('meeting') # pyright: ignore
    in_edit_mode = request.GET.get('inEditMode') == 'True'
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
