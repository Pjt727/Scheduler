from django import forms
from claim.models import Building, Room
from .models import RequestItem, RequestBundle, RequestMessage, RequestItemGroup
from django.db.models import Q


class EditRequestBundle(forms.Form):
    id = "edit-request-bundle"
    render_html = "request_bundle.html"
    view = "edit_request_bundle"

    request_groups = forms.MultipleChoiceField(choices=(), widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, request_bundle: RequestBundle, **kwargs):
        super().__init__(*args, **kwargs)
        request_items_groups_qs_all = RequestItemGroup.objects.filter(request_bundle=request_bundle)
        # filter out the ones whose head are not requested yet
        request_items_groups = [group for group in request_items_groups_qs_all.all() if group.get_head().status != RequestItem.NOT_REQUESTED]
        request_items_groups_choices = []

        # filling the group choices
        for request_item_group in request_items_groups:
            request_items_groups_choices.append((request_item_group.id, request_item_group,))

        self.fields['request_groups'].choices = request_items_groups_choices

class SubmitRequestBundle(forms.ModelForm):
    request_bundle = forms.ModelChoiceField(queryset=None, widget=forms.Select(attrs={'class': 'form-control', 'required': 'required'})) # should always get overwritten
    request_items = forms.MultipleChoiceField(choices=(), widget=forms.CheckboxSelectMultiple())
    
    id = "submit-request-bundle"
    render_html = "submit_request.html"
    class Meta:
        model = RequestMessage
        fields = (
            'message',
            'author',
            'group'
        )

        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control'}),
            'author': forms.HiddenInput(),
            'group': forms.HiddenInput(),
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['group'].required = False
        self.fields['author'].required = False
        self.fields['request_bundle'].queryset = RequestBundle.objects.filter(requester=self.user.id)

        self.request_items_not_requested = []
        request_bundle = self.data.get('request_bundle')
        if request_bundle != "":
            try:
                self.request_bundle_form = EditRequestBundle(request_bundle=request_bundle)
            except RequestBundle.DoesNotExist:
                self.request_bundle_form = None
            self.request_items_not_requested = RequestItem.objects.filter(group__request_bundle=request_bundle, status=RequestItem.NOT_REQUESTED).all()
            request_item_choices = []
            for request_item in self.request_items_not_requested:
                request_item_instance = request_item.get_item()
                request_item_choices.append((request_item.id, request_item_instance,))
            self.fields['request_items'].choices = request_item_choices

class CreateRequestBundle(forms.ModelForm):
    id = "request-bundle"
    table_name = "Request Bundle"
    view = "request_create"
    create = True
    
    class Meta:
        model=RequestBundle
        fields = (
            'title',
            'reason',
            'approver',
            'requester',
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control'}),
            'approver': forms.Select(attrs={'class': 'form-control'}),
            'requester': forms.HiddenInput(),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['requester'].required = False

class RequestBuilding(forms.ModelForm):
    request_bundle = forms.ModelChoiceField(queryset=None, widget=forms.Select(attrs={'class': 'form-control'})) # queryset should always get overwritten
    id = "request-building"
    table_name = Building.verbose_name
    view = "request_add"

    class Meta:
        model = Building
        fields = (
            'name',
            'code',
            'request',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'request': forms.HiddenInput(),
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['request_bundle'].queryset = RequestBundle.objects.filter(requester=self.user.id)

class RequestRoom(forms.ModelForm):
    request_bundle = forms.ModelChoiceField(queryset=RequestBundle.objects.all(), widget=forms.Select(attrs={'class': 'form-control', 'required': 'required'}))
    
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
            'request',
        )
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'classification': forms.Select(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'building': forms.Select(attrs={'class': 'form-control'}),
            'request': forms.HiddenInput(),
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['request_bundle'].queryset = RequestBundle.objects.filter(requester=self.user)
        request_bundle = self.data.get('request_bundle')
        if request_bundle == "":
            # TODO use generator 
            self.fields['building'].queryset = Building.objects.filter(Q(request=None))
        else:
            self.fields['building'].queryset = Building.objects.filter(Q(request=None) | Q(request__group__request_bundle=request_bundle))
