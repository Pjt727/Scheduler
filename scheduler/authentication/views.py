from django.http import HttpRequest, HttpResponse
from .models import Professor
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_user
from django.contrib.auth import logout as logout_user
from django.contrib import messages
from django.contrib.auth.models import User
from authentication.models import Professor
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError

def register(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        # Check if can make valid user
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        if not (password1 == password2):
            messages.error(request, ("Passwords do not match. Please try again."))
            return render(request, 'register.html')
        email = request.POST['email']
        try:
            validator = EmailValidator()
            validator(email)
        except ValidationError:
            messages.error(request, ("Not a valid email. Please try again."))
            return render(request, 'register.html')
        if User.objects.filter(username=email).first():
            messages.error(request, ("You are already registered. Please log in."))
            return render(request, 'login.html')
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        user = User.objects.create_user(username=email, email=email, password=password1, first_name=first_name)

        # if the prof has taught before there will already likely be an instance of them to attach
        # to their user
        # TODO: Implement a email verification step if there is an existing Professor instance
        prof = Professor.objects.filter(email=email).first()
        extra_message = ""
        if prof is None:
            email = email
            prof = Professor(first_name=first_name, last_name=last_name, email=email, user=user)
        else:
            extra_message = " Your previous teaching history is available."
            prof.user = user
        prof.save()
        
        professor = authenticate(username=email, password=password1) 
        if professor is not None and professor.is_authenticated:
            login_user(request=request, user=professor)

        messages.success(request, (f"Registration Successful.{extra_message}"))
        return redirect('index')

    
        
    return render(request, 'register.html')

def login(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        # Check if user exists
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login_user(request, user)
            messages.success(request, ("Login Successful"))   
            return redirect('index')

        messages.error(request, ("Login Failed"))

        return redirect('login')

    return render(request, 'login.html')

def logout(request: HttpRequest) -> HttpResponse:
    logout_user(request)
    return render(request, 'login.html')