import json
from django.conf import settings
import claim.models as MaristDB
from authentication.models import Professor as MaristDB_Professor
from datetime import datetime
import os

TERM_CODE_TO_SEASON = {
    "20": MaristDB.Term.SPRING,
    "40": MaristDB.Term.FALL,
}

DAY_KEYS_TO_DB_CODE = {
    'monday': MaristDB.Day.MONDAY,
    'tuesday': MaristDB.Day.TUESDAY,
    'wednesday': MaristDB.Day.WEDNESDAY,
    'thursday': MaristDB.Day.THURSDAY,
    'friday': MaristDB.Day.FRIDAY,
    'saturday': MaristDB.Day.SATURDAY,
    'sunday': MaristDB.Day.SUNDAY,
}


def add_course(course: dict):
    try:
        department = MaristDB.Department.objects.get(code=course.get('departmentCode'))
    except MaristDB.Department.DoesNotExist:
        department = MaristDB.Department.objects.get(code="OT")

    subject, _ = MaristDB.Subject.objects.get_or_create(
        code=course['subjectCode'],
        department=department,
        defaults= {
            'description': course.get('subjectDescription'),
        }
    )

    course, _ = MaristDB.Course.objects.get_or_create(
        code=course['courseNumber'],
        subject=subject,
        defaults={
            'banner_id': course['id'],
            'credits': course['creditHourLow'],
            'title': course['courseTitle'],
            'description': course.get('course_details'),
            'prerequisite': course.get('pre_reqs_desc'),
            'corequisite': course.get('co_reqs_desc'),
        }
    )


def add_section(section: dict):
    course_number = section['courseNumber']

    subject_code = section['subject']
    subject, _ = MaristDB.Subject.objects.get_or_create(
        code=subject_code,
        department=None, # THERE IS NO WAY TO KNOW THE DEPARTMENT HERE
        defaults= {
            'description': section.get('subjectDescription'),
        }
    )
    course, _ = MaristDB.Course.objects.get_or_create(
        code=course_number,
        subject=subject,
        defaults={
            'title': section['courseTitle'],
            'credits': section['creditHourLow'],
            'banner_id': section["courseReferenceNumber"],
        }
        )

    term_year = int(section['term'][:4])
    term_season = TERM_CODE_TO_SEASON[section['term'][-2:]]
    term, _ = MaristDB.Term.objects.get_or_create(
        year=term_year,
        season=term_season
    )

    primary_professor = None
    secondary_professor = None
    for prof in section['faculty']:
        last_name, first_name = prof['displayName'].split(', ')
        professor, _ = MaristDB_Professor.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            email=prof.get('emailAddress')
        )
        if prof['primaryIndicator']:
            primary_professor = professor
        else:
            secondary_professor = professor

    section_db, section_is_new = MaristDB.Section.objects.get_or_create(
        number=section['sequenceNumber'],
        campus=section['campusDescription'],
        term=term,
        course=course,
        defaults={
            "soft_cap": section['maximumEnrollment'],
            "banner_course": section['courseReferenceNumber'],
            "primary_professor": primary_professor,
        }
    )

    if not section_is_new: return

    next_professor = primary_professor
    for meeting in section['meetingsFaculty']:
        try:
            add_meeting(meeting['meetingTime'], section_db, next_professor)
        except KeyError as err:
            # One meetingTime didn't have a beginTime for some reason
            return
        if secondary_professor is not None:
            next_professor = secondary_professor


def add_meeting(meeting: dict, section: MaristDB.Section, professor: MaristDB_Professor):
    for day_key, db_code in DAY_KEYS_TO_DB_CODE.items():
        if not meeting.get(day_key): continue
        start_date = datetime.strptime(meeting['startDate'], "%m/%d/%Y")
        end_date = datetime.strptime(meeting['endDate'], "%m/%d/%Y")
        start_time = datetime.strptime(meeting['beginTime'], "%H%M").time()
        end_time= datetime.strptime(meeting['endTime'], "%H%M").time()

        start_end_time, _ = MaristDB.StartEndTime.objects.get_or_create(
            start=start_time,
            end=end_time
        )
        time_block, time_block_is_new = MaristDB.TimeBlock.objects.get_or_create(
            day=db_code,
            start_end_time=start_end_time,
        )

        if time_block_is_new:
            time_block.add_allocation_groups()

        try: 
            building, _ = MaristDB.Building.objects.get_or_create(
                name=meeting['buildingDescription'],
                code=meeting['building']
            )
            room, _ = MaristDB.Room.objects.get_or_create(
                building=building,
                number=meeting['room'],
                defaults={
                    "classification": meeting['meetingType'],
                }
            )
        except KeyError:
            building = None
            room = None

        meeting_db: MaristDB.Meeting = MaristDB.Meeting(
            start_date=start_date,
            end_date=end_date,
            style_code=meeting['meetingType'],
            style_description=meeting['meetingTypeDescription'],
            section=section,
            time_block=time_block,
            room=room,
            professor=professor,
        )

        meeting_db.save()


def create_terms(section_paths):
    BANNER_DUMP_PATH = os.path.join(settings.BASE_DIR, 'banner', 'data', 'classes')
    
    with open(os.path.join(BANNER_DUMP_PATH, 'courses.json'), 'r') as file:
        courses = json.load(file)
        for course in courses:
            add_course(course)

    for path in section_paths:
        with open(path, 'r') as file:
            sections = json.load(file)
            for section in sections:
                add_section(section)

    

