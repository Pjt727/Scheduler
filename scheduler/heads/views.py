from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from claim.models import *
from django.db.models import Q, Case, When, IntegerField, Count, F, Sum, QuerySet, Max, Min, Subquery, Value, Func, DurationField, TimeField
from datetime import timedelta

POST_ERR_MESSAGE = "Only post requests are allowed!"
GET_ERR_MESSAGE = "Only get requests are allowed!"

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
def term_overview(request: HttpRequest) -> HttpResponse:
    data = {
            "terms": Term.objects.all().order_by('-year',
            Case(
                When(season=Term.FALL, then=1),
                When(season=Term.WINTER, then=2),
                When(season=Term.SPRING, then=3),
                When(season=Term.SUMMER, then=4),
                default=0,
                output_field=IntegerField(),
            )),
            "departments": Department.objects.all(),
    }
    return render(request, 'term_overview.html', context=data)


# change to only department heads...
@login_required
def dep_allo(request: HttpRequest) -> JsonResponse:
    response_data = {}

    # not get check
    if request.method != 'GET':
        response_data['error'] = GET_ERR_MESSAGE
        response_data['ok'] = False
        return JsonResponse(response_data)
    department = request.GET.get('department')
    term = request.GET.get('term')

    
    time_blocks = TimeBlock.objects.exclude(number=None)
    
    numbers: dict[int, dict[str, dict[str, dict]]] = {}

    # generating the allocation group data
    numbers_allo_group: dict[int, dict] = {}
    for department_allocation in DepartmentAllocation.objects.filter(department=department).all():
        number_dict = {}

        number_dict["count"] = Room.objects.filter(
            meetings__section__course__subject__department=department,
            meetings__section__term=term,
            is_general_purpose=True,
            meetings__time_block__in=department_allocation.allocation_group.time_blocks.all()
        ).distinct().count()

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

    data = {
            "department": department,
            "time_blocks": time_blocks_dict,
            "numbers": numbers,
            "start_end_times": StartEndTime.objects.exclude(time_blocks__number=None).order_by("end").all(),
            "days": Day.DAY_CHOICES,
            }
    dep_allo_template = render(request, "dep_allo.html", data).content.decode()

    response_data['ok'] = True
    response_data['dep_allo_html'] = dep_allo_template
    return JsonResponse(response_data)


# change to only department heads...
@login_required
def dep_allo_sections(request: HttpRequest) -> JsonResponse:
    response_data = {}

    # not get check
    if request.method != 'GET':
        response_data['error'] = GET_ERR_MESSAGE
        response_data['ok'] = False
        return JsonResponse(response_data)
    
    department = request.GET.get('department')
    term = request.GET.get('term')

    sort_column = request.GET.get('sort_column')
    sort_type = request.GET.get('sort_type')
    group = request.GET.get('allocation_group')
    start_slice = int(request.GET.get('start_slice'))
    end_slice = int(request.GET.get('end_slice'))
    sections_qs = Section.objects.filter(course__subject__department=department, term=term)
    if (group is not None) and (group != 'null'):
        allocation_group = AllocationGroup.objects.get(pk=group)
        sections_qs = sections_qs.filter(
            meetings__room__is_general_purpose=True,
            meetings__time_block__in=allocation_group.time_blocks.all()
        ).distinct()


    sections_qs = Section.sort_sections(section_qs=sections_qs, sort_column=sort_column, sort_type=sort_type)
    original_length = len(sections_qs)
    sections_qs = sections_qs[start_slice:end_slice]

    sections_html = render(request, "sections.html", {
        "sections": sections_qs,
        "allocation": True,
        "sort_column": sort_column,
        "sort_type": sort_type,
        "start_slice": start_slice,
        "end_slice": min(end_slice, original_length),
        "original_length": original_length  
    }).content.decode()
    
    response_data['ok'] = True
    response_data['sections_html'] = sections_html

    return JsonResponse(response_data)