from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import render
import request.forms as forms
from django.db import IntegrityError, transaction
from django.forms import ModelForm
from authentication.models import Professor
from django.contrib.auth.decorators import login_required
from request.models import submit_requests, delete_requests
from claim.models import load_base_data, Building

REQUEST_FORMS = {
    forms.SubmitRequestBundle.id: forms.SubmitRequestBundle,
    forms.RequestBuilding.id: forms.RequestBuilding,
    forms.RequestRoom.id: forms.RequestRoom,
}

POST_ERR_MESSAGE = "Only post requests are allowed!"

#######
# Pages
#######
@login_required
def make_request(request: HttpRequest) -> HttpResponse:
    # Only for testing purposes to generate base_data if not already generate... eventually wont be here
    try:
        Building.objects.get(code='MUS')
    except Building.DoesNotExist:
        load_base_data()
    

    prof=Professor.objects.get(pk=request.user.id)
    context = {
        'modal_forms': (
            forms.RequestBuilding(data={}),
            forms.RequestRoom(data={}, user=request.user),
        ),
        'submit_request_form': forms.SubmitRequestBundle(user=request.user),
    }

    return render(request, 'make_request.html', context=context)


########
# Json views for requests
########    
@login_required
def request_add(request: HttpRequest, form_id:str) -> JsonResponse:
    response_data = {}

    # not post check
    if request.method != 'POST':
        response_data['ok'] = False
        response_data['error'] = POST_ERR_MESSAGE
        return JsonResponse(response_data)
    
    # getting user object
    professor = Professor.objects.get(id=request.user.id)

    # getting form
    FormModel= REQUEST_FORMS.get(form_id, None)
    if FormModel is None:
        response_data['ok'] = False
        response_data['error'] = f'Form {form_id} not found'
        return JsonResponse(response_data)
    
    # Probably bad practice
    try:
        form: ModelForm = FormModel(data=request.POST, user=professor)
    except TypeError:
        form: ModelForm = FormModel(data=request.POST)
    
    # form checking
    if not form.is_valid():
        response_data['ok'] = False
        response_data['error'] = form.errors.as_text()
        return JsonResponse(response_data)

    # saving form listing and coupled items
    with transaction.atomic():
        request_item_group = forms.RequestItemGroup(requester=professor)
        request_item_group.save()
        request_item = forms.RequestItem(group=request_item_group)
        request_item.save()
        form.instance.request = request_item
        record = form.save()    

    # success message
    response_data['message'] = f"{form.table_name} called {record} requested!"
    response_data['ok'] = True
    return JsonResponse(response_data)


@login_required
def request_submit(request: HttpRequest) -> JsonResponse:
    response_data = {}

    # not post check
    if request.method != 'POST':
        response_data['ok'] = False
        response_data['error'] = POST_ERR_MESSAGE
        return JsonResponse(response_data)
    
    # making form instance
    form: forms.SubmitRequestBundle = forms.SubmitRequestBundle(request.POST, user=request.user)

    # form checking
    if not form.is_valid():
        response_data['ok'] = False
        print(form.errors)
        response_data['error'] = form.errors.as_text()
        return JsonResponse(response_data)

    button_value = request.META.get('HTTP_BUTTON', '')

    # button checks
    ## Maybe should just separate into two different views
    if not (button_value == "submit" or button_value == "delete"):
        response_data['ok'] = False
        response_data['error'] = "Button data-value not recognized"
        return JsonResponse(response_data)
    
    ## button delete
    if button_value == "delete":
        try:
            delete_requests(form.cleaned_data['request_items'])
            response_data['ok'] = True
            response_data['message'] = "Successfully deleted all items!"
        except IntegrityError as err:
            response_data['ok'] = False
            response_data['error'] = str(err)
        
        return JsonResponse(response_data) 

    ## button submit
    try:
        submit_requests(form, form.cleaned_data['request_items'])
        response_data['message'] = f"Request message sent!"
        response_data['ok'] = True
    except IntegrityError as err:
        response_data['ok'] = False
        response_data['error'] = str(err)
        
   

    return JsonResponse(response_data)

@login_required
def get_form(request: HttpRequest, form_id:str) -> JsonResponse:
    response_data = {}

    # not post check
    if request.method != 'POST':
        response_data['error'] = POST_ERR_MESSAGE
        response_data['ok'] = False
        return JsonResponse(response_data)
    
    # getting form
    FormModel = REQUEST_FORMS.get(form_id, None)
    if FormModel is None:
        response_data = {
            'error': f'Form {form_id} not found',
            'ok': False
        }
        return JsonResponse(response_data)

    # Probably bad practice to create FormModel
    try:
        form = FormModel(data=request.POST, user=request.user)
    except TypeError:
        form = FormModel(data=request.POST)
    
    # getting how the form should be rendered
    render_html = 'form_as_p.html'
    if hasattr(form, "render_html"):
        render_html = form.render_html

    # rendering form
    rendered_template = render(request, render_html, {'form': form}).content.decode()
    response_data = {
        'form_html': rendered_template,
        'ok': True    
    }
    return JsonResponse(response_data)
