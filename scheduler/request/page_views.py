from django.http import HttpRequest, HttpResponse
from django.shortcuts import render 
from django.contrib.auth.decorators import login_required
from .models import *
from request.models import *
from claim.models import *

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
    professor: Professor = request.user.professor

    unread_bundles = professor.sent_bundles.filter(is_read=False) | \
        professor.receive_bundles.filter(is_read=False)
    
    read_bundles = professor.sent_bundles.filter(is_read=True) | \
        professor.receive_bundles.filter(is_read=True)
    context = {
        'professor': professor,
        'unread_bundles': unread_bundles.all(),
        'read_bundles': read_bundles.all(),
    }

    return render(request, 'messages.html', context=context)