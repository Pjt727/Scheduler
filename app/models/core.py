from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Enum,
    ForeignKeyConstraint,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.sql.expression import case
from sqlalchemy.orm import Mapped, validates
from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy.util import hybridmethod, hybridproperty
from models.config import session, Base
import enum
from datetime import time, datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.users import User

###############################
# Core is everything that gets mapped from banner
#     and all default information
#
# Notes:
#  1. unique id's are useful in place of composite pk's for lookups (forms and such);
#        so use rowid from sqlite
###############################


class Professor(Base):
    __tablename__ = "Professors"
    id: Mapped[int] = mapped_column(Integer(), primary_key=True)
    first_name: Mapped[str] = mapped_column(String())
    last_name: Mapped[str] = mapped_column(String())
    email: Mapped[Optional[str]] = mapped_column(String(), unique=True)
    default_title = "Professor"
    title: Mapped[str] = mapped_column(
        String(), default=default_title, server_default=default_title
    )

    sections: Mapped[List["Section"]] = relationship(back_populates="professor")
    meetings: Mapped[List["Meeting"]] = relationship(back_populates="professor")

    user: Mapped[Optional["User"]] = relationship("User", back_populates="professor", uselist=False)

    @validates("email")
    def validate_name(self, _, value):
        if value is None:
            return value
        if any(char.isupper() for char in value):
            raise ValueError(f"Email `{value}` must be all lowercase")
        return value

    def __hash__(self):
        return hash((self.first_name, self.last_name, self.email))

    def __eq__(self, other):
        if not isinstance(other, Professor):
            return False
        return (self.first_name, self.last_name, self.email) == (
            other.first_name,
            other.last_name,
            other.email,
        )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Building(Base):
    __tablename__ = "Buildings"
    code: Mapped[str] = mapped_column(String(length=2), primary_key=True)
    name: Mapped[str] = mapped_column(String())

    rooms: Mapped[List["Room"]] = relationship(back_populates="building")
    meetings: Mapped[List["Meeting"]] = relationship(back_populates="building")

    def __hash__(self):
        return hash(self.code)

    def __eq__(self, other):
        if not isinstance(other, Building):
            return False
        return self.code == other.code


class MeetingClassification(enum.Enum):
    LAB = "Lab"
    LECTURE = "Lecture"
    WEB = "On-Line"


class Room(Base):
    __tablename__ = "Rooms"
    default_capacity = 0
    default_is_general_purpose = False

    number: Mapped[int] = mapped_column(String(), primary_key=True)
    building_code: Mapped[str] = mapped_column(
        String(), ForeignKey("Buildings.code"), primary_key=True
    )
    capacity: Mapped[int] = mapped_column(
        String(length=2), default=default_capacity, server_default=str(default_capacity)
    )
    classification: Mapped[Optional[enum.Enum]] = mapped_column(Enum(MeetingClassification))
    is_general_purpose: Mapped[bool] = mapped_column(
        Boolean(), default=default_is_general_purpose, server_default="false"
    )
    building: Mapped["Building"] = relationship(back_populates="rooms")
    meetings: Mapped[List["Meeting"]] = relationship(back_populates="room", overlaps="meetings")

    def __hash__(self):
        return hash((self.number, self.building_code))

    def __eq__(self, other):
        if not isinstance(other, Room):
            return False
        return (self.number, self.building_code) == (other.number, self.building_code)


class Day(enum.Enum):
    MON = "Monday"
    TUE = "Tuesday"
    WED = "Wednesday"
    THU = "Thursday"
    FRI = "Friday"
    SAT = "Saturday"
    SUN = "Sunday"

    def __gt__(self, other):
        days = [Day.MON, Day.TUE, Day.WED, Day.THU, Day.FRI, Day.SAT, Day.SUN]
        return days.index(self) > days.index(other)

    def __lt__(self, other):
        days = [Day.MON, Day.TUE, Day.WED, Day.THU, Day.FRI, Day.SAT, Day.SUN]
        return days.index(self) < days.index(other)


