from dataclasses import dataclass
from enum import Enum
from django.db import models
from django.db.models import Q, Case, When, Sum, IntegerField, Subquery, OuterRef, F, Count, Max, Func, Value
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet
from authentication.models import Professor
from datetime import time, timedelta
from typing import TYPE_CHECKING, TypedDict
if TYPE_CHECKING:
    from request.models import EditMeetingRequest


class Day:
    MONDAY = 'MO'
    TUESDAY = 'TU'
    WEDNESDAY = 'WE'
    THURSDAY = 'TH'
    FRIDAY = 'FR'
    SATURDAY = 'SA'
    SUNDAY = 'SU'

    DAY_CHOICES = [
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
    ]

    CODE_TO_VERBOSE = {
        'MO': 'Monday',
        'TU': 'Tuesday',
        'WE': 'Wednesday',
        'TH': 'Thursday',
        'FR': 'Friday',
        'SA': 'Saturday',
        'SU': 'Sunday',
    }

    VERBOSE_TO_CODE = {
        'Monday': 'MO',
        'Tuesday': 'TU',
        'Wednesday': 'WE',
        'Thursday': 'TH',
        'Friday': 'FR',
        'Saturday': 'SA',
        'Sunday': 'SU',
    }


# Makes it so that to get items that are still in request you must explicitly ask for them
# This is done so there is never accidental additions of objects that are requested in the wrong place

class Building(models.Model):
    verbose_name = "Building"

    name = models.CharField(max_length=30)
    code = models.CharField(max_length=2)

    rooms: QuerySet['Room']

    def __str__(self) -> str:
        return f"{self.name}"
    
    def __repr__(self) -> str:
        return f"name={self.name}, code={self.code}"    
    
    def get_available_rooms(self, start_time: time | timedelta, end_time: time | timedelta, day: str, term: 'Term', include_general: bool, section: 'Section' = None) -> QuerySet['Room']:
        in_time_frame = Q(
            meetings__section__term=term,
            meetings__time_block__day=day,
            meetings__time_block__start_end_time__start__lte=end_time,
            meetings__time_block__start_end_time__end__gte=start_time,
        )
        # I am not sure why an exclude does not work
        if section is None:
            taken_rooms = self.rooms.filter(in_time_frame)
            open_rooms = self.rooms.exclude(pk__in=taken_rooms)
        else:
            taken_rooms = self.rooms.filter((~Q(meetings__section=section)) & in_time_frame)
            open_rooms = self.rooms.exclude(pk__in=taken_rooms)

        if include_general:
            return open_rooms

        return open_rooms.exclude(is_general_purpose=True)
    
    def get_available_rooms_in_number(self, number: int, term: 'Term', include_general: bool, both_open: bool = True):
        in_time_blocks = Q()
        
        for time_block in TimeBlock.objects.filter(number=number).all():
            in_time_block = Q(
                meetings__section__term=term,
                meetings__time_block__day=time_block.day,
                meetings__time_block__start_end_time__start__lte=time_block.start_end_time.end,
                meetings__time_block__start_end_time__end__gte=time_block.start_end_time.start,
            )
            if both_open:
                in_time_blocks |= in_time_block
            else:
                in_time_blocks &= in_time_block
        
        taken_rooms = self.rooms.filter(in_time_block)
        open_rooms = self.rooms.exclude(pk__in=taken_rooms)

        if not include_general:
            return open_rooms.distinct()

        return open_rooms.exclude(is_general_purpose=True).distinct()
    
    def recommend(course: 'Course', term: 'Term') -> 'Building':
        building_counts = Building.objects.annotate(
            count=Count('rooms__meetings__section',
                filter=Q(
                    rooms__meetings__section__course=course,
                    rooms__meetings__section=term)))
        return building_counts.order_by('-count')[0]



class Room(models.Model):
    verbose_name = "Room"

    LECTURE = 'LEC'
    LAB = 'LAB'
    CLASSIFICATIONS = (
        (LECTURE, 'Lecture'),
        (LAB, 'Laboratory'),
    )

    number = models.CharField(max_length=6)
    classification = models.CharField(max_length=20, choices=CLASSIFICATIONS)
    capacity = models.IntegerField(null=True, blank=True, default=False)
    is_general_purpose = models.BooleanField(null=True, blank=True, default=False)
    
    building = models.ForeignKey(Building, related_name="rooms", null=True, on_delete=models.SET_NULL)
    meetings: QuerySet['Meeting']


    class Meta:
        ordering = ['number']

    def __str__(self) -> str:
        return f"{self.building} {self.number}"

    def __repr__(self) -> str:
        return f"building={self.building}, number={self.number}, classification={self.classification}, capacity={self.capacity}"


