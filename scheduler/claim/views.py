from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Department, Course, Subject, Professor, Term, Section, Meeting, Day, TimeBlock, StartEndTime, AllocationGroup
from django.db.models import Q, Case, When, IntegerField, Count
from datetime import time
import json

POST_ERR_MESSAGE = "Only post requests are allowed!"
GET_ERR_MESSAGE = "Only get requests are allowed!"

@login_required
def claim(request: HttpRequest) -> HttpResponse:
    professor = Professor.objects.get(user=request.user)
    data = {
        'departments': Department.objects.all(),
        'subjects': Subject.objects.all(),
        'courses': Course.objects.all(),
        # could change this to limit from a certain year
        'previous_courses': Course.objects.filter(sections__meetings__professor=professor).distinct(),
        'terms': Term.objects.all().order_by('-year',
            Case(
                When(season=Term.FALL, then=1),
                When(season=Term.WINTER, then=2),
                When(season=Term.SPRING, then=3),
                When(season=Term.SUMMER, then=4),
                default=0,
                output_field=IntegerField(),
            )),
        'days': Day.DAY_CHOICES,
    }
    return render(request, 'claim.html', context=data)


def only_department_heads(view_func):
    def wrapper(request, *args, **kwargs):
        user = request.user
        prof = Professor.objects.get(user=user)
        if not prof.department_head:
            return redirect('index')

    return wrapper

# change to only department heads...
@login_required
def term_overview(request: HttpRequest) -> HttpResponse:
    data = {
            "terms": Term.objects.all(),
            "departments": Department.objects.all(),
    }
    return render(request, 'term_overview.html', context=data)

def dep_allo(request: HttpRequest) -> HttpResponse:
    department = Department.objects.first()
    term = Term.objects.first()

    sections = Section.objects.filter(term=term, course__subject__department=department)

    time_blocks = TimeBlock.objects.exclude(number=None)
    
    numbers: dict[int, dict[str, dict[str, dict]]] = {}

    # does more than two times more work than needed 
    for time_block in time_blocks.all():
        number_dict = {}
        count = sections.annotate(meeting_count=Count(
                'meetings', 
                filter=Q(meetings__time_block__allocation_group=time_block.allocation_group))
            ).exclude(meeting_count=0).count()

        number_dict["number"] = time_block.number
        number_dict["count"] = count
        department_allo: AllocationGroup = time_block.allocation_group
        number_dict["allocation_group"] = department_allo.pk
        allo = 0 if department_allo is None else department_allo.number_of_classrooms
        number_dict["max"] = allo
        start_time_blob = numbers.get(time_block.start_end_time.pk)
        if start_time_blob is None: numbers[time_block.start_end_time.pk] = {}
        numbers[time_block.start_end_time.pk][time_block.day] = number_dict

    time_blocks_dict = {}
    for code, _ in Day.DAY_CHOICES:
        time_blocks_dict[code] = {}
        for tb in time_blocks.filter(day=code).all():
            time_blocks_dict[code][tb.number] = tb

    data = {
            "department": department,
            "time_blocks": time_blocks_dict,
            "numbers": numbers,
            "start_end_times": StartEndTime.objects.exclude(time_blocks__number=None).order_by("end").all(),
            "days": Day.DAY_CHOICES,
            }
    return render(request, 'dep_allo.html', context=data)
# Fetch Api requests

@login_required
def course_search(request: HttpRequest) -> JsonResponse:
    response_data = {}
    
    # not get check
    if request.method != 'GET':
        response_data['error'] = GET_ERR_MESSAGE
        response_data['ok'] = False
        return JsonResponse(response_data)
    

    department = request.GET.get('department')
    subject = request.GET.get('subject')
    query = request.GET.get('search')
    count = int(request.GET.get('count'))

    courses_qs = Course.objects
    if department != 'any': courses_qs = courses_qs.filter(subject__department=department)
    if subject != 'any': courses_qs = courses_qs.filter(subject=subject)
    if query:
        items_q = Q()
        for item in query.split():
            item = item.replace('&nbsp;', '') # remove white space
            items_q &= Q(code__icontains=item) | Q(title__icontains=item)
        courses_qs = courses_qs.filter(items_q)

    courses = []
    bottom: bool = courses_qs.all().count() <= count
    for course in courses_qs.all().order_by('title')[:count]:
        courses.append({'pk': course.pk, 'title': course.title, 'code': course.code, 'subject': course.subject.code,})
    
    response_data['ok'] = True
    response_data['bottom'] = bottom
    response_data['courses'] = courses

    return JsonResponse(response_data)
    
