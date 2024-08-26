from data.helpers import *
from collections import Counter
from models.config import session
from models.core import *
from datetime import datetime
from data.hard_coded_defaults import *
import os
import json
from dataclasses import dataclass, field, fields
from typing import List
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError
import re

BANNER_DIR = os.path.join("data", "banner")


@dataclass
class CourseData:
    id: int
    termEffective: str
    courseNumber: str
    subject: str
    subjectCode: str
    college: str
    collegeCode: str
    department: str
    departmentCode: str
    courseTitle: str
    creditHourLow: int
    lectureHourLow: int
    billHourLow: int
    subjectDescription: str
    termStart: str
    termEnd: str
    preRequisiteCheckMethodCde: str

    @classmethod
    def from_dict(cls, env):
        return cls(**{k: v for k, v in env.items() if k in [f.name for f in fields(cls)]})


@dataclass
class Faculty:
    bannerId: str
    displayName: str
    primaryIndicator: bool
    emailAddress: str = ""

    @classmethod
    def from_dict(cls, env):
        return cls(**{k: v for k, v in env.items() if k in [f.name for f in fields(cls)]})


@dataclass
class MeetingInstance:
    category: str
    endDate: str
    friday: bool
    monday: bool
    saturday: bool
    startDate: str
    sunday: bool
    thursday: bool
    tuesday: bool
    wednesday: bool
    building: str | None = None
    buildingDescription: str | None = None
    room: str | None = None
    meetingType: str | None = None
    meetingTypeDescription: str | None = None
    beginTime: str | None = None
    endTime: str | None = None
    hoursWeek: float = 0

    @classmethod
    def from_dict(cls, env):
        env = env["meetingTime"]
        return cls(**{k: v for k, v in env.items() if k in [f.name for f in fields(cls)]})


@dataclass
class BannerSection:
    id: int
    term: str
    termDesc: str
    courseReferenceNumber: str
    partOfTerm: str
    courseNumber: str
    subject: str
    subjectDescription: str
    sequenceNumber: str
    campusDescription: str
    courseTitle: str
    creditHourLow: int
    faculty: List[Faculty] = field(default_factory=list)
    meetings: List[MeetingInstance] = field(default_factory=list)
    # possibly unused variables
    # sectionAttributes: List[dict] = field(default_factory=list)
    # scheduleTypeDescription: str = ""
    # maximumEnrollment: int = 0
    # enrollment: int = 0
    # seatsAvailable: int = 0
    # waitCapacity: int = 0
    # waitAvailable: int = 0
    # openSection: bool = True
    # creditHours: int = 0
    # crossList: str = ""
    # crossListCapacity: int = 0
    # crossListCount: int = 0
    # crossListAvailable: str = ""

    @classmethod
    def from_dict(cls, env):
        return cls(**{k: v for k, v in env.items() if k in [f.name for f in fields(cls)]})


