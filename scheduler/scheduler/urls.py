"""scheduler URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
import authentication.views as auth_views
import request.views as request_views
from django.views.generic import TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='base.html'), name='index'),

    # Auth views:
    path('login/',auth_views.login, name='login'),
    path('register/', auth_views.register, name='register'),
    path('logout/', auth_views.logout, name='logout'),

    # request views
    ## pages
    path('make_request/', request_views.make_request, name='make_request'),
    ## json responses
    path('get_form/<str:form_id>', request_views.get_form, name='get_form'),
    path('request_create/', request_views.request_create, name='request_create'),
    path('request_submit/', request_views.request_submit, name='request_submit'),
    path('request_add/<str:form_id>', request_views.request_add, name='request_add'),
]