class StartEndTime(models.Model):
    verbose_name = "Start End Time"
    start = models.TimeField()
    end = models.TimeField()

    
    
    def __str__(self) -> str:
        return f"{self.start_display()} - {self.end_display()}"
    
    def start_input(self) -> str:
        return self.start.strftime('%H:%M')

    def end_input(self) -> str:
        return self.end.strftime('%H:%M')

    def start_display(self) -> str:
        return self.start.strftime('%I:%M %p')

    def end_display(self) -> str:
        return self.end.strftime('%I:%M %p')
    
    def start_d(self) -> timedelta:
        return timedelta(hours=self.start.hour, minutes=self.start.minute)

    def end_delta(self) -> timedelta:
        return timedelta(hours=self.end.hour, minutes=self.start.minute)
    

class Department(models.Model):
    verbose_name = "Department"

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=5)

    chair = models.ForeignKey(Professor, related_name="departments", on_delete=models.CASCADE, blank=True, null=True, default=None)
   
    subject: QuerySet['Subject']
    department_allocations: QuerySet['DepartmentAllocation']

    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"name={self.name}, code={self.code}, chair={self.chair}"
    

class AllocationGroup(models.Model):
    verbose_name = "Slot Group"

    department_allocations: QuerySet['DepartmentAllocation']
    time_blocks: QuerySet['TimeBlock']

    def is_night(self) -> bool:
        return self.time_blocks.filter(
                number__in=TimeBlock.LONG_NIGHT_NUMBERS
            ).exists()



class DepartmentAllocation(models.Model):
    verbose_name = "Department Allocation"

    number_of_classrooms = models.IntegerField()

    department = models.ForeignKey(Department, related_name="department_allocations", on_delete=models.CASCADE)
    allocation_group = models.ForeignKey(AllocationGroup, related_name="department_allocations", on_delete=models.CASCADE)


    def __repr__(self) -> str:
        return f"number of classroom={self.number_of_classrooms}, time block={self.allocation_group.time_blocks.all()}, department={self.department}"

    def count_rooms(self, term: 'Term') -> int:
        return Room.objects.filter(
            meetings__section__course__subject__department=self.department,
            meetings__section__term=term,
            is_general_purpose=True,
            meetings__time_block__in=self.allocation_group.time_blocks.all()
        ).distinct().count()
    def exceeds_allocation(self, term: 'Term', amount_adding=1):
        return self.count_rooms(term) + amount_adding > self.number_of_classrooms
    
class NumberIcon(TypedDict):
    start: time
    end: time
    day: str
    numbers: str

class TimeBlock(models.Model):
    verbose_name = "Time Block"

    ONE_BLOCK = timedelta(hours=1, minutes=15)
    DOUBLE_BLOCK = timedelta(hours=2, minutes=45)
    DOUBLE_BLOCK_NIGHT = timedelta(hours=2, minutes=30)
    TRIPLE_NIGHT = timedelta(hours=3, minutes=30)
    # These numbers occur at the same time so may need special formatting
    LONG_NIGHT_NUMBERS = [21, 22, 23, 24] # 6:30-9:15's
    SHORT_NIGHT_NUMBERS = [17, 18, 19, 20] # 6:30-7:45's & 8:00-9:15's
    day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)

    # if this is None it means that it is an abnormal time slot
    number = models.IntegerField(null=True, blank=True, default=None)

    allocation_groups = models.ManyToManyField(AllocationGroup, related_name="time_blocks", blank=True, default=None)
    start_end_time = models.ForeignKey(StartEndTime, related_name="time_blocks", on_delete=models.CASCADE)

    meetings: QuerySet['Meeting']
   
    def __str__(self) -> str:
        return f"{self.number}, {self.day}"
    
    def __repr__(self) -> str:
        return f"block={self.number}, day={self.day}, time={self.start_end_time}"

    def add_allocation_groups(self):
        assert self.number is None
        tms = TimeBlock.objects.filter(number__isnull=False).filter(
            day=self.day,
            start_end_time__start__lte = self.start_end_time.end,
            start_end_time__end__gte = self.start_end_time.start
        )

        for tm in tms:
            self.allocation_groups.add(tm.allocation_groups.first())

    def get_official_time_blocks(start: time | timedelta, end: time | timedelta, day: str) -> QuerySet['TimeBlock']:
        time_blocks = TimeBlock.objects.filter(
                number__isnull=False
            ).filter(
                day=day,
                start_end_time__start__lte = end,
                start_end_time__end__gte = start
            )
        return time_blocks
    
    def get_number_icons() -> list[NumberIcon]:
        number_icons: list[NumberIcon] = []
        time_blocks = TimeBlock.objects \
            .filter(number__isnull=False) \
            .exclude(number__in = TimeBlock.LONG_NIGHT_NUMBERS) \
            .exclude(number__in = TimeBlock.SHORT_NIGHT_NUMBERS)
        for time_block in time_blocks.all():
            number_icons.append({
                'day': time_block.day,
                'start': time_block.start_end_time.start,
                'end': time_block.start_end_time.end,
                'numbers': str(time_block.number)
            })
        other_time_blocks = TimeBlock.objects \
            .filter(number__isnull=False) \
            .filter(number__in = TimeBlock.SHORT_NIGHT_NUMBERS)
        for time_block in other_time_blocks.all():
            bigger_time_block = TimeBlock.objects.get(number__in=TimeBlock.LONG_NIGHT_NUMBERS, day=time_block.day)
            number_icons.append({
                'day': time_block.day,
                'start': time_block.start_end_time.start,
                'end': time_block.start_end_time.end,
                'numbers': f"{time_block.number}/{bigger_time_block.number}"
            })

        return number_icons
                


