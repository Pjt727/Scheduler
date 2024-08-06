from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from claim.models import *
from django.db.models import Q, Case, When, IntegerField, Count, F, Sum, QuerySet, Max, Min, Subquery, Value, Func, DurationField, TimeField
from datetime import timedelta


def only_department_heads(view_func):
    def wrapper(request, *args, **kwargs):
        user = request.user
        prof = Professor.objects.get(user=user)
        # change condition
        if not prof:
            return redirect('index')
        raise NotImplemented("check for department head somehow")

    return wrapper

# Fetch Api requests

# change to only department heads...
@login_required
def term_overview(request: HttpRequest) -> HttpResponse:
    return render(request, 'term_overview.html')


@login_required
def grid_overview(request: HttpRequest) -> HttpResponse:
    data = {
            "terms": Term.objects.all().order_by('-year',
            Case(
                When(season=Term.FALL, then=1),
                When(season=Term.WINTER, then=2),
                When(season=Term.SPRING, then=3),
                When(season=Term.SUMMER, then=4),
                default=0,
                output_field=IntegerField(),
            )),
            "departments": Department.objects.all(),
    }
    return render(request, 'grid_overview.html', context=data)


@login_required
def manage_sections(request: HttpRequest) -> HttpResponse:
    professor = Professor.objects.get(user=request.user)
    preferences = Preferences.get_or_create_from_professor(professor)
    courses_from_preferences = map(lambda p: p.course, preferences.claim_courses.all())

    context = {
            "terms": Term.objects.all(),
            "departments": Department.objects.all(),
            "subjects": Subject.objects.all(),
            "courses_from_preferences": courses_from_preferences,
            }
    return render(request, 'manage_sections.html', context=context)

@login_required
def generate_reports(request: HttpRequest) -> HttpResponse:
    return render(request, 'generate_reports.html')
