# Creates DB instances of information gained from /classes/*/sections.csv and /classes/courses.csv
# That is information from each section that has been scraped from the Marist Banner system

# mfw "get_or_create" exists :/ 

from django.conf import settings
import claim.models as MaristDB
from authentication.models import Professor as MaristDB_Professor
import pandas as pd
import ast
import os
from functools import lru_cache
import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError
from django.db import connection

def add_courses(course_df: pd.DataFrame) -> None:
    for _, course_row in course_df.iterrows:
        if MaristDB.Course.objects.filter(subject=course_row["subject"], code=["number"]).exists(): continue
        MaristDB.Course(code=["number"], credits=["credit_hours"], title=["course_title"], subject=["subject"]).save()

def add_section(section_row, term: str) -> None:
        @lru_cache
        def add_professor(instructor_name: str, instructor_email: str) -> MaristDB_Professor:
            if pd.isna(instructor_name) and pd.isna(instructor_email): return None
            first_name, last_name =  (None, None) if pd.isna(instructor_name) else instructor_name.split(",", 1)
            first_name = first_name.strip()
            last_name = last_name.strip()
            instructor_email = None if instructor_email=="#" else instructor_email
            if instructor_email is None and first_name is None: return None
            if instructor_email:
                prof = MaristDB_Professor.objects.filter(email=instructor_email).first()
            elif first_name and last_name:
                prof = MaristDB_Professor.objects.filter(first_name=first_name, last_name=last_name).first()
            else:
                prof = None

            if prof is None:
                prof = MaristDB_Professor(first_name=first_name, last_name=last_name, email=instructor_email)
                prof.save()
            return prof
        
        @lru_cache
        def add_room(building: str, room_number: str, meeting_type: str) -> MaristDB.Room:
            if pd.isna(building) or (building is None) or (building=="None"): return None
            building = MaristDB.Building.objects.get(name=building)
            room = MaristDB.Room.objects.filter(building=building, number=room_number).first()
            if room: return room
            if meeting_type == "Laboratory":
                classification = MaristDB.Room.LAB
            else:
                classification = MaristDB.Room.CLASSROOM
            
            # TODO add the capacity as the max sum of all section caps that meet at a singular time slot
            room: MaristDB.Room = MaristDB.Room(number=room_number, classification=classification, capacity=0, building=building)
            room.save()
            return room

        if MaristDB.Section.objects.filter(number=section_row["section"], term=term, course=section_row["course_id"]).exists(): return
        section = MaristDB.Section(number=section_row["section"], campus=section_row["campus"], term=term, soft_cap=section_row["seat_cap"], course=section_row["course_id"])
        section.save()
        professor = add_professor(section_row["instructor"], section_row["instructor_email"])
        meeting_times: pd.DataFrame = section_row['meeting_times']

        for _, meeting_time in meeting_times.iterrows():
            
            days_col: str = meeting_time["days"]
            if (days_col is None) or (days_col.upper() == "NONE") or (MaristDB.Day.VERBOSE_TO_CODE.get(days_col) == "SA") or (MaristDB.Day.VERBOSE_TO_CODE.get(days_col) == "SU"): 
                continue

            days: list[str] = days_col.split(",") if "," in days_col else [days_col]
            start_date = datetime.datetime.strptime(meeting_time["start_date"], "%m/%d/%Y").date()
            end_date = datetime.datetime.strptime(meeting_time["end_date"], "%m/%d/%Y").date()
            start_time = datetime.datetime.strptime(meeting_time["start_time"], "%I:%M %p").time()
            end_time = datetime.datetime.strptime(meeting_time["end_time"], "%I:%M %p").time()
            for day in days:
                day_code = MaristDB.Day.VERBOSE_TO_CODE[day]
                # Creates a new time_block 
                time_block = MaristDB.TimeBlock.objects.filter(start_end_time__start=start_time, start_end_time__end=end_time, day=day_code).first()
                if time_block is None:
                    start_end_time = MaristDB.StartEndTime.objects.filter(start=start_time, end=end_time).first()
                    if start_end_time is None:
                        start_end_time = MaristDB.StartEndTime(start=start_time, end=end_time)
                        start_end_time.save()
                    time_block = MaristDB.TimeBlock(day=day_code, start_end_time=start_end_time)
                    time_block.save()
                room = add_room(building=meeting_time["building"], room_number=meeting_time["room"], meeting_type=meeting_time["meeting_type"]) if meeting_time["room"] else None
                meeting = MaristDB.Meeting(start_date=start_date, 
                                           end_date=end_date, 
                                           style=meeting_time["meeting_type"], 
                                           section=section,
                                           time_block=time_block,
                                           room=room,
                                           professor=professor)
                meeting.save()

