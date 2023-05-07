from django.http import HttpRequest, HttpResponse
from .models import Professor
from django.shortcuts import render, redirect
from .forms import RegisterUserForm
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_user
from django.contrib.auth import logout as logout_user
from django.contrib import messages


def register(request: HttpRequest) -> HttpResponse:
    form = RegisterUserForm()
    if request.method == 'POST':
        # Check if can make valid user
        form = RegisterUserForm(request.POST)
        if form.is_valid():

            # Might need to check to see if username exists already

            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            professor = authenticate(username=username, password=password) 
            login_user(request=request, user=professor)

            messages.success(request, ("Registration Successful"))
            return redirect('index')

    
        
    return render(request, 'register.html', context={
        'form': form,
    })

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