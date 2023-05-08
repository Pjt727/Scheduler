from django.db import models
from authentication.models import Professor
from request.models import RequestItem



class Day:
    MONDAY = 'MO'
    TUESDAY = 'TU'
    WEDNESDAY = 'WE'
    THURSDAY = 'TH'
    FRIDAY = 'FR'
    DAY_CHOICES = [
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
    ]

    DAY_CODES = {
        'MO': 'Monday',
        'TU': 'Tuesday',
        'WE': 'Wednesday',
        'TH': 'Thursday',
        'FR': 'Friday',
    }


class Building(models.Model):
    verbose_name = "Building"

    name = models.CharField(max_length=30)
    code = models.CharField(max_length=2)

    request = models.OneToOneField(RequestItem, on_delete=models.CASCADE, related_name='building_requests', null=True, blank=True, default=None)

    def __str__(self) -> str:
        return f"{self.name}"
    
    def __repr__(self) -> str:
        return f"name={self.name}, code={self.code}"    


class Room(models.Model):
    verbose_name = "Room"

    # Classroom, Computer Lab maybe should be formatted differently
    number = models.CharField(max_length=6)
    CLASSROOM = 'classroom'
    LAB = 'lab'
    CLASSIFICATIONS = (
        (CLASSROOM, 'Classroom'),
        (LAB, 'Computer Lab'),
    )
    classification = models.CharField(max_length=20, choices=CLASSIFICATIONS)
    capacity = models.IntegerField()
    
    building = models.ForeignKey(Building, related_name="rooms", null=True, on_delete=models.SET_NULL)
    request = models.OneToOneField(RequestItem, on_delete=models.CASCADE, related_name='room_requests', null=True, blank=True, default=None)

    def __str__(self) -> str:
        return f"{self.building} {self.number}"

    def __repr__(self) -> str:
        return f"building={self.building}, number={self.number}, classification={self.classification}, capacity={self.capacity}"


class StartEndTime(models.Model):
    verbose_name = "Start End Time"

    start = models.IntegerField()
    '''In minutes since 00:00'''
    end = models.IntegerField()
    '''In minutes since 00:00'''

    request = models.OneToOneField(RequestItem, on_delete=models.CASCADE, related_name='start_end_time_requests', null=True, blank=True, default=None)

    def __str__(self) -> str:
        return f"{convert_hour(self.start)} - {convert_hour(self.end)}"


class TimeBlock(models.Model):
    verbose_name = "Time Block"

    number = models.IntegerField(default=None)
    day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)

    start_end_time = models.ForeignKey(StartEndTime, related_name="time_blocks", on_delete=models.CASCADE)
    request = models.OneToOneField(RequestItem, on_delete=models.CASCADE, related_name='time_block_requests', null=True, blank=True, default=None)

    def __str__(self) -> str:
        return f"{self.number}, {self.day}"
    
    def __repr__(self) -> str:
        return f"block={self.number}, day={self.day}, time={self.start_end_time}"
    
        

class Department(models.Model):
    verbose_name = "Department"

    name = models.CharField(max_length=50)
    
    chair = models.ForeignKey(Professor, related_name="departments", on_delete=models.CASCADE, blank=True, null=True, default=None)
    request = models.OneToOneField(RequestItem, on_delete=models.CASCADE, related_name='department_requests', null=True, blank=True, default=None)

    def __str__(self) -> str:
        return self.name

    def get_subjects(self) -> list[str]:
        subjects: set = set()
        for course in self.courses.all():
            subjects.add(course.subject)
        return subjects

    def get_table_sections(self):
        '''returns sections in department'''
        sections_html = '''<div class="container text-center">
                              <div class="row row-cols-5">'''
        for course in self.courses.all():
            for section in course.sections.all():
                ids = []
                for meeting in section.meetings.all():
                    tb = meeting.time_block
                    ids.append(f"{self.id}{tb.day}{tb.number}")
                sections_html += f'''<div class="col subject{course.subject} course{course.id} d-none"
                                        onmouseout="unhighlightCells(this, {ids})"
                                        onmouseover="highlightCells(this, {ids})">
                                        {course.subject}: {section.number}
                                    </div>'''
        sections_html += '''</div> </div>'''
        return sections_html

    def get_table_time_blocks(self):
        '''Return Department table'''

        table = '''<table class="table table-dark table-striped">
                        <tr>
                            <td>Time</td>'''
        for code in Day.DAY_CODES:
            table += f'''<td>{code}</td>'''
        table += f'''</tr>'''

        times = StartEndTime.objects.order_by('start')
        for time in times:
            table += f'''<tr>
                            <td >{convert_hour(time.start)} - {convert_hour(time.end)}</td>'''
            for code in Day.DAY_CODES:
                try: 
                    time_block = TimeBlock.objects.get(start_end_time=time, day=code)
                    table += f'''<td id={self.id}{code}{time_block.number}>{time_block.number}</td>'''
                except TimeBlock.DoesNotExist:
                    table += f'''<td>NA</td>'''

                
            table += f'''</tr>'''
        table += f'''</table>'''

        return table

    def __repr__(self) -> str:
        return f"name={self.name}, chair={self.chair}"
    
