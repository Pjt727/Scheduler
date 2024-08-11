from data.helpers import *
from collections import Counter
from models.config import session
from models.core import *
import os
import json
from dataclasses import dataclass, field, fields
from typing import List
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc  import IntegrityError
import re

BANNER_DIR = os.path.join("data", "banner")

@dataclass
class Faculty:
    bannerId: str
    displayName: str
    primaryIndicator: bool
    emailAddress: str = ""

    @classmethod
    def from_dict(cls, env):      
        return cls(**{
            k: v for k, v in env.items() 
            if k in [f.name for f in fields(cls)]
        })

@dataclass
class MeetingTime:
    category: str
    endDate: str
    friday: bool
    meetingType: str
    meetingTypeDescription: str
    monday: bool
    saturday: bool
    startDate: str
    sunday: bool
    thursday: bool
    tuesday: bool
    wednesday: bool
    hoursWeek: float = 0

    @classmethod
    def from_dict(cls, env):
        env = env["meetingTime"]
        return cls(**{
            k: v for k, v in env.items() 
            if k in [f.name for f in fields(cls)]
        })

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
    meetingsTimes: List[MeetingTime] = field(default_factory=list)
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
        return cls(**{
            k: v for k, v in env.items() 
            if k in [f.name for f in fields(cls)]
        })

def merge_sections(term: Term, courses: set[Course], banner_sections: list[BannerSection]):
    professors: set[Professor] = set()
    schools: set[School] = set()
    subjects: set[Subject] = set()
    sections: set[Section] = set()
    buildings: set[Building] = set()
    room: set[Room] = set()
    meetings: list[Meeting] = []

    for banner_section in banner_sections:
        # professors
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
            professors.add(Professor(first_name=first_name,
                      last_name=last_name, email=email_address))
    # probably would be fast to use
    #   https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#insert-on-conflict-upsert
    # but this is easier
    for professor in professors:
        insert_prof = insert(Professor).values(
                first_name=professor.first_name,
                last_name=professor.last_name,
                email=professor.email
                )
        update_prof = insert_prof.on_conflict_do_update(
                index_elements=[ Professor.email ],
                set_=dict(last_name=professor.last_name, first_name=professor.first_name)
                )
        session.execute(update_prof)

    
    session.commit()


def facilitate_section_merge():
    files = os.listdir(BANNER_DIR)
    term_pattern = r"(Fall|Spring|Winter|Summer)(2[0-9]{3})"
    for file_name in files:
        if not file_name.startswith("sections"): continue
        sections: list[BannerSection] = []
        matches = re.search(term_pattern, file_name)
        assert matches is not None
        term_season = matches.group(1)
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
                meetingsFaculty = [MeetingTime.from_dict(m) for m in section["meetingsFaculty"]]
                faculty = [Faculty.from_dict(m) for m in section["faculty"]]
                section["meetingsTimes"] = meetingsFaculty
                section["faculty"] = faculty
                sections.append(BannerSection.from_dict(section))
        merge_sections(term, set(), sections)
        print_info(f"Finished loading banner classes for {term_season} {term_year}")

