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
import claim.page_views as claim_page_views
import claim.api_views as claim_api_views
import heads.views as heads_views
from django.views.generic import TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='base.html'), name='index'),

    # Auth views:
    ## pages
    path('login/',auth_views.login, name='login'),
    path('register/', auth_views.register, name='register'),
    path('logout/', auth_views.logout, name='logout'),
    ## json responses
    path('get_professor/', auth_views.get_professor, name='get_professor'),

    # request views
    ## pages

    # Claim views
    ## pages
    path('claim/', claim_page_views.claim, name='claim'),
    path('my_meetings/', claim_page_views.my_meetings, name='my_meetings'),
    path('edit_section/<int:section>', claim_page_views.edit_section, name='edit_section'),
    ## json responses
    path('course_search/', claim_api_views.course_search, name='course_search'),
    path('section_search/', claim_api_views.section_search, name='section_search'),
    path('submit_claim/', claim_api_views.submit_claim, name="submit_claim"),
    path('get_meetings/', claim_api_views.get_meetings, name='get_meetings'),
    path('get_meetings_edit_section/', claim_api_views.get_meetings_edit_section, name='get_meetings_edit_section'),
    path('get_edit_section/', claim_api_views.get_edit_section, name='get_edit_section'),
    path('get_rooms_edit_section', claim_api_views.get_rooms_edit_section, name='get_room_edit_section'),
    path('get_meeting_details/', claim_api_views.get_meeting_details, name='get_meeting_details'),
    path('add_rows/', claim_api_views.add_rows, name='add_rows'),
    path('get_warnings/', claim_api_views.get_warnings, name='get_warnings'),
    path('submit_section_changes/', claim_api_views.submit_section_changes, name='submit_section_changes'),
    
    # Head views
    ## pages
    path('term_overview/', heads_views.term_overview, name="term_overview"),
    ## json responses
    path('dep_allo/', heads_views.dep_allo, name="dep_allo"),
    path('dep_allo_sections/', heads_views.dep_allo_sections, name="dep_allo_sections"),
]
