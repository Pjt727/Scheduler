from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from claim.models import *
from django.db.models import Q
from .page_views import only_department_heads



# Fetch Api requests


# change to only department heads...
@login_required
def dep_allo(request: HttpRequest) -> HttpResponse:
    department = request.GET.get('department')
    department = Department.objects.get(pk=department)
    term = request.GET['term']
    print(department, term)

    
    time_blocks = TimeBlock.objects.exclude(number=None)
    
    numbers: dict[int, dict[str, dict[str, dict]]] = {}

    # generating the allocation group data
    numbers_allo_group: dict[int, dict] = {}
    for department_allocation in DepartmentAllocation.objects.filter(department=department).all():
        number_dict = {}

        number_dict["count"] = department_allocation.count_rooms(term)

        number_dict["max"] = department_allocation.number_of_classrooms
        numbers_allo_group[department_allocation.allocation_group.pk] = number_dict


    for time_block in time_blocks.all():
        department_allo: AllocationGroup = time_block.allocation_groups.first()
        number_dict = numbers_allo_group[department_allo.pk].copy()
        number_dict["allocation_group"] = department_allo.pk
        number_dict["number"] = time_block.number

        start_time_blob = numbers.get(time_block.start_end_time.pk)
        if start_time_blob is None: numbers[time_block.start_end_time.pk] = {}
        numbers[time_block.start_end_time.pk][time_block.day] = number_dict

    time_blocks_dict = {}
    for code, _ in Day.DAY_CHOICES:
        time_blocks_dict[code] = {}
        for tb in time_blocks.filter(day=code).all():
            time_blocks_dict[code][tb.number] = tb

    context = {
            "department": department,
            "time_blocks": time_blocks_dict,
            "numbers": numbers,
            "start_end_times": StartEndTime.objects.exclude(time_blocks__number=None).order_by("end").all(),
            "days": Day.DAY_CHOICES,
            }
    response = render(request, "dep_allo.html", context=context)
    response['HX-Trigger'] = 'newOptions'
    return response



# change to only department heads...
@login_required
def dep_allo_sections(request: HttpRequest) -> HttpResponse:
    department = request.GET.get('department')
    term = request.GET.get('term')

    sort_column = request.GET.get('sortColumn')
    sort_type = request.GET.get('sortType')
    group = request.GET.get('allocationGroup')
    start_slice = int(request.GET.get('startSlice', 0))
    end_slice = int(request.GET.get('endSlice', Section.SEARCH_INTERVAL))
    sections_qs = Section.objects.filter(course__subject__department=department, term=term)
    if (group is not None):
        allocation_group = AllocationGroup.objects.get(pk=group)
        sections_qs = sections_qs.filter(
            meetings__room__is_general_purpose=True,
            meetings__time_block__in=allocation_group.time_blocks.all()
        ).distinct()


    sections_qs = Section.sort_sections(section_qs=sections_qs, sort_column=sort_column, sort_type=sort_type)
    original_length = len(sections_qs)
    sections_qs = sections_qs[start_slice:end_slice]
    context = {
        "refresh_url": reverse(request.resolver_match.view_name),
        "sections": sections_qs,
        "allocation": True,
        "allocation_group": group,
        "sort_column": sort_column,
        "sort_type": sort_type,
        "start_slice": start_slice,
        "end_slice": min(end_slice, original_length),
        "original_length": original_length,
        "search_interval": Section.SEARCH_INTERVAL
    }

    return render(request, "sections.html", context=context) 

@login_required
def professor_search(request: HttpRequest, offset: int) -> HttpResponse:
    data = request.GET

    professor_query = data.get("professor_query", "")
    professor_filter = Q()
    for part in professor_query.split(" "):
        professor_filter |= Q(first_name__icontains=part)
        professor_filter |= Q(last_name__icontains=part)
        professor_filter |= Q(email__icontains=part)
    possible_professor = Professor.objects.filter(professor_filter).all()
    amount_of_professors = len(possible_professor)

    context = {
        "professors": possible_professor[offset:offset + Professor.SEARCH_INTERVAL],
        "offset": offset,
        "get_more": amount_of_professors > (offset + Professor.SEARCH_INTERVAL),
        "next_offset": offset + Professor.SEARCH_INTERVAL,
        "has_results": amount_of_professors > 0,
    }

    return render(request, "professor_results.html", context=context)

@login_required
def professor_live_search(request: HttpRequest) -> HttpResponse:
    return render(request, "professor_live_search.html")

@login_required
def professor_display(request: HttpRequest, professor_pk: str) -> HttpResponse:
    if professor_pk == "any":
        professor = None
    else:
        professor = Professor.objects.filter(pk=professor_pk).first()
    context = {
            "professor": professor
            }
    return render(request, "professor_display.html", context=context)

@login_required
def get_head_sections(request: HttpRequest) -> HttpResponse:
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

    is_available = request.GET.get("available", False)

    start_slice = int(request.GET.get("startSlice", 0))
    end_slice = int(request.GET.get("endSlice", Section.SEARCH_INTERVAL))
    original_length = 0
    context = {
        "sections": [],
        "claim": True,
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

    return render(request, "head_sections.html", context=context)
