from django.http import HttpRequest, HttpResponse
from django.shortcuts import render 
from django.contrib.auth.decorators import login_required
from .models import *
from request.models import *

@login_required
def claim(request: HttpRequest) -> HttpResponse:
    terms = Term.objects.all()
    professor = Professor.objects.get(user=request.user)
    preferences = Preferences.get_or_create_from_professor(professor)
    courses_from_preferences = map(lambda p: p.course, preferences.claim_courses.all())
    data = {
        'departments': Department.objects.all(),
        'selected_department':preferences.claim_department,
        'subjects': Subject.objects.all(),
        'selected_subject': preferences.claim_subject,
        'courses': courses_from_preferences,
        # could change this to limit from a certain year
        'terms': terms,
        'selected_term': preferences.claim_term,
        'has_results': True,
            
        'days': Day.DAY_CHOICES,
    }
    return render(request, 'claim.html', context=data)

@login_required
def professor_meetings(request: HttpRequest, professor_pk: int) -> HttpResponse:
    # getting the sections that the professor is primary for but does not have any
    # meetings with
    professor = Professor.objects.get(pk=professor_pk)
    data = {
        # could change this to limit from a certain year
        'terms': Term.objects.all(),
        'professor': professor
    }
    return render(request, 'my_meetings.html', context=data)

