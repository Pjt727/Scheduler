from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Department, Course
import logging


@login_required
def claim(request: HttpRequest) -> HttpResponse:
    data = {
        'departments': Department.objects.filter(request=None).all(),

        # inefficient query (could make new table if this is a problem)
        'department_subjects': [(c['department'], c['subject']) for c in Course.objects.filter(request=None).values('department', 'subject').distinct()],
        'courses': Course.objects.filter(request=None).all()
    }
    return render(request, 'claim.html', context=data)