def create_terms(terms: list[str] = [], force=False) -> tuple[list[str], list[str]]:
    # paths
    BANNER_DUMP_PATH = f"{settings.BASE_DIR}/banner/data/classes"

    @lru_cache
    def college_convertor(college: str) -> MaristDB.Department:
        if not college: return MaristDB.Department.objects.get(code="OT")
        try:
            code = college[college.rfind(" ", ) + 1:]
            return MaristDB.Department.objects.get(code=code)
        except MaristDB.Department.DoesNotExist or IndexError:
            return MaristDB.Department.objects.get(code="OT")
        
    courses_df: pd.DataFrame = pd.read_csv(f"{BANNER_DUMP_PATH}/courses.csv",
            usecols= ["course_title", "subject", "number", "college", "credit_hours", "id"],
            converters={"college": college_convertor})
    
    def add_course(course_row) -> None:
        subject = MaristDB.Subject.objects.filter(code=course_row["subject"]).first()
        if subject is None:
            new_subject = MaristDB.Subject(code=course_row["subject"], department=course_row["college"])
            new_subject.save()
            MaristDB.Course(code=course_row["number"], credits=course_row["credit_hours"], title=course_row["course_title"], subject=new_subject).save()
            return
        course = MaristDB.Course.objects.filter(code=course_row["number"], subject__code=course_row["subject"]).first()
        if course: return
        MaristDB.Course(code=course_row["number"], credits=course_row["credit_hours"], title=course_row["course_title"], subject=subject).save()
    
    course_errs = []
    for _, course_row in courses_df.iterrows():
        try:
            add_course(course_row)
        except ObjectDoesNotExist as err:
            if not force: raise CommandError(f"{err} Run with --force to silence errors.")
            course_errs.append(err)

    def convert_meeting_times(meeting_times) -> pd.DataFrame:
        meeting_times = ast.literal_eval(meeting_times)
        headers = meeting_times[0]
        if len(meeting_times) > 1:
            values = meeting_times[1:]
        else:
            values = []
        df = pd.DataFrame(values, columns=headers)
        return df
    @lru_cache
    def course_convertor(course_id) -> MaristDB.Course:
        course_df: pd.DataFrame = courses_df.loc[courses_df["id"] == int(course_id)]
        if course_df.empty:
            raise ValueError(f"Could not find course_id: {course_id}.")
        
        course_row = course_df.iloc[0]

        subject = MaristDB.Subject.objects.get(code=course_row["subject"])
        return MaristDB.Course.objects.get(code=course_row["number"], subject=subject)
    
    terms = [term for term in os.listdir(BANNER_DUMP_PATH) if os.path.isdir(os.path.join(BANNER_DUMP_PATH, term))]
    section_dfs: dict[str, pd.DataFrame] = {term: pd.read_csv(f"{BANNER_DUMP_PATH}/{term}/sections.csv", converters={"meeting_times": convert_meeting_times, "course_id": course_convertor}) for term in terms}
    
    section_errs = []
    for term, section_df in section_dfs.items():
        # sort of hacky way to put a space between the Season and year
        term = term.lower().replace("2", " 2", 1)
        season, year = term.split()
        term = MaristDB.Term.objects.filter(season=season, year=year).first()
        if term is None:
            term = MaristDB.Term(season=season, year=year)
            term.save()
        for _, section_row in section_df.iterrows():
            try:
                add_section(section_row, term)
            except ObjectDoesNotExist as err:
                if not force:
                    raise CommandError(f"{err} Run with --force to silence errors.")
                section_errs.append(err)

    return course_errs, section_errs


