from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from claim.models import Meeting, Preferences
    from request.models import *

class Professor(models.Model):
    verbose_name = "Professor"

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.CharField(max_length=128, blank=True, null=True, default=None)
    title = models.CharField(max_length=20,blank=True, null=True, default="Professor")
    is_department_head = models.BooleanField(blank=True, null=True, default=False)
    credits = models.IntegerField(blank=True, default=0)

    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='professor', null=True, blank=True, default=None)

    meetings: models.QuerySet['Meeting']
    sections: models.QuerySet['Section']
    edit_requests_involving: models.QuerySet['EditMeetingRequest']
    edit_request_bundles_sent: models.QuerySet['EditRequestBundle']
    requested_bundles: models.QuerySet['EditMeetingMessageBundleRequest']
    authorized_bundles: models.QuerySet['EditMeetingMessageBundleResponse']
    preferences: 'Preferences'

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    #TODO make it also take into consideration if the start and end date
    def section_in_meetings(self) -> Q:
        exclusion_filter = Q()
        for meeting in self.meetings.all():
            if meeting.time_block is None: continue
            exclusion_filter |= Q(
                meetings__time_block__day=meeting.time_block.day,
                meetings__time_block__start_end_time__start__lte=meeting.time_block.start_end_time.end,
                meetings__time_block__start_end_time__end__gte=meeting.time_block.start_end_time.start
            )
        return exclusion_filter
    
    def count_unread_messages(self) -> int:
        unread_messages = self.requested_bundles.filter(response__is_read=False)
        # TODO: if they are a department head count the requests they should be accepting

        return unread_messages.count()

    