# ORM sqlite docs on upserts
#    https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html#orm-upsert-statements
# note that defaults will not populate when doing this because those defaults are rendered by python
def merge_sections(term: Term, banner_sections: list[BannerSection]):
    # we need to get the professor here first because we want to treat
    #   first_name, last_name as unqiue ONLY if email is None
    # There is no way to do that in the database besides with triggers and besides
    #   we only really want this for this automated data entry
    select_prof = select(Professor)
    # ok i know this looks weird but the __hash__and __eq__ of professor
    #    is the first_name last_name email so that this will work for adding professor
    #    and this is needed to retreive the professor associated in the database instead
    #    of the random object we created
    old_professors = {professor: professor for professor in session.scalars(select_prof).all()}
    old_professors_by_email = {
        professor.email: professor for professor in session.scalars(select_prof).all()
    }
    new_professors_by_email: dict[str, Professor] = {}
    new_professors: dict[Professor, Professor] = {}
    subjects: list[dict] = []
    buildings: list[dict] = []
    rooms: list[dict] = []
    courses: list[dict] = []
    sections: list[Section] = []
    meetings: list[Meeting] = []

    for banner_section in banner_sections:
        # professors
        professor: Professor | None = None
        for fac in banner_section.faculty:
            names = fac.displayName.split(", ")
            if len(names) > 1:
                last_name, first_name = names
            elif len(names) == 1:
                last_name, first_name = "", names[0]
            else:
                first_name, last_name = "", ""

            email_address = fac.emailAddress
            if not email_address:
                email_address = None
            professor = Professor(first_name=first_name, last_name=last_name, email=email_address)
            # cursed - remember this is messy bc professor doesnt have a good PK
            if professor in old_professors:
                professor = old_professors.get(professor)
            elif email_address in old_professors_by_email:
                professor = old_professors_by_email[email_address]
            elif professor in new_professors:
                professor = new_professors.get(professor)
            elif email_address in new_professors_by_email:
                professor = new_professors_by_email[email_address]
            else:
                new_professors[professor] = professor
                if email_address is not None:
                    new_professors_by_email[email_address] = professor
        # subjects
        subject_dict = {
            "code": banner_section.subject,
            "description": banner_section.subjectDescription,
        }
        if subject_dict not in subjects:
            subjects.append(subject_dict)
        # adding courses
        course_dict = {
            "code": banner_section.courseNumber,
            "subject_code": subject_dict["code"],
            "credits": banner_section.creditHourLow,
            "name": banner_section.courseTitle,
            # from courses json you could myabe get desc so better to
            #    keep that information that this
            "description": None,
            "banner_id": banner_section.courseReferenceNumber,
        }
        if course_dict not in courses:
            courses.append(course_dict)

        # making sections
        section_dict = {
            "number": banner_section.sequenceNumber,
            "course_code": course_dict["code"],
            "subject_code": course_dict["subject_code"],
            "term": term,
            # needed that professor hack to get the associate with the new
            #   prof object OR the one that was in the db instead of the
            #   new prof object that would not be added
            "professor": professor,
            "campus": banner_section.campusDescription,
            "soft_capacity": 0,
            "banner_course": banner_section.courseReferenceNumber,
        }
        section = Section(**section_dict)
        # there should reall be no overlapping sections on pk's
        #    but comment this to allow them
        # if section in sections:
        #     print_warning("Duplicate Section:")
        #     print(section.as_dict())
        #     continue
        sections.append(section)
        # building/ room / meeting stuff
        for banner_meeting in banner_section.meetings:
            # buildings
            building_code = banner_meeting.building
            building_name = banner_meeting.buildingDescription
            if building_code is not None:
                building_dict = {"code": building_code, "name": building_name}
                if building_dict not in buildings:
                    buildings.append(building_dict)
            if banner_meeting.meetingType == "LEC":
                classifcation = MeetingClassification.LECTURE
            elif banner_meeting.meetingType == "LAB":
                classifcation = MeetingClassification.LAB
            elif banner_meeting.meetingType == "WEB":
                classifcation = MeetingClassification.WEB
            else:
                classifcation = None
            # rooms

            room_number = banner_meeting.room
            if room_number is not None and building_code is not None:
                room_dict = {
                    "building_code": building_code,
                    "classification": classifcation,
                    "number": room_number,
                    "is_general_purpose": Room.default_is_general_purpose,
                    "capacity": Room.default_capacity,
                }
                if room_dict not in rooms:
                    rooms.append(room_dict)
            ## making meetings
            day_is_day: list[tuple[Day, bool]] = [
                (Day.MON, banner_meeting.monday),
                (Day.TUE, banner_meeting.tuesday),
                (Day.WED, banner_meeting.wednesday),
                (Day.THU, banner_meeting.thursday),
                (Day.FRI, banner_meeting.friday),
                (Day.SAT, banner_meeting.saturday),
                (Day.SUN, banner_meeting.sunday),
            ]
            # one meeting instance may map to multiple days
            for day, is_day in day_is_day:
                if not is_day:
                    continue
                start_time = None
                end_time = None
                bt = banner_meeting.beginTime
                et = banner_meeting.endTime
                if bt is not None and et is not None:
                    start_time = int(bt[0:2]) * 60 + int(bt[2:])
                    end_time = int(et[0:2]) * 60 + int(et[2:])
                meeting_dict = {
                    "section_number": section_dict["number"],
                    "course_code": course_dict["code"],
                    "subject_code": subject_dict["code"],
                    "day": day,
                    "professor": professor,
                    "start_minutes_from_est": start_time,
                    "end_minutes_from_est": end_time,
                    "room_number": room_number,
                    "building_code": building_code,
                    "start_date": datetime.strptime(banner_meeting.startDate, "%m/%d/%Y"),
                    "end_date": datetime.strptime(banner_meeting.endDate, "%m/%d/%Y"),
                    "style_code": str(classifcation),
                    "term": term,
                }
                meeting = Meeting(**meeting_dict)
                meetings.append(meeting)

    ## upserting professors
    update_prof = sqlite_insert(Professor).values(
        # dont ask me about this ever
        [
            {p1: p2 for p1, p2 in professor.as_dict().items() if p2 is not None and p1 != "email"}
            for professor in new_professors
        ]
    )
    update_prof = update_prof.on_conflict_do_nothing(
        # If two professors have the same first and last name as well as None for email
        #    then they are treated as the same professor (no reall good fix for this)
        #    unless we maybe use banner id but idk if that will even work that well
        index_elements=[Professor.email],
    )
    session.execute(update_prof)
    ## adding new subjects doing nothing if the subject code is already there
    #      this is because we have no way of getting the correct school to attribute this subject
    add_subjects = sqlite_insert(Subject).values(subjects)
    add_subjects = add_subjects.on_conflict_do_nothing()
    session.execute(add_subjects)
    ## adding new buildings
    if buildings:
        add_buildings = sqlite_insert(Building).values(buildings)
        add_buildings = add_buildings.on_conflict_do_nothing()
        session.execute(add_buildings)
    ## adding rooms
    if rooms:
        add_rooms = sqlite_insert(Room).values(rooms)
        add_rooms = add_rooms.on_conflict_do_nothing()
        session.execute(add_rooms)
    ## adding courses
    add_courses = sqlite_insert(Course).values(courses)
    add_courses = add_courses.on_conflict_do_nothing()
    session.execute(add_courses)
    ## adding sections and meetings
    session.add_all(sections)
    session.add_all(meetings)

    session.commit()


