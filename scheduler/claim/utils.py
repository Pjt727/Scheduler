from .models import *
from datetime import timedelta

def will_exceed_department_allocation(start_time: timedelta, end_time: timedelta, day: str, department: Department, term: Term) -> bool:
    group_time_blocks = TimeBlock.objects.filter(number__isnull=True).filter(
        day=day,
        start_end_time__start__lte = start_time,
        start_end_time__end__gte = end_time
    )

    department_allocations = DepartmentAllocation.objects.filter(
        department=department,
        allocation_group__in=group_time_blocks.values('allocation_groups').all()
    )

    exceeds_department_allocation = False
    for department_allocation in department_allocations.all():
        room_count = Room.objects.filter(
            meetings__section__course__subject__department=department,
            meetings__section__term=term,
            is_general_purpose=True,
            meetings__time_block__in=department_allocation.allocation_group.time_blocks.all()
        ).distinct().count()
        if room_count >= department_allocation.number_of_classrooms:
            exceeds_department_allocation = True
    
    return exceeds_department_allocation

def get_available_rooms(building: Building, start_time: timedelta, end_time: timedelta, day: str, department: Department, term: Term, enforce_department_constraints: bool) -> QuerySet[Room]:
    open_rooms = Room.objects.filter(building=building).exclude(
        meetings__section__term=term,
        meetings__time_block__day=day,
        meetings__time_block__start_end_time__start__lte=start_time,
        meetings__time_block__start_end_time__end__gte=end_time,
    )

    if enforce_department_constraints:
        does_exceed = will_exceed_department_allocation(
            start_time=start_time,
            end_time=end_time,
            day=day,
            department=department,
            term=term
        )
        if does_exceed:
            open_rooms = open_rooms.exclude(is_general_purpose=True)
    
    return open_rooms

