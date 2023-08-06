from .models import *
from datetime import timedelta

def will_exceed_department_allocation(start_time: timedelta, end_time: timedelta, day: str, department: Department, term: Term) -> bool:
    
    group_time_blocks = TimeBlock.get_official_time_blocks(start_time, end_time, day)

    department_allocations = DepartmentAllocation.objects.filter(
        department=department,
        allocation_group__in=group_time_blocks.values('allocation_groups').all()
    )

    return any(map(lambda d_a: d_a.exceeds_allocation(term), department_allocations.all()))
