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
import request.page_views as request_page_views
import request.partial_views as request_partial_views
import claim.page_views as claim_page_views
import claim.partial_views as claim_partial_views
import heads.page_views as heads_page_views
import heads.partial_views as heads_partial_views
from django.views.generic import TemplateView


# yeah you should probably put these all in module folder then import the modules here
# but i'm currently the only maintainer and i'm too lazy to change this

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='base.html'), name='index'),
    path('test/', TemplateView.as_view(template_name='test.html'), name='test'),

    # Auth views:
    ## pages
    path('login/',auth_views.login, name='login'),
    path('register/', auth_views.register, name='register'),
    path('logout/', auth_views.logout, name='logout'),
    ## partial responses
    path('get_professor/', auth_views.get_professor, name='get_professor'),

    # request views
    ## pages
    path('message_hub', request_page_views.message_hub, name="message_hub"),
    path('edit_section/<int:section_pk>', request_page_views.edit_section, name='edit_section'),
    ## partial
    path('display_row', request_partial_views.DisplayRow.as_view(), name="display_row"),
    path('input_row', request_partial_views.InputRow.as_view(), name="input_row"),
    path('add_rows', request_partial_views.add_rows, name="add_rows"),
    path('add_section', request_partial_views.add_section, name="add_section"),
    path('update_rooms', request_partial_views.update_rooms, name="update_rooms"),
    path('update_meetings', request_partial_views.update_meetings, name="update_meetings"),
    path('soft_submit', request_partial_views.soft_submit, name='soft_submit'),
    path('hard_submit', request_partial_views.hard_submit, name='hard_submit'),
    path('soft_approve', request_partial_views.soft_approve, name='soft_approve'),
    path('hard_approve', request_partial_views.hard_approve, name='hard_approve'),
    path('read_bundle', request_partial_views.read_bundle, name='read_bundle'),
    path('cancel_request', request_partial_views.cancel_request, name="cancel_request"),
    path('deny_request', request_partial_views.deny_request, name="deny_request"),
    path('update_time_intervals', request_partial_views.update_time_intervals, name="update_time_intervals"),
    path('update_durations', request_partial_views.update_duration, name="update_duration"),

    # Claim views
    ## pages
    path('claim/', claim_page_views.claim, name='claim'),
    path('professor_meetings/<int:professor_pk>', claim_page_views.professor_meetings, name='professor_meetings'),
    ## partial responses
    path('get_course_search/', claim_partial_views.get_course_search, name="get_course_search"),
    path('get_course_results/<int:offset>', claim_partial_views.get_course_results, name='get_course_results'),
    path('add_course_pill/<int:course>', claim_partial_views.add_course_pill, name='add_course_pill'),
    path('remove_course_pill/<int:course>', claim_partial_views.remove_course_pill, name='remove_course_pill'),
    path('section_search/', claim_partial_views.section_search, name='section_search'),
    path('get_meetings/<int:professor_pk>', claim_partial_views.get_meetings, name='get_meetings'),
    path('get_meeting_details/', claim_partial_views.get_meeting_details, name='get_meeting_details'),
    path('get_claim_info/<int:section_pk>', claim_partial_views.get_claim_info, name='get_claim_info'),
    path('claim_section/<int:section_pk>', claim_partial_views.claim_section, name='claim_section'),
    
    # Head views
    ## pages
    path('term_overview/', heads_page_views.term_overview, name="term_overview"),
    ## partial responses
    path('dep_allo/', heads_partial_views.dep_allo, name="dep_allo"),
    path('dep_allo_sections/', heads_partial_views.dep_allo_sections, name="dep_allo_sections"),
]
