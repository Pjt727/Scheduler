from django.http import HttpRequest, HttpResponse
from django.shortcuts import render 
from django.contrib.auth.decorators import login_required
from .models import *
from django.db.models import Case, When, IntegerField 

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

@login_required
def my_meetings(request: HttpRequest) -> HttpResponse:
    data = {
        # could change this to limit from a certain year
        'terms': Term.objects.all().order_by('-year',
            Case(
                When(season=Term.FALL, then=1),
                When(season=Term.WINTER, then=2),
                When(season=Term.SPRING, then=3),
                When(season=Term.SUMMER, then=4),
                default=0,
                output_field=IntegerField(),
            )),
    }
    return render(request, 'my_meetings.html', context=data)

def edit_section(request: HttpRequest, section: int) -> HttpResponse:
    section = Section.objects.get(pk=section)

    data = {
        "professor": Professor.objects.get(user=request.user),
        "section": section,
        "days": Day.CODE_TO_VERBOSE.items(), 
        "buildings": Building.objects.all()
    }

    return render(request, 'edit_section.html', context=data)