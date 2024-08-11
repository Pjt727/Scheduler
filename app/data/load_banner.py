from data.helpers import *
import os
import json
from dataclasses import dataclass, field, fields
from typing import List
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
class Section:
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





def facilitate_section_merge():
    files = os.listdir(BANNER_DIR)
    for file_name in files:
        if not file_name.startswith("sections"): continue

        sections: list[Section] = []
        term_pattern = r"(Fall|Spring|Winter|Summer)(2[0-9]{3})"
        with open(os.path.join(BANNER_DIR, file_name), "r") as file:
            data = json.load(file)
            matches = re.search(term_pattern, file_name)
            assert matches is not None
            term = matches.group(1)
            year = int(matches.group(2))
            print_info(f"Loading banner classes for {term} {year}")
            for section in data:
                meetingsFaculty = [MeetingTime.from_dict(m) for m in section["meetingsFaculty"]]
                faculty = [Faculty.from_dict(m) for m in section["faculty"]]
                section["meetingsTimes"] = meetingsFaculty
                section["faculty"] = faculty
                sections.append(Section.from_dict(section))

            print_info(f"Finished loading banner classes for {term} {year}")

