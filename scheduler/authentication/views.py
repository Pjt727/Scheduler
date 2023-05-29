from django.http import HttpRequest, HttpResponse
from .models import Professor
from django.shortcuts import render, redirect
from .forms import RegisterUserForm
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_user
from django.contrib.auth import logout as logout_user
from django.contrib import messages
from authentication.models import Professor

def register(request: HttpRequest) -> HttpResponse:
    form = RegisterUserForm()
    if request.method == 'POST':
        # Check if can make valid user
        form = RegisterUserForm(request.POST)
        if not form.is_valid():
            messages.error(request, ("Registration Unsuccessful. Please try again."))
            return render(request, 'register.html', context={'form': form,})
        user = form.save()
        username = form.cleaned_data['username'] # email
        # if the prof has taught before there will already likely be an instance of them to attach
        # to their user
        # TODO: Implement a email verification step if there is an existing Professor instance
        prof = Professor.objects.filter(email=username).first()
        extra_message = ""
        if prof is None:
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = username
            credits = form.cleaned_data['credits']
            prof = Professor(first_name=first_name, last_name=last_name, email=email, credits=credits, user=user)
        else:
            extra_message = " Your previous teaching history is available."
            prof.user = user
        prof.save()
        
        password = form.cleaned_data['password1']
        professor = authenticate(username=username, password=password) 
        login_user(request=request, user=professor)

        messages.success(request, (f"Registration Successful.{extra_message}"))
        return redirect('index')

    
        
    return render(request, 'register.html', context={'form': form,})

def login(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
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