# time is set up as minutes since EST 00:00
#   to avoid dealing with timezones and make checks easier
class TimeBlock(Base):
    __tablename__ = "TimeBlocks"
    day: Mapped[Day] = mapped_column(Enum(Day), primary_key=True)
    number: Mapped[int] = mapped_column(Integer(), primary_key=True)
    start_minutes_from_est: Mapped[int] = mapped_column(Integer())
    end_minutes_from_est: Mapped[int] = mapped_column(Integer())

    school_allocations: Mapped[List["SchoolAllocation"]] = relationship(back_populates="time_block")

    @validates("end_minutes_from_est")
    def validate_end_time(self, _, end_minutes_from_est):
        if end_minutes_from_est is None and self.start_minutes_from_est is None:
            return end_minutes_from_est
        if not (end_minutes_from_est and self.start_minutes_from_est):
            raise ValueError("Both end minutes and startminutes must be set together")
        if end_minutes_from_est > 1440 or end_minutes_from_est < 0:
            raise ValueError("End time must be less than within 24 hour range")
        if self.start_minutes_from_est > 1440 or self.start_minutes_from_est < 0:
            raise ValueError("Start time must be less than within 24 hour range")
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

    def __hash__(self):
        return hash((self.day, self.number))

    def __eq__(self, other):
        if not isinstance(other, TimeBlock):
            return False
        return (self.number, self.day) == (other.number, self.day)


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

    def __hash__(self):
        return hash((self.code, self.name))

    def __eq__(self, other):
        if not isinstance(other, School):
            return False
        return (self.code, self.name) == (other.code, self.name)


# Registrar may try to say this is "deparment" allocationbut it is school
#    allocation
# Keep in mind there is not history of school allocations so if this changes
#    views on previous years using these values my also change
# There would have to be history both this change and of rooms to
#    correctly calculate allocation numbers
# Technically the group + school_code dictates the alloaction
class SchoolAllocation(Base):
    __tablename__ = "SchoolAllocations"
    group: Mapped[int] = mapped_column(Integer())
    allocation: Mapped[int] = mapped_column(Integer())
    school_code: Mapped[str] = mapped_column(String(), ForeignKey("Schools.code"), primary_key=True)
    time_block_number: Mapped[int] = mapped_column(String(), primary_key=True)
    time_block_day: Mapped[Day] = mapped_column(Enum(Day), primary_key=True)

    time_block: Mapped["TimeBlock"] = relationship(back_populates="school_allocations")
    school: Mapped["School"] = relationship(back_populates="allocations")

    _fk_c = ForeignKeyConstraint(
        ["time_block_number", "time_block_day"], ["TimeBlocks.number", "TimeBlocks.day"]
    )
    __table_args__ = (_fk_c,)

    def __hash__(self):
        return hash((self.school_code, self.time_block_number, self.time_block_day))

    def __eq__(self, other):
        if not isinstance(other, SchoolAllocation):
            return False
        return (self.school_code, self.time_block_number, self.time_block_day) == (
            other.school_code,
            self.time_block_number,
            self.time_block_day,
        )


class Subject(Base):
    __tablename__ = "Subjects"
    code: Mapped[str] = mapped_column(String(length=10), primary_key=True)
    school_code: Mapped[Optional[str]] = mapped_column(String(), ForeignKey("Schools.code"))
    description: Mapped[Optional[str]] = mapped_column(String())

    school: Mapped["School"] = relationship(back_populates="subjects")
    courses: Mapped[List["Course"]] = relationship(back_populates="subject")

    def __hash__(self):
        return hash(self.code)

    def __eq__(self, other):
        if not isinstance(other, Subject):
            return False
        return self.code == other.code


