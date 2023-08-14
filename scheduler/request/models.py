from django.db import models, IntegrityError, transaction
from authentication.models import Professor
from claim.models import *
from authentication.models import Professor

class EditRequestBundle(models.Model):
    verbose_name = "Edit Meeting Bundle"

    requester = models.ForeignKey(Professor, related_name="edit_request_bundles", on_delete=models.CASCADE)

class EditSectionRequest(models.Model):
    verbose_name = "Edit Section"

    is_primary = models.BooleanField()

    section = models.ForeignKey(Section, related_name="edit_sections", on_delete=models.CASCADE)
    bundle = models.ForeignKey(EditRequestBundle, related_name="edit_sections", on_delete=models.CASCADE)


class EditMeetingRequest(models.Model):
    verbose_name = "Edit Meeting"

    start_time = models.TimeField()
    end_time = models.TimeField()
    day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)

    building = models.ForeignKey(Building, related_name="edit_requests", blank=True, null=True, on_delete=models.SET_NULL)
    # If the room is None then the new meeting can be any room in the building 
    room = models.ForeignKey(Room, related_name="edit_requests", blank=True, null=True, on_delete=models.SET_NULL)
    professor = models.ForeignKey(Professor, related_name="edit_requests_involving", blank=True, null=True, default=None, on_delete=models.CASCADE)
    # If there is no original then it is a created meeting
    original = models.ForeignKey(Meeting, related_name="edit_meetings", blank=True, null=True, default=None, on_delete=models.CASCADE)

    edit_section = models.ForeignKey(EditSectionRequest, related_name="edit_meetings", on_delete=models.CASCADE)


    messages: QuerySet['EditMeetingMessage']

    def is_changed(self) -> bool:
        if self.original is None: return True
        old_new = [
            (self.original.time_block.start_end_time.start, self.start_time,),
            (self.original.time_block.start_end_time.end, self.end_time,),
            (self.original.time_block.day, self.day,),
            (self.original.room, self.room,),
            (self.original.professor, self.professor,),
        ]

        return any(map(lambda old_new: old_new[0] != old_new[1], old_new))

    def freeze(self, bundle: 'EditMeetingMessageBundle') -> 'EditMeetingMessage':
        '''Freezes the current state of the request into a message'''
        if self.original is not None:
            old_start_time = self.original.time_block.start_end_time.start
            old_end_time = self.original.time_block.start_end_time.end
            old_day = self.original.time_block.day
            old_room = self.original.room
            old_professor = self.original.professor
            if old_room is not None:
                old_building = old_room.building
            else:
                old_building = None
        else:
            old_professor = None
            old_start_time = None
            old_end_time = None
            old_day = None
            old_room = None
            old_building = None



        message = EditMeetingMessage(
            is_changed=self.is_changed(),

            old_start_time=old_start_time,
            old_end_time=old_end_time,
            old_day=old_day,
            old_building=old_building,
            old_room=old_room,
            old_professor=old_professor,

            new_start_time=self.start_time,
            new_end_time=self.end_time,
            new_day=self.day,
            new_building=self.building,
            new_room=self.room,
            new_professor=self.professor,

            section=self.edit_section.section,
            request=self,
            bundle=bundle,
        )
        message.save()
        return message


class EditMeetingMessageBundle(models.Model):
    verbose_name = "Update meeting message bundle"

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
    date_sent = models.DateTimeField(auto_now_add=True, blank=True)
    is_read = models.BooleanField(default=False, blank=True)
    

    status = models.CharField(max_length=20, choices=choices)
    sender = models.ForeignKey(Professor, related_name="sent_bundles", on_delete=models.CASCADE)
        
    recipient = models.ForeignKey(Professor, related_name="receive_bundles", blank=True, null=True, default=None, on_delete=models.SET_NULL)

    messages: QuerySet['EditMeetingMessage']

    class Meta:
        ordering = ["date_sent"]
    

class EditMeetingMessage(models.Model):
    verbose_name = "Change Meeting Message"

    is_changed = models.BooleanField()

    old_start_time = models.TimeField(blank=True, null=True)
    old_end_time = models.TimeField(blank=True, null=True)
    old_day = models.CharField(max_length=2, choices=Day.DAY_CHOICES, blank=True, null=True)
    old_building = models.ForeignKey(Building, related_name="messages_of_old", blank=True, null=True, on_delete=models.SET_NULL)
    old_room = models.ForeignKey(Room, related_name="messages_of_old", blank=True, null=True, on_delete=models.SET_NULL)
    old_professor = models.ForeignKey(Professor, related_name="messages_of_old", blank=True, null=True, on_delete=models.SET_NULL)

    new_start_time = models.TimeField()
    new_end_time = models.TimeField()
    new_day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)
    new_building = models.ForeignKey(Building, related_name="messages_of_new", null=True, on_delete=models.SET_NULL)
    new_room = models.ForeignKey(Room, related_name="messages_of_new", null=True, on_delete=models.SET_NULL)
    new_professor = models.ForeignKey(Professor, related_name="messages_of_new", blank=True, null=True, on_delete=models.SET_NULL)

    section = models.ForeignKey(Section, related_name="messages", null=True, on_delete=models.SET_NULL)

    # If none the request is no longer active and has been resolved
    # may not be in sync with the message information instead points to the most recent edit of it
    request = models.ForeignKey(EditMeetingRequest, related_name="messages", null=True, on_delete=models.SET_NULL)
    bundle = models.ForeignKey(EditMeetingMessageBundle, related_name="messages", null=True, on_delete=models.CASCADE)

    def get_old_start_time(self):
        return self.old_start_time.strftime('%I:%M %p')
    
    def get_old_end_time(self):
        return self.old_end_time.strftime('%I:%M %p')

    def get_new_start_time(self):
        return self.new_start_time.strftime('%I:%M %p')

    def get_new_end_time(self):
        return self.new_end_time.strftime('%I:%M %p')

