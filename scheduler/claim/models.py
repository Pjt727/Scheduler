from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet
from authentication.models import Professor
from datetime import time


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

    def __str__(self) -> str:
        return f"{self.name}"
    
    def __repr__(self) -> str:
        return f"name={self.name}, code={self.code}"    


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
        return f"{self.start.strftime('%I:%M %p')} - {self.end.strftime('%I:%M %p')}"
    
    def start_input(self) -> str:
        return self.start.strftime('%H:%M')

    def end_input(self) -> str:
        return self.end.strftime('%H:%M')

class Department(models.Model):
    verbose_name = "Department"

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=5)

    chair = models.ForeignKey(Professor, related_name="departments", on_delete=models.CASCADE, blank=True, null=True, default=None)
   
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"name={self.name}, code={self.code}, chair={self.chair}"
    

class AllocationGroup(models.Model):
    verbose_name = "Slot Group"


class DepartmentAllocation(models.Model):
    verbose_name = "Department Allocation"

    number_of_classrooms = models.IntegerField()

    department = models.ForeignKey(Department, related_name="department_allocations", on_delete=models.CASCADE)
    allocation_group = models.ForeignKey(AllocationGroup, related_name="department_allocations", on_delete=models.CASCADE)


    def __repr__(self) -> str:
        return f"number of classroom={self.number_of_classrooms}, time block={self.allocation_group.time_blocks.all()}, department={self.department}"


class TimeBlock(models.Model):
    verbose_name = "Time Block"

    # These numbers occur at the same time so may need special formatting
    LONG_NIGHT_NUMBERS = [21, 22, 23, 24] # 6:30-9:15's
    SHORT_NIGHT_NUMBERS = [17, 18, 19, 20] # 6:30-7:45's & 8:00-9:15's
    day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)

    # if this is None it means that it is an abnormal time slot
    number = models.IntegerField(null=True, blank=True, default=None)

    allocation_groups = models.ManyToManyField(AllocationGroup, related_name="time_blocks", blank=True, default=None)
    start_end_time = models.ForeignKey(StartEndTime, related_name="time_blocks", on_delete=models.CASCADE)
   

    def add_allocation_groups(self):
        assert self.number is None
        tms = TimeBlock.objects.filter(number__isnull=False).filter(
            day=self.day,
            start_end_time__start__lte = self.start_end_time.end,
            start_end_time__end__gte = self.start_end_time.start
        )

        for tm in tms:
            self.allocation_groups.add(tm.allocation_groups.first())
    
    def __str__(self) -> str:
        return f"{self.number}, {self.day}"
    
    def __repr__(self) -> str:
        return f"block={self.number}, day={self.day}, time={self.start_end_time}"
    


class Subject(models.Model):
    verbose_name = "Subject"

    code = models.CharField(max_length=10)
    description = models.CharField(max_length=100, blank=True, null=True, default=None)

    department = models.ForeignKey(Department, related_name="subjects", null=True, on_delete=models.CASCADE)
   
    def __str__(self) -> str:
        return self.code
    
    def __repr__(self) -> str:
        return f"code={self.code}, department={self.department}, request={self.request}"
    

class Course(models.Model):
    verbose_name = "Course"

    banner_id = models.IntegerField(blank=True, null=True, default=None)
    code = models.CharField(max_length=5)
    credits = models.IntegerField()
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=1000, blank=True, null=True, default=None)
    prerequisite = models.CharField(max_length=100, blank=True, null=True, default=None)
    corequisite = models.CharField(max_length=100, blank=True, null=True, default=None)

    subject = models.ForeignKey(Subject, related_name="courses", null=True, on_delete=models.SET_NULL)
   
    
    def __str__(self) -> str:
        return f"{self.subject}: {self.code}"

    def __repr__(self) -> str:
        return f"code={self.code}, credits={self.credits}, title={self.title}, subject={self.subject}"    

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

    def __str__(self) -> str:
        return f"{self.season.capitalize()} {self.year}"
    
    def __repr__(self) -> str:
        return f"{self.season.capitalize()} {self.year}"


class Section(models.Model):
    verbose_name = "Section"
    
    banner_course = models.CharField(max_length=10)
    number = models.CharField(blank=True, max_length=5)
    campus = models.CharField(max_length=20)

    soft_cap = models.IntegerField(blank=True, default=0)

    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="sections", max_length=20)
    course = models.ForeignKey(Course, related_name="sections", on_delete=models.CASCADE)
    primary_professor = models.ForeignKey(Professor, related_name="sections", on_delete=models.SET_NULL, blank=True, null=True, default=None)
    

    class Meta:
        unique_together = ('course', 'term', 'number',)

    def __str__(self) -> str:
        return f"{self.course.subject} {self.course.code}-{self.number}"     

    def __repr__(self) -> str:
        return f"number={self.number}, campus={self.campus}, course={self.course}, soft cap={self.soft_cap}, request={self.request}"
        
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

    section = models.ForeignKey(Section, related_name="meetings", null=True, on_delete=models.CASCADE)
    time_block = models.ForeignKey(TimeBlock, related_name="meetings", on_delete=models.SET_NULL, blank=True, null=True, default=None)
    room = models.ForeignKey(Room, related_name="meetings", on_delete=models.SET_NULL, null=True, blank=True, default=None)
    professor = models.ForeignKey(Professor, related_name="meetings", on_delete=models.SET_NULL, blank=True, null=True, default=None)
   

    

    def __str__(self) -> str:
        return f"{self.time_block.day} {self.time_block.start_end_time}"
    
    def __repr__(self) -> str:
        return f"section={self.section}, time block={self.time_block}, room={self.room}, teacher={self.professor}"
    
    
