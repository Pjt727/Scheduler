# Creates DB instances of /static/*.csv if they are not already created
from django.conf import settings
import claim.models as MaristDB
import pandas as pd
from functools import lru_cache
import datetime
import ast

# mfw "get_or_create" exists :/ I'm too lazy to change it maybe

# helper functions
def add_buildings(buildings_df: pd.DataFrame) -> None:
    for _, build_row in buildings_df.iterrows():
        if MaristDB.Building.objects.filter(code=build_row["code"]): continue
        MaristDB.Building(name=build_row["name"], code=build_row["code"]).save()

def add_departments(department_df: pd.DataFrame) -> None:
    for _, dep_row in department_df.iterrows():
        if MaristDB.Department.objects.filter(code=dep_row["code"]).exists(): continue
        MaristDB.Department(name=dep_row["name"], code=dep_row["code"]).save()

def add_start_end_times(start_end_times_df: pd.DataFrame) -> None:
    for _, time_row in start_end_times_df.iterrows():
        if MaristDB.StartEndTime.objects.filter(start=time_row["start"], end=time_row["end"]).exists(): continue
        MaristDB.StartEndTime(start=time_row["start"], end=time_row["end"]).save()
        
def add_time_blocks(time_block_df: pd.DataFrame) -> None:
    for _, timeb_row in time_block_df.iterrows():
        if MaristDB.TimeBlock.objects.filter(start_end_time=timeb_row["start_end_time"], number=timeb_row["number"], day=timeb_row["day"]): continue
        MaristDB.TimeBlock(start_end_time=timeb_row["start_end_time"], number=timeb_row["number"], day=timeb_row["day"]).save()
        
def add_allocation_groups(allocation_group_df: pd.DataFrame) -> None:
    for _, allo_row in allocation_group_df.iterrows():
        add_allo_group = False
        time_block_populated = False
        allo_group = MaristDB.AllocationGroup(department=allo_row["department"], number_of_classrooms=allo_row["allocation"])
        time_blocks = list(allo_row["time_blocks"])
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
    @lru_cache
    def time_blocks_convertor(time_block):
        time_blocks: list[int] = ast.literal_eval(time_block)
        time_blocks: map[pd.Series] = map( lambda t_id: time_blocks_df.iloc[t_id], time_blocks)
        return map(lambda t: 
                   (MaristDB.TimeBlock.objects.get(start_end_time=t["start_end_time"], number=t["number"], day=t["day"])),
                time_blocks)
    @lru_cache
    def department_convertor(department) -> MaristDB.Department:
        return MaristDB.Department.objects.get(code=department)
    add_allocation_groups(pd.read_csv(f"{STATIC_DATA_PATH}/AllocationGroup.csv", converters={
        "time_blocks": time_blocks_convertor, "department": department_convertor}))
    