class Course(Base):
    __tablename__ = "Courses"
    SEARCH_INTERVAL = 10
    code: Mapped[str] = mapped_column(String(), primary_key=True)
    subject_code: Mapped[int] = mapped_column(
        String(), ForeignKey("Subjects.code"), primary_key=True
    )
    credits: Mapped[int] = mapped_column(Integer())
    name: Mapped[str] = mapped_column(String())
    description: Mapped[Optional[str]] = mapped_column(String())
    banner_id: Mapped[Optional[str]] = mapped_column(String())

    subject: Mapped["Subject"] = relationship(back_populates="courses")
    sections: Mapped[List["Section"]] = relationship(back_populates="course")

    def __hash__(self):
        return hash((self.code, self.subject_code))

    def __eq__(self, other):
        if not isinstance(other, Course):
            return False
        return (self.code, self.subject_code) == (other.code, other.subject_code)


class Season(enum.Enum):
    WINTER = "WINTER"
    SPRING = "SPRING"
    SUMMER = "SUMMER"
    FALL = "FALL"

    def __str__(self) -> str:
        return self.value.lower().capitalize()


class Term(Base):
    __tablename__ = "Terms"
    season: Mapped[Season] = mapped_column(Enum(Season), primary_key=True)
    year: Mapped[int] = mapped_column(Integer(), primary_key=True)

    sections: Mapped[List["Section"]] = relationship(back_populates="term")
    meetings: Mapped[List["Meeting"]] = relationship(back_populates="term")

    @staticmethod
    def recent_order() -> tuple:
        """used to get the most recent terms"""
        return Term.year.desc(), case(
            (Term.season == Season.SUMMER, 4),
            (Term.season == Season.SPRING, 3),
            (Term.season == Season.WINTER, 2),
            (Term.season == Season.FALL, 1),
            else_=0,
        ).desc()

    def __hash__(self):
        return hash((self.season, self.year))

    def __eq__(self, other):
        if not isinstance(other, Term):
            return False
        return (self.season, self.year) == (other.season, other.year)


class Section(Base):
    __tablename__ = "Sections"
    SEARCH_INTERVAL = 10
    number: Mapped[str] = mapped_column(String(), primary_key=True)
    course_code: Mapped[str] = mapped_column(String(), primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(), primary_key=True)
    term_season: Mapped[Season] = mapped_column(Enum(Season), primary_key=True)
    term_year: Mapped[Season] = mapped_column(Integer(), primary_key=True)
    professor_id: Mapped[Optional[Professor]] = mapped_column(
        Integer(), ForeignKey("Professors.id")
    )
    campus: Mapped[str] = mapped_column(String())
    soft_capacity: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    banner_course: Mapped[Optional[str]] = mapped_column(String())

    course: Mapped["Course"] = relationship(back_populates="sections")
    term: Mapped["Term"] = relationship(back_populates="sections")
    professor: Mapped[Optional["Professor"]] = relationship(back_populates="sections")
    meetings: Mapped[List["Meeting"]] = relationship(back_populates="section", overlaps="meetings")

    _fk_c_to_term = ForeignKeyConstraint(
        ["term_season", "term_year"],
        ["Terms.season", "Terms.year"],
    )
    _fk_c_to_course = ForeignKeyConstraint(
        ["course_code", "subject_code"],
        ["Courses.code", "Courses.subject_code"],
    )
    __table_args__ = (
        _fk_c_to_term,
        _fk_c_to_course,
    )

    def __hash__(self):
        return hash(
            (self.number, self.course_code, self.subject_code, self.term_season, self.term_year)
        )

    def __eq__(self, other):
        if not isinstance(other, Section):
            return False
        return (
            self.number,
            self.course_code,
            self.subject_code,
            self.term_season,
            self.term_year,
        ) == (
            other.number,
            other.course_code,
            other.subject_code,
            other.term_season,
            other.term_year,
        )


