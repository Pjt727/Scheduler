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
        if not prof.department_head:
            return redirect('index')

    return wrapper


# Fetch Api requests

# change to only department heads...
@login_required
def term_overview(request: HttpRequest) -> HttpResponse:
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
    return render(request, 'term_overview.html', context=data)