class DepartmentTimeBlockAllocation(models.Model):
    verbose_name = "Department Time Block Allocation"

    number_of_classrooms = models.IntegerField()

    time_block = models.ForeignKey(TimeBlock, related_name="department_time_block_allocations", null=True, on_delete=models.SET_NULL)
    department = models.ForeignKey(Department, related_name="department_time_block_allocations", null=True, on_delete=models.SET_NULL)
    request = models.OneToOneField(RequestItem, on_delete=models.CASCADE, related_name='department_time_block_allocation_requests', null=True, blank=True, default=None)
    
    def __repr__(self) -> str:
        return f"number of classroom={self.number_of_classrooms}, time block={self.time_block}, department={self.department}"

class Course(models.Model):
    verbose_name = "Course"

    subject = models.CharField(max_length=10)
    code = models.CharField(max_length=5)
    credits = models.IntegerField()
    title = models.CharField(max_length=50)
    soft_cap = models.IntegerField()

    department = models.ForeignKey(Department, related_name="courses", null=True, on_delete=models.SET_NULL)
    request = models.OneToOneField(RequestItem, on_delete=models.CASCADE, related_name='course_requests', null=True, blank=True, default=None)

    def __str__(self) -> str:
        return f"{self.subject}: {self.code}"

    def __repr__(self) -> str:
        return f"subject={self.subject}, code={self.code}, credits={self.credits}, title={self.title}, soft cap={self.soft_cap}, department={self.department}"    


class Section(models.Model):
    verbose_name = "Section"
    
    number = models.CharField(max_length=5, default=None)
    category = models.CharField(max_length=20, default=None)

    course = models.ForeignKey(Course, related_name="sections", null=True, on_delete=models.SET_NULL)
    request = models.OneToOneField(RequestItem, on_delete=models.CASCADE, related_name='section_requests', null=True, blank=True, default=None)

    def __str__(self) -> str:
        return f"{self.course.subject}-{self.number}"     

    def __repr__(self) -> str:
        return f"number={self.number}, category={self.category}, course={self.course}, request={self.request}"

class Meeting(models.Model):
    verbose_name = "Meeting"

    is_locked = models.BooleanField(blank=True, default=False)

    section = models.ForeignKey(Section, related_name="meetings", null=True, on_delete=models.SET_NULL)
    time_block = models.ForeignKey(TimeBlock, related_name="meetings", on_delete=models.SET_NULL, blank=True, null=True, default=None)
    room = models.ForeignKey(Room, related_name="meetings", on_delete=models.SET_NULL, null=True, blank=True, default=None)
    professor = models.ForeignKey(Professor, related_name="meetings", on_delete=models.SET_NULL, blank=True, null=True, default=None)
    request = models.OneToOneField(RequestItem, on_delete=models.SET_NULL, related_name='meeting_requests', null=True, blank=True, default=None)

    def __str__(self) -> str:
        return f"Meeting during {self.time_block}"
    
    def __repr__(self) -> str:
        return f"section={self.section}, time block={self.time_block}, room={self.room}, teacher={self.professor}"


def convert_hour(hour: int) -> list[str]:
    time = 'AM'
    hour_format = hour // 60
    if hour_format == 0:
        hour_format = 12
    elif hour_format > 12:
        hour_format -= 12
        time = 'PM'

    return f"{hour_format}:{convert_minute(hour)} {time}"

def convert_minute(hour: int) -> str:
    minute_format = str(hour % 60)

    if len(minute_format) == 1:
        minute_format = '0' + minute_format
    
    return minute_format