class Subject(models.Model):
    verbose_name = "Subject"

    code = models.CharField(max_length=10)
    description = models.CharField(max_length=100, blank=True, null=True, default=None)

    department = models.ForeignKey(Department, related_name="subjects", null=True, on_delete=models.CASCADE)

    courses: QuerySet['Course']
   
    def __str__(self) -> str:
        return self.code
    
    def __repr__(self) -> str:
        return f"code={self.code}, department={self.department}, request={self.request}"
    

class Course(models.Model):
    verbose_name = "Course"
    SEARCH_INTERVAL = 10

    CREDIT_HOUR_POSSIBILITIES = {
        # More that one block is only for 1 credit classes that meet for half the semester
        1: {TimeBlock.ONE_BLOCK, TimeBlock.ONE_BLOCK * 2, TimeBlock.DOUBLE_BLOCK, TimeBlock.DOUBLE_BLOCK_NIGHT},
        # ONE_BLOCK * 2 and DOUBLE_BLOCK_NIGHT are the same
        3: {TimeBlock.ONE_BLOCK * 2, TimeBlock.DOUBLE_BLOCK, TimeBlock.DOUBLE_BLOCK_NIGHT},
        # DOUBLE_BLOCK_NIGHT + ONE_BLOCK is the same as ONE_BLOCK * 3
        4: {TimeBlock.ONE_BLOCK * 3, TimeBlock.DOUBLE_BLOCK + TimeBlock.ONE_BLOCK, TimeBlock.DOUBLE_BLOCK_NIGHT + TimeBlock.ONE_BLOCK, TimeBlock.TRIPLE_NIGHT},
    }

    banner_id = models.IntegerField(blank=True, null=True, default=None)
    code = models.CharField(max_length=5)
    credits = models.IntegerField()
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=1000, blank=True, null=True, default=None)
    prerequisite = models.CharField(max_length=100, blank=True, null=True, default=None)
    corequisite = models.CharField(max_length=100, blank=True, null=True, default=None)

    subject = models.ForeignKey(Subject, related_name="courses", null=True, on_delete=models.SET_NULL)

    sections: QuerySet['Section']
   
    
    def __str__(self) -> str:
        return f"{self.subject}: {self.code}"

    def __repr__(self) -> str:
        return f"code={self.code}, credits={self.credits}, title={self.title}, subject={self.subject}"    
    
    def get_approximate_times(self) -> set[timedelta]:
        return self.CREDIT_HOUR_POSSIBILITIES.get(self.credits, timedelta(seconds=0))
    
    # TODO make this faster and maybe implement it
    def sort_with_prof(courses: QuerySet['Course'], professor: Professor) -> QuerySet['Course']:
        professor_courses = courses \
            .filter(sections__primary_professor=professor) \
            .distinct() \
            .annotate(count=Count('sections', Q(sections__primary_professor=professor))) \
        
        other_courses = courses \
            .exclude(sections__primary_professor=professor) \
            .distinct() \
            .annotate(count=Value(0)) \

        all_courses = professor_courses | other_courses

        return all_courses.order_by('-count', 'title')

    
    def live_search_filter(search_query: str) -> Q:

        course_filter = Q()
        for item in search_query.split():
            item = item.replace('&nbsp', '')
            course_filter &= Q(code__icontains=item) | Q(title__icontains=item)
        return course_filter
    
    def search(query: str, term_pk: str, department_pk: str = "any", subject_pk: str = "any") -> tuple[QuerySet['Course'], bool]:

        courses = Course.objects.filter(sections__term=term_pk).distinct()
        courses_less_filtered = courses
        if subject_pk == "any":
            if department_pk != "any":
                subject_values = Subject.objects.filter(department=department_pk)
                courses = courses.filter(subject__in=subject_values)
        else:
            courses = courses.filter(subject=subject_pk)
        
        if query:
            query_filter = Course.live_search_filter(query)
            courses = courses.filter(query_filter)
        if len(courses) > 0:
            return courses, True
        
        if query:
            courses_less_filtered = courses_less_filtered.filter(query_filter)
        return courses_less_filtered, False

            
        



