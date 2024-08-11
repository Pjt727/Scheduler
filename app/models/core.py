from sqlalchemy import ForeignKey, Integer, String, Boolean, Enum, ForeignKeyConstraint, DateTime
from sqlalchemy.sql.expression import case
from sqlalchemy.orm import Mapped, validates
from sqlalchemy.orm import mapped_column, relationship
from models.config import session, Base
import enum
from datetime import time, datetime
from typing import Optional, List
###############################
# Core is everything that gets mapped from banner
#     and all default information
#
# Notes:
#  1. unique id's are useful in place of composite pk's for lookups (forms and such); still,
#     when possible composite keys are used for database integrity
###############################


class Professor(Base):
    __tablename__ = "Professors"
    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String())
    last_name: Mapped[str] = mapped_column(String())
    email_name: Mapped[Optional[str]] = mapped_column(String(), unique=True)
    title: Mapped[str] = mapped_column(String(), default="Professor")

    sections: Mapped[List["Section"]] = relationship(back_populates="professor")

class Building(Base):
    __tablename__ = "Buildings"
    code: Mapped[str] = mapped_column(String(length=2), primary_key=True)
    name: Mapped[str] = mapped_column(String())

    rooms: Mapped[List["Room"]] = relationship(back_populates="building")


class RoomClassification(enum.Enum):
    LAB = "Lab"
    LECTURE = "Lecture"

class Room(Base):
    __tablename__ = "Rooms"
    id: Mapped[int] = mapped_column(Integer(), autoincrement=True, unique=True)
    number: Mapped[int] = mapped_column(String(), primary_key=True)
    building_code: Mapped[str] = mapped_column(String(), ForeignKey("Buildings.code"), primary_key=True)
    capacity: Mapped[int] = mapped_column(String(length=2), default=0)
    classification: Mapped[enum.Enum] = mapped_column(Enum(RoomClassification))
    is_general_purpose: Mapped[bool] = mapped_column(Boolean())

    building: Mapped["Building"] = relationship(back_populates="rooms")

class Day(enum.Enum):
    MON = "Monday"
    TUE = "Tuesday"
    WED = "Wednesday"
    THU = "Thursday"
    FRI = "Friday"
    SAT = "Saturday"
    SUN = "Sunday"

# time is set up as minutes since EST 00:00
#   to avoid dealing with timezones and make checks easier
class TimeBlock(Base):
    __tablename__ = "TimeBlocks"
    id: Mapped[int] = mapped_column(Integer(), autoincrement=True, unique=True)
    day: Mapped[Day] = mapped_column(Enum(Day), primary_key=True)
    number: Mapped[int] =mapped_column(Integer(), primary_key=True) 
    start_minutes_from_est: Mapped[int] = mapped_column(Integer())
    end_minutes_from_est: Mapped[int] = mapped_column(Integer())

    school_allocations: Mapped["SchoolAllocation"] = relationship(back_populates="time_blocks")

    @validates('end_minutes_from_est')
    def validate_end_time(self, _, end_minutes_from_est):
        if int(end_minutes_from_est) <= int(self.start_minutes_from_est):
            raise ValueError("End time must be greater than start time")
        return end_minutes_from_est

    @property
    def start_time(self) -> time:
        hours, minutes = divmod(int(self.start_minutes_from_est), 60)
        return time(hours, minutes)

    @property
    def end_time(self) -> time:
        hours, minutes = divmod(int(self.end_minutes_from_est), 60)
        return time(hours, minutes)

# Marist really blurs the line in their communication on what a school versus
#   a deparment really is...
# There is no list of "departments" that I could find, but I was told it was valuable
#   to group things under a "deparment" (a smaller group) than school
#   so "departments" will be implement as a group of subjects defined by heads
#   and do not exist in this core file
class School(Base):
    __tablename__ = "Schools"
    code: Mapped[str] = mapped_column(String(), primary_key=True)
    name: Mapped[str] = mapped_column(String())

    allocations: Mapped[List["SchoolAllocation"]] = relationship(back_populates="school")
    subjects: Mapped[List["Subject"]] = relationship(back_populates="school")

# Registrar may try to say this is "deparment" allocationbut it is school
#    allocation
# Keep in mind there is not history of school allocations so if this changes
#    views on previous years using these values my also change
# There would have to be history both this change and of rooms to 
#    correctly calculate allocation numbers
class SchoolAllocation(Base):
    __tablename__ = "SchoolAllocations"
    id: Mapped[int] = mapped_column(Integer(), autoincrement=True, unique=True)
    school_code: Mapped[str] = mapped_column(String(), ForeignKey("Schools.code"), primary_key=True)
    time_block_number: Mapped[int] = mapped_column(String(), primary_key=True)
    time_block_day: Mapped[Day] = mapped_column(Enum(Day), primary_key=True)

    time_block: Mapped["TimeBlock"] = relationship(back_populates="school_allocations")
    school: Mapped["School"] = relationship(back_populates="allocations")

    _fk_c = ForeignKeyConstraint(
            ["time_block_number", "time_block_day"],
            ["TimeBlocks.number", "TimeBlocks.day"]
            )
    __table_args__ = (_fk_c,)


class Subject(Base):
    __tablename__ = "Subjects"
    code: Mapped[str] = mapped_column(String(length=10), primary_key=True)
    school_code: Mapped[str] = mapped_column(String(), ForeignKey("Schools.code"))
    description: Mapped[Optional[str]] = mapped_column(String())

    school: Mapped["School"] = relationship(back_populates="subjects")
    courses: Mapped[List["Course"]] = relationship(back_populates="subject")

