from django import forms
from claim.models import Building, Room
from .models import RequestItem, RequestItemGroup
from authentication.models import Professor
from django.db.models import Q


class SubmitRequest(forms.Form):
    request_items = forms.MultipleChoiceField(choices=(), widget=forms.CheckboxSelectMultiple())
    
    id = "submit-request"
    render_html = "submit_request.html"

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
            
        self.request_items_not_requested: list[RequestItem] = RequestItem.objects.filter(group__requester=self.user, status=RequestItem.NOT_REQUESTED).all()
        request_item_choices = []
        for request_item in self.request_items_not_requested:
            request_item_instance = request_item.get_item()
            request_item_choices.append((request_item.id, request_item_instance,))
        self.fields['request_items'].choices = request_item_choices


class RequestBuilding(forms.ModelForm):
    id = "request-building"
    table_name = Building.verbose_name
    view = "request_add"

    class Meta:
        model = Building
        fields = (
            'name',
            'code',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
        }

    
class RequestRoom(forms.ModelForm):
    id = "request-room"
    table_name = Room.verbose_name
    view = "request_add"

    class Meta:
        model = Room
        fields = (
            'number',
            'classification',
            'capacity',
            'building',
        )
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'classification': forms.Select(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'building': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
        # TODO use generator
        self.fields['building'].queryset = Building.objects.filter(Q(request=None) | Q(request__group__requester=user))