class Term(models.Model):
    verbose_name = "Term"
    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    SEASONS = (
        (WINTER, 'Winter'),
        (SPRING, 'Spring'),
        (SUMMER, 'Summer'),
        (FALL, 'Fall'),
    )

    season = models.CharField(max_length=20, choices=SEASONS)
    year = models.IntegerField()

    sections: QuerySet['Section']

    class Meta:
        ordering = ('-year',
            Case(
                When(season="fall", then=1),
                When(season="winter", then=2),
                When(season="spring", then=3),
                When(season="summer", then=4),
                default=0,
                output_field=IntegerField(),
            )
        )

    def __str__(self) -> str:
        return f"{self.season.capitalize()} {self.year}"
    
    def __repr__(self) -> str:
        return f"{self.season.capitalize()} {self.year}"
    


class Section(models.Model):
    verbose_name = "Section"
    SEARCH_INTERVAL = 10
    banner_course = models.CharField(max_length=10)
    number = models.CharField(blank=True, max_length=5)
    campus = models.CharField(max_length=20)

    soft_cap = models.IntegerField(blank=True, default=0)

    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="sections", max_length=20)
    course = models.ForeignKey(Course, related_name="sections", on_delete=models.CASCADE)
    primary_professor = models.ForeignKey(Professor, related_name="sections", on_delete=models.SET_NULL, blank=True, null=True, default=None)
    
    meetings: QuerySet['Meeting']
    edit_requests: QuerySet['EditMeetingRequest']

    class Meta:
        unique_together = ('course', 'term', 'number',)

    def __str__(self) -> str:
        return f"{self.course.subject} {self.course.code}-{self.number}"     

    def __repr__(self) -> str:
        return f"number={self.number}, campus={self.campus}, course={self.course}, soft cap={self.soft_cap}"
        
    def meetings_sorted(self): 
        return self.meetings.order_by(models.Case(
            models.When(time_block__day=Day.MONDAY, then=1),
            models.When(time_block__day=Day.TUESDAY, then=2),
            models.When(time_block__day=Day.WEDNESDAY, then=3),
            models.When(time_block__day=Day.THURSDAY, then=4),
            models.When(time_block__day=Day.FRIDAY, then=5),
            models.When(time_block__day=Day.SATURDAY, then=6),
            models.When(time_block__day=Day.SUNDAY, then=7),
        ))


         

    def sort_sections(section_qs: QuerySet, sort_column: str, sort_type: str) -> QuerySet:
        field_names = {
        'sortTitle': 'course__title',
        'sortSubject': 'course__subject__code',
        'sortCode': 'course__code',
        }

        field_name = field_names.get(sort_column)
        if field_name is not None:
            if sort_type == "descending":
                field_name = '-' + field_name

            section_qs = section_qs.order_by(field_name)

        return section_qs


class Meeting(models.Model):
    verbose_name = "Meeting"
    
    start_date = models.DateField(null=True, blank=True, default=None)
    end_date = models.DateField(null=True, blank=True, default=None)

    style_code = models.CharField(max_length=20, default="LEC", blank=True, null=True)
    style_description = models.CharField(max_length=20, default="Lecture", blank=True, null=True)

    # is whether other meetings have the same time block and room
    is_sharable = models.BooleanField(default=False, blank=True)

    section = models.ForeignKey(Section, related_name="meetings", null=True, on_delete=models.CASCADE)
    time_block = models.ForeignKey(TimeBlock, related_name="meetings", on_delete=models.SET_NULL, blank=True, null=True, default=None)
    room = models.ForeignKey(Room, related_name="meetings", on_delete=models.SET_NULL, null=True, blank=True, default=None)
    professor = models.ForeignKey(Professor, related_name="meetings", on_delete=models.SET_NULL, blank=True, null=True, default=None)
    

    def __str__(self) -> str:
        return f"{self.time_block.day} {self.time_block.start_end_time}"
    
    def __repr__(self) -> str:
        return f"section={self.section}, time block={self.time_block}, room={self.room}, teacher={self.professor}"
    
    
