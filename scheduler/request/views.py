from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import render
from django.db import IntegrityError, transaction
from django.forms import ModelForm
from authentication.models import Professor
from django.contrib.auth.decorators import login_required


POST_ERR_MESSAGE = "Only post requests are allowed!"