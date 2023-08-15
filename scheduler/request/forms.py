from django import forms
from .models import *

class EditMeetingRequestFrom(models.ModelFrom):
    class Meta:
        model = EditMeetingRequest
        fields = (
            'start_time',
            'end_time',
            'day',
            'building',
            'room',
            'professor',
            'original',
        )


class EditSectionRequestForm(models.ModelForm):
    meetings = forms.formsets(EditMeetingRequest)
    class Meta:
        model = EditSectionRequest
        fields = (
            'section'
        )

class EditRequestBundleForm(models.ModelForm):
    sections = forms.formsets(EditSectionRequest)
    class Meta:
        model = EditRequestBundle
