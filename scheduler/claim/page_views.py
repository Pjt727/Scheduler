from django.http import HttpRequest, HttpResponse
from django.shortcuts import render 
from django.contrib.auth.decorators import login_required
from .models import *
from request.models import *
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
        'terms': Term.objects.all(),
            
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

@login_required
def edit_section(request: HttpRequest, section: int) -> HttpResponse:
    section = Section.objects.get(pk=section)

    data = {
        "professor": Professor.objects.get(user=request.user),
        "section": section,
        "days": Day.CODE_TO_VERBOSE.items(), 
        "buildings": Building.objects.all()
    }

    return render(request, 'edit_section.html', context=data)

@login_required
def message_hub(request: HttpRequest) -> HttpResponse:
    message_bundles = EditMeetingMessageBundle.objects.filter(
        Q(sender=request.user.professor) | Q(recipient=request.user.professor)
    )

    context = {
        'message_bundles': message_bundles
    }

    return render(request, 'messages.html', context=context)