class Meeting(Base):
    __tablename__ = "Meetings"
    # There is no functional dependencies within meeting so must have an autoincrementing key
    id: Mapped[int] = mapped_column(Integer(), primary_key=True, autoincrement=True)
    section_number: Mapped[str] = mapped_column(String())
    course_code: Mapped[str] = mapped_column(String())
    subject_code: Mapped[str] = mapped_column(String())
    term_season: Mapped[Season] = mapped_column(Enum(Season))
    term_year: Mapped[Season] = mapped_column(Integer())
    day: Mapped[Optional[Day]] = mapped_column(Enum(Day))
    start_minutes_from_est: Mapped[Optional[int]] = mapped_column(Integer())
    end_minutes_from_est: Mapped[Optional[int]] = mapped_column(Integer)
    room_number: Mapped[Optional[str]] = mapped_column(
        String(),
    )
    # building code is a fk for builds and part of the composite key for room
    building_code: Mapped[Optional[str]] = mapped_column(String(), ForeignKey("Buildings.code"))
    professor_id: Mapped[Optional[Professor]] = mapped_column(
        Integer(), ForeignKey("Professors.id")
    )
    #####
    # these probably wont matter all that much
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime())
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime())
    style_code: Mapped[Optional[str]] = mapped_column(String(), default="Lec", server_default="Lec")

    section: Mapped["Section"] = relationship(back_populates="meetings", overlaps="meetings")
    room: Mapped["Room"] = relationship(back_populates="meetings", overlaps="meetings")
    term: Mapped["Term"] = relationship(back_populates="meetings", overlaps="meetings,section")
    building: Mapped["Building"] = relationship(back_populates="meetings", overlaps="meetings,room")
    professor: Mapped["Professor"] = relationship(back_populates="meetings")

    @validates("end_minutes_from_est")
    def validate_end_time(self, _, end_minutes_from_est):
        if end_minutes_from_est is None and self.start_minutes_from_est is None:
            return end_minutes_from_est
        if not (end_minutes_from_est and self.start_minutes_from_est):
            raise ValueError("Both end minutes and startminutes must be set together")
        if end_minutes_from_est > 1440 or end_minutes_from_est < 0:
            raise ValueError("End time must be less than within 24 hour range")
        if self.start_minutes_from_est > 1440 or self.start_minutes_from_est < 0:
            raise ValueError("Start time must be less than within 24 hour range")
        if int(end_minutes_from_est) <= int(self.start_minutes_from_est):
            raise ValueError("End time must be greater than start time")
        return end_minutes_from_est

    _fk_c_to_section = ForeignKeyConstraint(
        ["section_number", "course_code", "subject_code", "term_season", "term_year"],
        [
            "Sections.number",
            "Sections.course_code",
            "Sections.subject_code",
            "Sections.term_season",
            "Sections.term_year",
        ],
    )
    _fk_c_to_room = ForeignKeyConstraint(
        ["room_number", "building_code"],
        ["Rooms.number", "Rooms.building_code"],
    )
    _fk_c_to_term = ForeignKeyConstraint(
        ["term_season", "term_year"],
        ["Terms.season", "Terms.year"],
    )
    __table_args__ = (_fk_c_to_room, _fk_c_to_section, _fk_c_to_term)

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
            else_=8,
        ).asc(), Meeting.start_minutes_from_est.asc()

    @property
    def start_time(self) -> time | None:
        if self.start_minutes_from_est is None:
            return None
        hours, minutes = divmod(int(self.start_minutes_from_est), 60)
        return time(hours, minutes)

    @property
    def end_time(self) -> time | None:
        if self.end_minutes_from_est is None:
            return None
        hours, minutes = divmod(int(self.end_minutes_from_est), 60)
        return time(hours, minutes)

    @property
    def display_time(self) -> str:
        if self.start_time is None or self.end_time is None:
            return "No time"
        return f"{self.start_time.strftime("%I:%M %p")} - {self.end_time.strftime("%I:%M %p")}"

    def __hash__(self):
        return hash(self.rowid)

    def __eq__(self, other):
        if not isinstance(other, Meeting):
            return False
        return self.rowid == other.rowid