######### only use if `python manage.py loaddata myapp/fixtures/initial_data.json` does not work
def load_base_data() -> None:
    path_to_sampleData = "sampleData/"

    # loading test buildings
    building_f = open(f'{path_to_sampleData}/Building.csv', 'r')

    ## Expected Name,Code
    header_row = building_f.readline()

    buildings = []
    for line in building_f.readlines():
        name, code = line[:-1].split(',')
        buildings.append(Building(name=name, code=code))
    
    Building.objects.bulk_create(buildings)
    building_f.close()
    
    path_to_sampleData = "sampleData/"

     # loading test rooms
    room_f = open('sampleData/Room.csv', 'r')

    ## Expected Code,Number,Type,Capacity
    header_row = room_f.readline()

    rooms = []
    for line in room_f.readlines():
        code, number, kind, hard_cap = line[:-1].split(',')
        building = Building.objects.filter(code=code).first()
        rooms.append(Room(number=number, classification=kind,capacity=hard_cap,building=building))
    Room.objects.bulk_create(rooms)
    room_f.close()

    #Load Departments
    departments = []
    with open(f'{path_to_sampleData}/Department.csv', 'r') as file:
        # Expected name
        header_row = file.readline()

        for line in file.readlines():
            departments.append(Department(name=line[:-1]))
    
    Department.objects.bulk_create(departments)


    # loading test course
    course_f = open(f'{path_to_sampleData}/Course.csv', 'r')
    ## Expected Subj,Course,Title,Credits, Cap, Department
    header_row = course_f.readline()

    courses = []
    for line in course_f.readlines():
        subject, code, credits, title, soft_cap, department_name = line[:-1].split(',')
        department = Department.objects.filter(name=department_name).first()
        courses.append(Course(subject=subject, code=code, title=title, credits=credits, soft_cap=soft_cap, department=department))
    
    Course.objects.bulk_create(courses)
    course_f.close()

    # Loading StartEndTime
    start_end_times = []
    with open(f'{path_to_sampleData}/StartEndTime.csv', 'r') as file:
        ## Expected Start, end

        header_row = file.readline()

        for line in file.readlines():
            start, end = line[:-1].split(',')
            start_end_times.append(StartEndTime(start=start, end=end))
    
    StartEndTime.objects.bulk_create(start_end_times)


    # loading time blocks

    time_block_f = open('sampleData/TimeBlock.csv', 'r')
    
    ## Expected start, end, number, day
    header_row = time_block_f.readline()

    time_blocks = []
    for line in time_block_f.readlines():
        start, end, number, day_code = line[:-1].split(',')
        start_end_time = StartEndTime.objects.filter(start=start, end=end).first()
        time_blocks.append(TimeBlock(number=number, day=day_code, start_end_time=start_end_time))
    
    TimeBlock.objects.bulk_create(time_blocks)
    time_block_f.close()
    
   

    # Load DepartmentTimeBlockAllocations
    DepartmentTimeBlockAllocations = []

    with open(f'{path_to_sampleData}/DepartmentTimeBlockAllocation.csv', 'r') as file:
        # Expected Department, TimeBlock, Allocation
        header_row = file.readline()

        for line in file.readlines():
            department_name, TimeBlock_number, allocation = line[:-1].split(',')
            department = Department.objects.filter(name=department_name).first()
            
            for time_block in TimeBlock.objects.filter(number=TimeBlock_number):
                DepartmentTimeBlockAllocations.append(DepartmentTimeBlockAllocation(number_of_classrooms=allocation, time_block=time_block, department=department))

    DepartmentTimeBlockAllocation.objects.bulk_create(DepartmentTimeBlockAllocations)                



def load_sample_data() -> None:
    
    # loading test sections
    section_f = open('sampleData/Section.csv', 'r')

    ## Expected Subj,Course,Sec,Type
    header_row = section_f.readline()

    sections = []
    for line in section_f.readlines():
        subject, code, number, category = line[:-1].split(',')
        course = Course.objects.filter(code=code, subject=subject).first()
        if course is None: continue

        sections.append(Section(number=number, category=category, course=course))
    Section.objects.bulk_create(sections)
    section_f.close()

   
    # loading the meetings

    meeting_f = open('sampleData/Meeting.csv', 'r')

    ## Expected Subj, Course, Sec, Day, TimeSlot, cap, code, number and creating the grouping
    header_row = meeting_f.readline()
    ## since all meetings in sample data only have one section it can be done this way

    meetings = []
    for line in meeting_f.readlines():
        subj, course_num, sec, day, time_slot_number, cap, code, number = line[:-1].split(',')

        course = Course.objects.filter(subject=subj, code=course_num).first()
        try:
            section = Section.objects.filter(course=course, number=sec).first()
        except AttributeError:
            section = None
        building = Building.objects.filter(code=code).first()
        room = Room.objects.get_or_create(building=building, number=number)[0]
        time_block = TimeBlock.objects.filter(day=day,number=time_slot_number).first()
        meeting = Meeting(room=room, time_block=time_block, section=section)
        
        meetings.append(meeting)
        
    Meeting.objects.bulk_create(meetings)
    meeting_f.close()