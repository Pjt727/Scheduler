# Creates DB instances of /static/*.csv if they are not already created
from django.conf import settings
import claim.models as MaristDB
import pandas as pd
from functools import lru_cache
import datetime
import ast


# helper functions
def add_buildings(buildings_df: pd.DataFrame) -> None:
    for _, build_row in buildings_df.iterrows():

        MaristDB.Building.objects.get_or_create(name=build_row["name"], code=build_row["code"])

def add_departments(department_df: pd.DataFrame) -> None:
    for _, dep_row in department_df.iterrows():
        MaristDB.Department.objects.get_or_create(name=dep_row["name"], code=dep_row["code"])

def add_start_end_times(start_end_times_df: pd.DataFrame) -> None:
    for _, time_row in start_end_times_df.iterrows():
        MaristDB.StartEndTime.objects.get_or_create(start=time_row["start"], end=time_row["end"])
        
def add_time_blocks(time_block_df: pd.DataFrame) -> None:
    for _, timeb_row in time_block_df.iterrows():
        MaristDB.TimeBlock.objects.get_or_create(
            start_end_time=timeb_row["start_end_time"],
            number=timeb_row["number"], 
            day=timeb_row["day"]
        )
        
def add_allocation_groups(allocation_group_df: pd.DataFrame) -> None:
    for _, allo_row in allocation_group_df.iterrows():
        add_allo_group = False
        time_block_populated = False
        allo_group = MaristDB.AllocationGroup()
        time_blocks = allo_row["time_blocks"]
        for time_block in time_blocks:
            if time_block.allocation_group is None:
                add_allo_group = True
                time_block.allocation_group = allo_group
                continue
            time_block_populated = True
        if add_allo_group and time_block_populated:
            raise ValueError("A set of time blocks' allocation group was partially loaded")
        if add_allo_group: 
            allo_group.save()
            for time_block in time_blocks:
                time_block.save()

def add_department_allocations(department_allocation: pd.DataFrame) -> None:
    for _, dep_allo_row in department_allocation.iterrows():
        MaristDB.DepartmentAllocation.objects.get_or_create(
            department=dep_allo_row['department'],
            allocation_group=dep_allo_row['allocation_group'],
            number_of_classrooms=dep_allo_row['allocation']
        )
    
# driver function
def create_all():
    STATIC_DATA_PATH: str = f"{settings.BASE_DIR}/banner/data/static"

    # Loading data frames and creating/ getting objects

    # Buildings
    add_buildings(pd.read_csv(f"{STATIC_DATA_PATH}/Building.csv"))

    # Departments
    department_df: pd.DataFrame = pd.read_csv(f"{STATIC_DATA_PATH}/Department.csv")
    add_departments(department_df)

    # Start end times
    def time_convertor(time_in_minutes) -> datetime.time:
        hours = int(time_in_minutes) // 60
        minutes = int(time_in_minutes) % 60
        return datetime.time(hour=hours, minute=minutes)
    start_end_times_df: pd.DataFrame = pd.read_csv(f"{STATIC_DATA_PATH}/StartEndTime.csv", converters={"start": time_convertor, "end": time_convertor})
    add_start_end_times(start_end_times_df)

    # Time blocks
    @lru_cache
    def start_end_time_convertor(start_end_time) -> MaristDB.StartEndTime:
        time_row = start_end_times_df.iloc[int(start_end_time)]
        return MaristDB.StartEndTime.objects.get(start=time_row["start"], end=time_row["end"])
    time_blocks_df: pd.DataFrame = pd.read_csv(f"{STATIC_DATA_PATH}/TimeBlock.csv", converters={"start_end_time": start_end_time_convertor})
    add_time_blocks(time_blocks_df)

    # Department time block allocations
    def time_blocks_convertor(time_block):
        time_blocks: list[int] = ast.literal_eval(time_block)
        time_blocks: map[pd.Series] = map( lambda t_id: time_blocks_df.iloc[t_id], time_blocks)
        time_blocks: map[MaristDB.TimeBlock] = map(lambda t: 
                   (MaristDB.TimeBlock.objects.get(start_end_time=t["start_end_time"], number=t["number"], day=t["day"])),
                time_blocks)
        return list(time_blocks)
    allocation_group_df = pd.read_csv(f"{STATIC_DATA_PATH}/AllocationGroup.csv", converters={
        "time_blocks": time_blocks_convertor})
    add_allocation_groups(allocation_group_df)
    

    @lru_cache
    def department_convertor(department) -> MaristDB.Department:
        return MaristDB.Department.objects.get(code=department)
    @lru_cache
    def allocation_group_convertor(allocation_group) -> list[MaristDB.AllocationGroup]:
        allocation_group_row = allocation_group_df.iloc[int(allocation_group)]
        return list(allocation_group_row["time_blocks"])[0].allocation_group
    
    add_department_allocations(pd.read_csv(f"{STATIC_DATA_PATH}/DepartmentAllocation.csv", converters={
        "department": department_convertor,
        "allocation_group": allocation_group_convertor,
    }))
    