@login_required
def section_search(request: HttpRequest) -> JsonResponse:
    response_data = {}

    # not get check
    if request.method != 'POST':
        response_data['error'] = POST_ERR_MESSAGE
        response_data['ok'] = False
        return JsonResponse(response_data)
    
    data: dict = json.loads(request.body)

    term = data.get('term')
    courses = data.get('courses')
    if not courses:
        response_data['ok'] = True
        response_data['section_html'] = ''
        return JsonResponse(response_data)
    
    exclusion_times = data.get('exclusion_times', [])
    does_fit = data.get('does_fit', False)
    is_available = data.get('is_available', False)

    professor = Professor.objects.get(user=request.user)
    section_qs = Section.objects.filter(term=term, course__in=courses)

    if is_available:
        section_qs = section_qs.filter(meetings__professor__isnull=True)


    if exclusion_times:
        exclusion_query = Q()
        for exclusion_time in exclusion_times:
            day = exclusion_time['day']
            start_time = time.fromisoformat(exclusion_time['start_time'])
            end_time = time.fromisoformat(exclusion_time['end_time'])

            exclusion_query |= Q(meetings__time_block__day=day,
                                meetings__time_block__start_end_time__start__lte=end_time,
                                meetings__time_block__start_end_time__end__gte=start_time)
        section_qs = section_qs.exclude(exclusion_query)

    # Exclude all meetings that overlap with professor meetings
    if does_fit:
        #TODO make it also take into consideration if the start and end date
        professor_meetings = professor.meetings.filter(section__term=term)
        exclusion_query = Q()
        for meeting in professor_meetings.all():
            exclusion_query |= Q(meetings__time_block__day=meeting.time_block.day,
                                meetings__time_block__start_end_time__start__lte=meeting.time_block.start_end_time.end,
                                meetings__time_block__start_end_time__end__gte=meeting.time_block.start_end_time.start)

        section_qs = section_qs.exclude(exclusion_query)
    
    
    sections_template = render(request, "sections.html", {"sections": section_qs.all()}).content.decode()

    response_data['ok'] = True
    response_data['section_html'] = sections_template
    return JsonResponse(response_data)

@login_required
def submit_claim(request: HttpRequest) -> JsonResponse:
    response_data = {}

    # not get check
    if request.method != 'POST':
        response_data['error'] = POST_ERR_MESSAGE
        response_data['ok'] = False
        return JsonResponse(response_data)
    
    data: dict = json.loads(request.body)
    meeting_ids: list[str] = data.get("meetings", [])
    # no selected meetings check
    if not meeting_ids:
        response_data['error'] = "There must be at least one meeting time selected."
        response_data['ok'] = False
        return JsonResponse(response_data)

    meetings: list[Meeting] = []
    # meeting does not exist check
    for id in meeting_ids:
        try:
            meeting = Meeting.objects.get(pk=id)
        except Meeting.DoesNotExist:
            response_data['error'] = "Could not find one of those meetings. (Try again)"
            response_data['ok'] = False
            return JsonResponse(response_data)
        meetings.append(meeting)
    
    # meeting is already taken check
    if any([meeting.professor != None for meeting in meetings]):
            response_data['error'] = "A professor has already claimed one of those meeting(s)."
            response_data['ok'] = False
            return JsonResponse(response_data)

    professor: Professor = Professor.objects.get(user=request.user)
    # meeting does not fit in schedule check
    for meeting in meetings:
        for prof_meeting in professor.meetings.filter(section__term=meeting.section.term, time_block__day=meeting.time_block.day):
            # TODO account for 
            meeting_start = meeting.time_block.start_end_time.start
            prof_meeting_end = prof_meeting.time_block.start_end_time.end

            meeting_end = meeting.time_block.start_end_time.end
            prof_meeting_start = prof_meeting.time_block.start_end_time.start
            if meeting_start <= prof_meeting_end and meeting_end >= prof_meeting_start:
                response_data['error'] = f"Meeting {meeting} interferes with your meeting {prof_meeting}."
                response_data['ok'] = False
                return JsonResponse(response_data)

    # change the meetings' professor
    for meeting in meetings:
        meeting.professor = professor
        meeting.save()

    response_data['success_message'] = "Successfully claimed all meetings."
    response_data['ok'] = True
    return JsonResponse(response_data)

