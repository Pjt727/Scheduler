from django.db import models, IntegrityError, transaction
from authentication.models import Professor
from django.utils.timezone import now
from claim.models import Meeting, Building, Room, Day, Course
from authentication.models import Professor

class UpdateMeetingRequest(models.Model):
    verbose_name = "Change Meeting"

    start_time = models.TimeField()
    end_time = models.TimeField()
    day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)

    # If the building is None then there is no room
    # If the room is None then the new meeting can be any room in the building 
    building = models.ForeignKey(Building, related_name="change_requests", null=True, on_delete=models.SET_NULL)
    room = models.ForeignKey(Room, related_name="change_requests", null=True, on_delete=models.SET_NULL)

    original = models.ForeignKey(Meeting, related_name="change_requests", on_delete=models.CASCADE)


class UpdateMeetingMessage(models.Model):
    verbose_name = "Change Meeting Message"
    REQUESTED = 'requested'
    ACCEPTED = 'accepted'
    REVISED_ACCEPTED = 'revised_accepted'
    DENIED = 'denied'

    choices = [
        (REQUESTED, 'Requested'),
        (ACCEPTED, 'Accepted'),
        (REVISED_ACCEPTED, 'Revised and Accepted'),
        (DENIED, 'Denied')
    ]

    status = models.CharField(max_length=20, choices=choices)

    old_start_time = models.TimeField()
    old_end_time = models.TimeField()
    old_day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)
    old_building = models.ForeignKey(Building, related_name="messages_of_new",null=True, on_delete=models.SET_NULL)
    old_room = models.ForeignKey(Room, related_name="messages_of_new", null=True, on_delete=models.SET_NULL)

    new_start_time = models.TimeField()
    new_end_time = models.TimeField()
    new_day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)
    new_building = models.ForeignKey(Building, related_name="messages_of_old", null=True, on_delete=models.SET_NULL)
    new_room = models.ForeignKey(Room, related_name="messages_of_old", null=True, on_delete=models.SET_NULL)

    course = models.ForeignKey(Building, related_name="messages", null=True, on_delete=models.SET_NULL)

    # If none the request is no longer active and has been resolved
    request = models.ForeignKey(UpdateMeetingRequest, related_name="messages", null=True, on_delete=models.SET_NULL)

    def get_old_start_time(self):
        return self.old_start_time.strftime('%I:%M %p')
    
    def get_old_end_time(self):
        return self.old_end_time.strftime('%I:%M %p')

    def get_new_start_time(self):
        return self.new_start_time.strftime('%I:%M %p')

    def get_new_end_time(self):
        return self.new_end_time.strftime('%I:%M %p')