def facilitate_section_merge():
    files = os.listdir(BANNER_DIR)
    term_pattern = r"(Fall|Spring|Winter|Summer)(2[0-9]{3})"
    for file_name in files:
        if not file_name.startswith("sections"):
            continue
        sections: list[BannerSection] = []
        matches = re.search(term_pattern, file_name)
        assert matches is not None
        term_season = matches.group(1).upper()
        term_year = int(matches.group(2))
        try:
            term = Term(season=term_season, year=term_year)
            session.add(term)
            session.commit()
        except IntegrityError:
            print_warning(f"Skipping term {term_season} {term_year} because it already exists")
            session.rollback()
            continue
        print_info(f"Loading banner classes for {term_season} {term_year}")
        with open(os.path.join(BANNER_DIR, file_name), "r") as file:
            data = json.load(file)
            for section in data:
                meetingsFaculty = [MeetingInstance.from_dict(m) for m in section["meetingsFaculty"]]
                faculty = [Faculty.from_dict(m) for m in section["faculty"]]
                section["meetings"] = meetingsFaculty
                section["faculty"] = faculty
                sections.append(BannerSection.from_dict(section))
        merge_sections(term, sections)

        print_info(f"Finished loading banner classes for {term_season} {term_year}")


def course_merge():
    with open(os.path.join(BANNER_DIR, "courses.json")) as file:
        data = json.load(file)
        course_datas = [CourseData.from_dict(c) for c in data]
        subjects: list[dict] = []
        courses: list[dict] = []
        for course in course_datas:
            school_code = None
            for code, valid_departments in SCHOOL_CODE_AND_VALID_DEPARTMENTS:
                # college not department has literally like one different in code that
                #   completely screwed over the CMPT subject
                if course.collegeCode in valid_departments:
                    school_code = code
                    break
            subject_dict = {
                "code": course.subjectCode,
                "school_code": school_code,
                "description": course.subjectDescription.replace("amp;", ""),
            }
            # probably dont need this check since the database should take care of duplicates
            if subject_dict not in subjects:
                subjects.append(subject_dict)
            course_dict = {
                "code": course.courseNumber,
                "subject_code": course.subjectCode,
                "credits": course.creditHourLow,
                "name": course.courseTitle.replace("amp;", ""),
                # sadge theres no description
                "banner_id": course.id,
            }
            # probably dont need this check since the database should take care of duplicates
            courses.append(course_dict)

        add_subjects = sqlite_insert(Subject).values(subjects)
        add_subjects = add_subjects.on_conflict_do_update(
            set_={
                "description": add_subjects.excluded.description,
                "school_code": add_subjects.excluded.school_code,
            }
        )
        add_courses = sqlite_insert(Course).values(courses)
        add_courses = add_courses.on_conflict_do_update(
            set_={
                "description": add_courses.excluded.description,
                "credits": add_courses.excluded.credits,
            }
        )
        session.execute(add_subjects)
        session.execute(add_courses)
        session.commit()


def load_everything_from_banner():
    facilitate_section_merge()
    course_merge()
