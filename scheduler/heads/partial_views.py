from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from claim.models import *
from django.db.models import Q, Case, When, IntegerField, Count, F, Sum, QuerySet, Max, Min, Subquery, Value, Func, DurationField, TimeField
from datetime import timedelta

def only_department_heads(view_func):
    def wrapper(request, *args, **kwargs):
        user = request.user
        prof = Professor.objects.get(user=user)
        if not prof.department_head:
            return redirect('index')

    return wrapper


# Fetch Api requests


# change to only department heads...
@login_required
def dep_allo(request: HttpRequest) -> HttpResponse:
    department = request.GET.get('department')
    department = Department.objects.get(pk=department)
    term = request.GET.get('term')
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