class Course(Base):
    __tablename__ = "Courses"
    SEARCH_INTERVAL = 10
    id: Mapped[int] = mapped_column(Integer(), autoincrement=True)
    code: Mapped[str] = mapped_column(String(), primary_key=True)
    subject_code: Mapped[int] = mapped_column(String(), ForeignKey("Subjects.code"), primary_key=True)
    credits: Mapped[int] = mapped_column(Integer())
    name: Mapped[str] = mapped_column(String())
    description: Mapped[Optional[str]] = mapped_column(String())
    banner_id: Mapped[Optional[str]] = mapped_column(String())

    subject: Mapped["Subject"] = relationship(back_populates="courses")
    sections: Mapped[List["Section"]] = relationship(back_populates="coures")


class Season(enum.Enum):
    WINTER = "Winter"
    SPRING = "Spring"
    SUMMER = "Summer"
    FALL = "Fall"

class Term(Base):
    __tablename__ = "Terms"
    id: Mapped[int] = mapped_column(Integer(), autoincrement=True, unique=True)
    season: Mapped[Season] = mapped_column(Enum(Season), primary_key=True)
    year: Mapped[int] = mapped_column(Integer(), primary_key=True)

    sections: Mapped[List["Section"]] = relationship(back_populates="term")

    @staticmethod
    def recent_order() -> tuple:
        '''used to get the most recent terms'''
        return Term.year.desc(), case(
            (Term.season == Season.SUMMER, 4),
            (Term.season == Season.SPRING, 3),
            (Term.season == Season.WINTER, 2),
            (Term.season == Season.FALL, 1),
            else_=0).desc()


class Section(Base):
    __tablename__ = "Sections"
    SEARCH_INTERVAL = 10
    id: Mapped[int] = mapped_column(Integer(), autoincrement=True, unique=True)
    number: Mapped[str] = mapped_column(String(), primary_key=True)
    course_code: Mapped[str] = mapped_column(String(), primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(), primary_key=True)
    term_season: Mapped[Season] = mapped_column(String(), primary_key=True)
    term_year: Mapped[Season] = mapped_column(Integer(), primary_key=True)
    professor_id: Mapped[Optional[Professor]] = mapped_column(Integer(), ForeignKey("Professors.id"))
    campus: Mapped[str] = mapped_column(String())
    soft_capacity: Mapped[int] = mapped_column(Integer(), default=0)
    banner_course: Mapped[Optional[str]] = mapped_column(String())

    course: Mapped["Course"] = relationship(back_populates="sections")
    term: Mapped["Term"] = relationship(back_populates="sections")
    professor: Mapped["Professor"] = relationship(back_populates="sections")

    _fk_c_to_term = ForeignKeyConstraint(
            ["term_season", "term_year"],
            ["Terms.season", "Terms.year"],
            )
    _fk_c_to_course = ForeignKeyConstraint(
            ["course_code", "subject_code"],
            ["Courses.code", "Courses.subject_code"],
            )
    __table_args__ = (_fk_c_to_term, _fk_c_to_course,)


class Meeting(Base):
    __tablename__ = "Meetings"
    # There is no functional dependencies within meeting so must have an autoincrementing key
    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    section_number: Mapped[str] = mapped_column(String())
    course_code: Mapped[str] = mapped_column(String())
    subject_code: Mapped[str] = mapped_column(String())
    term_season: Mapped[Season] = mapped_column(String())
    term_year: Mapped[Season] = mapped_column(Integer())
    day: Mapped[Optional[Day]] = mapped_column(Enum(Day))
    start_minutes_from_est: Mapped[Optional[int]] = mapped_column(Integer())
    end_minutes_from_est: Mapped[Optional[int]] = mapped_column(Integer)
    room_number: Mapped[Optional[str]] = mapped_column(String(), )
    # building code is a fk for builds and part of the composite key for room
    building_code: Mapped[Optional[str]] = mapped_column(String(), ForeignKey("Buildings.code"))
    professor_id: Mapped[Optional[Professor]] = mapped_column(Integer(), ForeignKey("Professors.id"))
    #####
    # these probably wont matter all that much
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime())
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime())
    style_code: Mapped[Optional[str]] = mapped_column(String(), default="Lec")
    style_description: Mapped[Optional[str]] = mapped_column(String(), default="Lecture")

    _fk_c_to_section = ForeignKeyConstraint(
            ["section_number", "course_code", "subject_code", "term_season", "term_year"],
            ["Sections.number", "Sections.course_code", "Sections.subject_code", "Sections.term_season", "Sections.term_year"],
            )
    _fk_c_to_room = ForeignKeyConstraint(
            ["room_number", "building_code"],
            ["Sections.number", "Sections.course_code"],
            )

    __table_args__ = (_fk_c_to_room, _fk_c_to_section)

    @staticmethod
    def day_time_sort() -> tuple:
        return case(
                (Meeting.day == Day.MON, 1),
                (Meeting.day == Day.TUE, 2),
                (Meeting.day == Day.WED, 3),
                (Meeting.day == Day.THU, 4),
                (Meeting.day == Day.FRI, 5),
                (Meeting.day == Day.SAT, 6),
                (Meeting.day == Day.SUN, 7),
                else_=8
                ).asc(), Meeting.start_minutes_from_est.asc()

