# Creates DB instances of /static/*.csv if they are not already created
from django.conf import settings
import claim.models as MaristDB
import pandas as pd
from functools import lru_cache
import datetime


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
        
def add_department_time_block_allocations(department_time_block_allocations_df: pd.DataFrame) -> None:
    for _, allo_row in department_time_block_allocations_df.iterrows():
        if MaristDB.DepartmentTimeBlockAllocation.objects.filter(department=allo_row["department"], time_block=allo_row["time_block"]).exists(): continue
        MaristDB.DepartmentTimeBlockAllocation(department=allo_row["department"], time_block=allo_row["time_block"], number_of_classrooms=allo_row["allocation"]).save()

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
    def time_block_convertor(time_block) -> MaristDB.TimeBlock:
        timeb_row = time_blocks_df.iloc[int(time_block)]
        return MaristDB.TimeBlock.objects.get(start_end_time=timeb_row["start_end_time"], number=timeb_row["number"], day=timeb_row["day"])
    @lru_cache
    def department_convertor(department) -> MaristDB.Department:
        dep_row = department_df.iloc[int(department)]
        return MaristDB.Department.objects.get(code=dep_row["code"])
    add_department_time_block_allocations(pd.read_csv(f"{STATIC_DATA_PATH}/DepartmentTimeBlockAllocation.csv", converters={
        "time_block": time_block_convertor, "department": department_convertor}))
    
