from dataclasses import dataclass
from enum import Enum
from django.db import models
from django.db.models import Q, Case, When, Sum, IntegerField, Subquery, OuterRef, F, Count, Max, Func
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet
from authentication.models import Professor
from datetime import time, timedelta
from typing import TYPE_CHECKING
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
        if section is None:
            open_rooms: QuerySet[Room] = self.rooms.exclude(in_time_frame)
        else:
            open_rooms: QuerySet[Room] = self.rooms.exclude(
                ~Q(meetings__section=section) & in_time_frame
            )


        if include_general:
            return open_rooms

        return open_rooms.exclude(is_general_purpose=True)
    
    def get_available_rooms_in_number(self, number: int, term: 'Term', include_general: bool, both_open: bool = True):
        is_open_room = Q()
        
        for time_block in TimeBlock.objects.filter(number=number).all():
            in_time_block = Q(
                meetings__section__term=term,
                meetings__time_block__day=time_block.day,
                meetings__time_block__start_end_time__start__lte=time_block.start_end_time.end,
                meetings__time_block__start_end_time__end__gte=time_block.start_end_time.start,
            )
            if both_open:
                is_open_room |= in_time_block
            else:
                is_open_room &= in_time_block
        
        open_rooms = self.rooms.exclude(is_open_room)

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
        return self.start.strftime('%H:%M %p')

    def end_display(self) -> str:
        return self.end.strftime('%I:%M %p')
    
    def start_delta(self) -> timedelta:
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
    

@dataclass
class EditMeeting:
    start_time: time
    end_time: time
    day: str
    building: Building
    room: Room | None
    meeting: 'Meeting'
    counter: int | None
    professor: Professor = None
    is_deleted: bool = False

    def create(edit_meeting: dict, is_deleted: bool = False, primary_professor: Professor = None) -> 'EditMeeting':
        start_time = edit_meeting['startTime']
        end_time = edit_meeting['endTime']
        
        start_time = time.fromisoformat(start_time)
        end_time = time.fromisoformat(end_time)

        day = edit_meeting['day']

        building = edit_meeting.get('building')
        if isinstance(building, str):
            building = Building.objects.get(pk=building)
        
        room = edit_meeting.get('room')
        if (room == 'any') or (room == '') or (room is None):
            room = None
        else:
            room = Room.objects.get(pk=room)

        meeting = edit_meeting.get('meeting')
        if (meeting == '') or (meeting is None):
            meeting = None
            professor = primary_professor
        else:
            meeting = Meeting.objects.get(pk=meeting)
            professor = meeting.professor


        counter = edit_meeting['counter']
        
        return EditMeeting(
            start_time=start_time,
            end_time=end_time,
            day=day,
            building=building,
            room=room,
            meeting=meeting,
            counter=counter,
            professor=professor,
            is_deleted=is_deleted
        )
    
    def get_warnings(section_edit_meetings: list[tuple['Section', list['EditMeeting']]]) -> list[tuple[str, str]]:
        DANGER = 'danger'
        flattened: list[tuple[Section, EditMeeting]] = []
        for section, edit_meetings in section_edit_meetings:
            for edit_meeting in edit_meetings:
                flattened.append((section, edit_meeting))

        problems: list[tuple[str, str]] = []
        for i, section_meeting1 in enumerate(flattened[:-1]):
            section1, edit_meeting1 = section_meeting1
            for section2, edit_meeting2 in flattened[i+1:]:
                overlapping_time = (edit_meeting1.start_time_d() <= edit_meeting2.end_time_d()) \
                    and (edit_meeting1.end_time_d() >= edit_meeting2.start_time_d()) 
                same_day = (edit_meeting1.day == edit_meeting2.day)
                if not (overlapping_time and same_day): continue
                same_room = (edit_meeting1.room == edit_meeting2.room) \
                    and (edit_meeting1.room is not None)
                if same_room:
                    message = f"Meeting {edit_meeting1.counter} from {section1} overlaps {edit_meeting1.room} with meeting {edit_meeting2.counter} from {section2}."
                    problems.append((DANGER, message))
                    continue
                same_professor = (edit_meeting1.professor == edit_meeting2.room) \
                    and (edit_meeting1.room is not None)
                if same_professor:
                    message = f"Meeting {edit_meeting1.counter} from {section1} overlaps professor with meeting {edit_meeting2.counter} from {section2}."
                    problems.append((DANGER, message))
        return problems
    def is_changed(self) -> bool:
        if self.meeting is None:
            return True
        og_time_block = self.meeting.time_block
        if og_time_block.day != self.day:
            return True
        if og_time_block.start_end_time.start != self.start_time:
            return True
        if og_time_block.start_end_time.end != self.end_time:
            return True
        if self.meeting.room != self.room:
            return True

        return False

    def start_time_d(self):
        return timedelta(hours=self.start_time.hour, minutes=self.start_time.minute)

    def end_time_d(self):
        return timedelta(hours=self.end_time.hour, minutes=self.end_time.minute)


