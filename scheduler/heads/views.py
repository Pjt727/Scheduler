from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from claim.models import Department, Course, Subject, Professor, Term, Section, Meeting, Day, TimeBlock, StartEndTime, AllocationGroup, Meeting, DepartmentAllocation
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

def count_by_two_spots(sections: QuerySet, allocation_group: AllocationGroup) -> int:
    return sections.annotate(meeting_count=Count(
            'meetings',
            filter=Q(meetings__time_block__allocation_group=allocation_group))
        ).filter(meeting_count__gte=2).count()

def count_by_sum_hours_in_allocation(sections: QuerySet, allocation_group: AllocationGroup) -> int:
    return sections.annotate(
            duration_sum=Sum(
                F('meetings__time_block__start_end_time__end') - F('meetings__time_block__start_end_time__start'),
                filter=Q(meetings__time_block__allocation_group=allocation_group),
            )
        ).filter(duration_sum__gte=timedelta(hours=2,minutes=30)).count()

# get sections in 
def get_sections_by_overlapping_duration(sections: QuerySet, allocation_group: AllocationGroup):
    allocation_time_blocks = allocation_group.time_blocks

    allocation_overlaps = {}

    for allocation_time_block in allocation_time_blocks.all():
        in_allocation_time_blocks = (Q(meetings__time_block__day=allocation_time_block.day)
            & Q(meetings__time_block__start_end_time__start__lte=allocation_time_block.start_end_time.end)
            & Q(meetings__time_block__start_end_time__end__gte=allocation_time_block.start_end_time.start)
            )
        
        allocation_start = allocation_time_block.start_end_time.start
        allocation_end = allocation_time_block.start_end_time.end

        cases = Case(
            When(meetings__time_block__start_end_time__end__lt=allocation_end, 
                then=Case(
                    When(meetings__time_block__start_end_time__start__gt=allocation_start,
                        then=F('meetings__time_block__start_end_time__end') - F('meetings__time_block__start_end_time__start')),
                    default=F('meetings__time_block__start_end_time__end') - Value(allocation_start, output_field=TimeField())
                    ),
            ),
            default=Case(
                When(meetings__time_block__start_end_time__start__gt=allocation_start,
                then=Value(allocation_end, output_field=TimeField()) - F('meetings__time_block__start_end_time__start')
                ),
                default=Value(allocation_end, output_field=TimeField()) - Value(allocation_start, output_field=TimeField())
            )
        )
        ann = sections.annotate(total_overlapped_time=Sum(cases,filter=in_allocation_time_blocks)).exclude(total_overlapped_time=None).values('pk', 'total_overlapped_time')
        for section in ann.all():
            prev_allocation_overlap = allocation_overlaps.get(section['pk'], timedelta())
            allocation_overlaps[section['pk']] = prev_allocation_overlap + section['total_overlapped_time']
    
    sections: list[Section] = []
    for section, overlap in allocation_overlaps.items():
        if overlap >= timedelta(hours=2, minutes=30):
            sections.append(Section.objects.get(pk=section))

    return sections

def get_sections_by_overlapping_duration_course(sections: QuerySet, allocation_group: AllocationGroup):
    allocation_time_blocks = allocation_group.time_blocks

    allocation_overlaps = {}

    for allocation_time_block in allocation_time_blocks.all():
        in_allocation_time_blocks = (Q(meetings__time_block__day=allocation_time_block.day)
            & Q(meetings__time_block__start_end_time__start__lte=allocation_time_block.start_end_time.end)
            & Q(meetings__time_block__start_end_time__end__gte=allocation_time_block.start_end_time.start)
            )
        
        allocation_start = allocation_time_block.start_end_time.start
        allocation_end = allocation_time_block.start_end_time.end

        cases = Case(
            When(meetings__time_block__start_end_time__end__lt=allocation_end, 
                then=Case(
                    When(meetings__time_block__start_end_time__start__gt=allocation_start,
                        then=F('meetings__time_block__start_end_time__end') - F('meetings__time_block__start_end_time__start')),
                    default=F('meetings__time_block__start_end_time__end') - Value(allocation_start, output_field=TimeField())
                    ),
            ),
            default=Case(
                When(meetings__time_block__start_end_time__start__gt=allocation_start,
                then=Value(allocation_end, output_field=TimeField()) - F('meetings__time_block__start_end_time__start')
                ),
                default=Value(allocation_end, output_field=TimeField()) - Value(allocation_start, output_field=TimeField())
            )
        )
        ann = sections.annotate(total_overlapped_time=Sum(cases,filter=in_allocation_time_blocks)).exclude(total_overlapped_time=None).values('pk', 'total_overlapped_time')
        for section in ann.all():
            prev_allocation_overlap = allocation_overlaps.get(section['pk'], timedelta())
            allocation_overlaps[section['pk']] = prev_allocation_overlap + section['total_overlapped_time']
    
    sections: list[Section] = []
    for section, overlap in allocation_overlaps.items():
        if overlap >= timedelta(hours=2, minutes=30):
            sections.append(Section.objects.get(pk=section))

    courses = set()
    for section in sections:
        courses.add(section.course.pk)
    return len(courses)

def count_section_by_overlapping_duration(sections: QuerySet, allocation_group: AllocationGroup):
    return len(get_sections_by_overlapping_duration(sections, allocation_group))

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

    sections = Section.objects.filter(term=term, course__subject__department=department)
    
    time_blocks = TimeBlock.objects.exclude(number=None)
    
    numbers: dict[int, dict[str, dict[str, dict]]] = {}

    # generating the allocation group data
    numbers_allo_group: dict[int, dict] = {}
    for department_allocation in DepartmentAllocation.objects.filter(department=department).all():
        number_dict = {}

        number_dict["count"] = get_sections_by_overlapping_duration_course(sections=sections, allocation_group=department_allocation.allocation_group)
        number_dict["max"] = department_allocation.number_of_classrooms
        numbers_allo_group[department_allocation.allocation_group.pk] = number_dict


    for time_block in time_blocks.all():
        department_allo: AllocationGroup = time_block.allocation_group
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
    allocation_group = AllocationGroup.objects.get(pk=request.GET.get('allocation_group'))
    sections = Section.objects.filter(course__subject__department=department, term=term)
    sections_list = get_sections_by_overlapping_duration(sections, allocation_group)

    sections_html = render(request, "sections.html", {"sections": sections_list, "allocation": True}).content.decode()
    
    response_data['ok'] = True
    response_data['sections_html'] = sections_html

    return JsonResponse(response_data)