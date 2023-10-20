from django.http import HttpRequest, HttpResponse
from django.shortcuts import render 
from django.contrib.auth.decorators import login_required
from .models import *
from request.models import *
from django.db.models import Case, When, IntegerField, Value

@login_required
def claim(request: HttpRequest) -> HttpResponse:
    professor = Professor.objects.get(user=request.user)
    terms = Term.objects.all()
    professor: Professor = request.user.professor
    courses = Course.objects.filter(sections__term=terms.first()).distinct()
    courses = courses.order_by('title')
    # TODO implement if faster
    # courses = Course.sort_with_prof(courses, professor).all()[:Course.SEARCH_INTERVAL]

    data = {
        'departments': Department.objects.all(),
        'subjects': Subject.objects.all(),
        'courses': courses,
        # could change this to limit from a certain year
        'previous_courses': Course.objects.filter(sections__meetings__professor=professor).distinct(),
        'terms': terms,
        'has_results': True,
            
        'days': Day.DAY_CHOICES,
    }
    return render(request, 'claim.html', context=data)

@login_required
def my_meetings(request: HttpRequest) -> HttpResponse:
    data = {
        # could change this to limit from a certain year
        'terms': Term.objects.all(),
    }
    return render(request, 'my_meetings.html', context=data)