class Section(models.Model):
    verbose_name = "Section"
    
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

    def get_warnings(self, edit_meetings: list[EditMeeting], section_pks: list[str], professor: Professor = None) -> list[tuple[str, str]]:
        DANGER = 'danger'
        WARNING = 'warning'
        problems: list[tuple[str, str]]= []

        
        # room empty check
        meetings = Meeting.objects.filter(section__term=self.term).exclude(section__pk__in=section_pks)

        # TODO change this once sharable meetings gets changed
        for edit_meeting in edit_meetings:
            if edit_meeting.room is None: continue
            overlaps_time_room = Q(
                time_block__start_end_time__start__lte = edit_meeting.end_time,
                time_block__start_end_time__end__gte = edit_meeting.start_time,
                time_block__day = edit_meeting.day,
                room=edit_meeting.room
            )

            overlapping_sections: set[str] = set(map(lambda m: str(m.section), meetings.filter(overlaps_time_room).all()))
            if overlapping_sections:
                sections = ", ".join(overlapping_sections)
                problems.append((DANGER, f"Meeting {edit_meeting.counter} overlaps {edit_meeting.room} with {sections}."))

        professor = self.primary_professor if professor is None else professor
        if professor is not None:
            for edit_meeting in edit_meetings:
                overlaps_time_room = Q(
                    time_block__start_end_time__start__lte = edit_meeting.end_time,
                    time_block__start_end_time__end__gte = edit_meeting.start_time,
                    time_block__day = edit_meeting.day,
                    professor=professor
                )
                
                overlapping_sections: set[str] = set(map(lambda m: str(m.section), meetings.filter(overlaps_time_room).all()))

                if overlapping_sections:
                    sections = ", ".join(overlapping_sections)
                    problems.append((DANGER, f"Meeting {edit_meeting.counter} overlaps professor with {sections}."))

        # regular time check
        total_time = sum(map(lambda t: t.end_time_d() - t.start_time_d(), edit_meetings), start=timedelta())

        if total_time not in self.course.get_approximate_times():
            problems.append((WARNING, f'The total time for this section does not match {self.course.credits} credit hours.'))

        for edit_meeting in edit_meetings:
            if edit_meeting.room is None: continue
            if not edit_meeting.room.is_general_purpose: continue
            time_blocks = TimeBlock.get_official_time_blocks(edit_meeting.start_time, edit_meeting.end_time, day=edit_meeting.day)
            department_allocations = DepartmentAllocation.objects.filter(
                department = self.course.subject.department,
                allocation_group__in = time_blocks.values('allocation_groups')
            )
            # when doing multiple sections in the request that add to the same allocation group
            #   This will not work properly
            if any(map(lambda d_a: d_a.exceeds_allocation(self.term), department_allocations.all())):
                problems.append((WARNING, f"Meeting {edit_meeting.counter} exceeds department constraints for that time slot."))
        
        # TODO implement a warning for giving a professor too many teaching hours

        return problems

    def no_recommendation(counter: str = 1, building: Building = None, professor=None) -> EditMeeting:
        t_s = time(hour=0, minute=0)
        t_e = time(hour=1, minute=15)

        return EditMeeting(start_time=t_s, end_time=t_e, day=Day.MONDAY, building=building, room=None, meeting=None, counter=counter, professor=professor)

    # recommendations currently to not take into account meetings in the group
    # TODO add professors to reccomendaitons
    def get_recommendations(self, partial_meetings: list[EditMeeting] | None = None) -> None:
        if partial_meetings is None: partial_meetings = []

        existing_time = sum(map(lambda t: t.end_time_d() - t.start_time_d(),
            filter(lambda m: not m.is_deleted, partial_meetings)), start=timedelta())

        possible_times_to_achieve = list(map(lambda approx: approx - existing_time, self.course.get_approximate_times()))

        if len(partial_meetings) == 0:
            desired_building = Building.recommend(self.course, self.term)
        elif partial_meetings[0].building is not None:
            desired_building = partial_meetings[0].building
        else:
            desired_building = Building.recommend(self.course, self.term) 

        count = '1' if len(partial_meetings) == 0 else str(int(partial_meetings[-1].counter) + 1)
        if any(map(lambda time: time == timedelta(days=0), possible_times_to_achieve)):
            print('early exit 1')
            partial_meetings.append(Section.no_recommendation(counter=count, building=desired_building, professor=self.primary_professor))
            return
        
        if any(map(lambda approx: approx == TimeBlock.ONE_BLOCK * 3, possible_times_to_achieve)):
            print("recommending 3")
            partial_meetings.extend(self.recommend_2_time_blocks(desired_building, partial_meetings))
            edit_meeting = self.recommend_1_time_block(desired_building, partial_meetings)
            if edit_meeting is not None:
                partial_meetings.append(edit_meeting)
        elif any(map(lambda approx: approx == TimeBlock.ONE_BLOCK * 2, possible_times_to_achieve)):
            print("recommending 2")
            partial_meetings.extend(self.recommend_2_time_blocks(desired_building, partial_meetings))
        elif any(map(lambda approx: approx == TimeBlock.ONE_BLOCK, possible_times_to_achieve)):
            print("recommending 1")
            edit_meeting = self.recommend_1_time_block(desired_building, partial_meetings)
            if edit_meeting is not None:
                partial_meetings.append(edit_meeting)
        else:
            print('early exit 2')
            partial_meetings.append(Section.no_recommendation(counter=count, building=desired_building, professor=self.primary_professor))
            
    def recommend_2_time_blocks(self, building: Building = None, partial_meetings: list[EditMeeting] = None) -> list[EditMeeting]:
        professor = self.primary_professor # TODO change when shareable sections change
        if building is None:
            building = Building.recommend(self.course, self.term)
        if partial_meetings is None:
            partial_meetings = []
        if not partial_meetings:
            last_counter = "0"
        else:
            last_counter = partial_meetings[-1].counter
        allocations_counted: list[tuple[DepartmentAllocation, int]] = []
        department_allocations = DepartmentAllocation.objects.filter(
            department=self.course.subject.department
        )
        for dep_allo in department_allocations.all():
            allocations_counted.append( (dep_allo, dep_allo.count_rooms(self.term)) )
        
        allocations_counted.sort(key=lambda a_c: a_c[1])

        meetings_to_add: list[EditMeeting] = []
        for a_c in allocations_counted:
            department_allocation  = a_c[0]
            count = a_c[1]
            allocation_group = department_allocation.allocation_group
            # allocation_groups that have are at night have different numbers
            #   Therefore will need to be implemented differently
            if allocation_group.is_night(): continue

            number = allocation_group.time_blocks.first().number

            include_general = department_allocation.number_of_classrooms < count
            available_rooms = building.get_available_rooms_in_number(number, self.term, include_general, True)

            if available_rooms.exists(): continue
            for time_block in allocation_group.time_blocks.filter(number__isnull=False).all():
                start_time = time_block.start_end_time.start
                end_time = time_block.start_end_time.end
                day = time_block.day
                last_counter = str(int(last_counter) + 1)
                meetings_to_add.append(EditMeeting(
                    start_time=start_time,
                    end_time=end_time,
                    day=day,
                    building=building,
                    room=None, # Question on whether or not it should recommend a room in this case
                    meeting=None,
                    counter=last_counter,
                    professor=professor
                ))
            return meetings_to_add
        meetings_to_add.append(Section.no_recommendation(counter=last_counter, building=building, professor=professor))
        return meetings_to_add

    def recommend_1_time_block(self, building: Building, partial_meetings: list[EditMeeting] | None) -> list[EditMeeting]:
        professor = self.primary_professor # TODO change this for shared sections
        def get_all_time_blocks() -> QuerySet[TimeBlock]:
            in_problematic_meetings = Q()
            for m in partial_meetings:
                if m.is_deleted: continue
                in_problematic_meetings |= Q(
                    start_end_time__start__lte=m.end_time,
                    start_end_time__end__gte=m.start_time,
                    day=m.day
                )
            if professor is not None:
                for m in professor.meetings.filter(section__term=self.term).exclude(section__pk=self.pk).all():
                    tm = m.time_block
                    in_problematic_meetings |= Q(
                    start_end_time__start__lte=tm.start_end_time.end,
                    start_end_time__end__gte=tm.start_end_time.start,
                    day=tm.day
                )

            time_blocks = TimeBlock.objects \
                .filter(number__isnull=False) \
                .exclude(number__in=TimeBlock.LONG_NIGHT_NUMBERS) \
                .exclude(in_problematic_meetings)
            
            return time_blocks
        time_blocks_info: list[tuple[TimeBlock, int, Room]] = []
        if partial_meetings is None:
            last_counter = 0
            partial_meetings = []
        else:
            last_counter = partial_meetings[-1].counter
        if any([partial_meetings is None, all(map(lambda m: m.is_deleted, partial_meetings))]):
            time_blocks = get_all_time_blocks()
            for time_block in time_blocks.all():
                department_allocation = DepartmentAllocation.objects.get(
                    department = self.course.subject.department,
                    allocation_group=time_block.allocation_groups.first()
                )

                count = department_allocation.count_rooms(self.term)
                time_blocks_info.append(
                    (time_block, count, None)
                )
        else:
            all_time_blocks = get_all_time_blocks()
            time_blocks = time_blocks = TimeBlock.objects.none()
            for edit_meeting in filter(lambda m: not m.is_deleted,partial_meetings):
                start = edit_meeting.start_time
                end = edit_meeting.end_time
                day = edit_meeting.day
                t_bs = TimeBlock.objects.filter(
                    number__isnull=False,
                    start_end_time__start__lte = end,
                    start_end_time__end__gte = start,
                    day=day
                )
                # sort of cheaty way to do this since this only works bc time blocks with the same number
                #   are never on the same day
                for t_b in t_bs.all():
                    time_blocks |= TimeBlock.objects \
                        .filter(number=t_b.number) \
                        .exclude(day=t_b.day)
            time_blocks = time_blocks.filter(pk__in=all_time_blocks.values('pk'))
            if not time_blocks.exists():
                time_blocks = all_time_blocks 
            for time_block in time_blocks.all():
                department_allocation = DepartmentAllocation.objects.get(
                    department = self.course.subject.department,
                    allocation_group=time_block.allocation_groups.first()
                )
                count = department_allocation.count_rooms(self.term)
                time_blocks_info.append(
                    (time_block, count, edit_meeting.room)
                )
                
        time_blocks_info.sort(key=lambda t_b: t_b[1])
        for time_block, count, room in time_blocks_info:
            department_allocation = DepartmentAllocation.objects.get(
                department = self.course.subject.department,
                allocation_group=time_block.allocation_groups.first()
            )
            start_time = time_block.start_end_time.start
            end_time = time_block.start_end_time.end
            day = time_block.day

            # include_general = count < department_allocation.number_of_classrooms
            open_rooms = building.get_available_rooms(start_time, end_time, day, self.term, True, section=self)
            
            if not open_rooms.exists(): continue

            try:
                if room is not None:
                    desired_room = open_rooms.get(id=room.pk)
                else:
                    desired_room = None # question on whether we should select the room
            except Room.DoesNotExist:
                continue

            return EditMeeting(
                start_time=start_time,
                end_time=end_time,
                day=day,
                building=building,
                room=desired_room,
                meeting=None,
                counter=str(int(last_counter) + 1),
                professor=professor
            )

        return Section.no_recommendation(counter=str(int(last_counter) + 1), building=building, professor=professor)
         

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
    
    
