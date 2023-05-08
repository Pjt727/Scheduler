from django.http import HttpRequest, HttpResponse, JsonResponse, Http404
from django.shortcuts import render
import request.forms as forms
from django.db import IntegrityError, transaction
from django.forms import ModelForm
from authentication.models import Professor
from django.contrib.auth.decorators import login_required
from request.models import RequestMessageGroup, submit_requests, delete_requests


REQUEST_FORMS = {
    forms.EditRequestBundle.id: forms.EditRequestBundle,
    forms.SubmitRequestBundle.id: forms.SubmitRequestBundle,
    forms.CreateRequestBundle.id: forms.CreateRequestBundle,
    forms.RequestBuilding.id: forms.RequestBuilding,
    forms.RequestRoom.id: forms.RequestRoom,
}

POST_ERR_MESSAGE = "Only post requests are allowed!"

#######
# Pages
#######
@login_required
def make_request(request: HttpRequest) -> HttpResponse:

    prof=Professor.objects.get(pk=request.user.id)
    context = {
        'modal_forms': (
            forms.CreateRequestBundle(data={'requester': prof}),
            forms.RequestBuilding(data={}, user=request.user),
            forms.RequestRoom(data={}, user=request.user),
        ),
        'submit_request_form': forms.SubmitRequestBundle(data={'author': prof}, user=request.user),
    }

    return render(request, 'make_request.html', context=context)


########
# Json views for requests
########
@login_required
def request_create(request: HttpRequest) -> JsonResponse:
    response_data = {}

    # not post check
    if request.method != 'POST':
        response_data['error'] = POST_ERR_MESSAGE
        response_data['ok'] = False
        return JsonResponse(response_data)
    
    # creating form
    form = forms.CreateRequestBundle(request.POST)
    form.data = form.data.copy()
    form.data['requester'] = Professor.objects.get(pk=request.user.id)
    
    # bundle checking
    if not form.is_valid():
        response_data['error'] = form.errors.as_text()
        response_data['ok'] = False
        return JsonResponse(response_data)
    
    # making request bundle
    request_bundle_created = form.save()
    response_data['requestBundleValue'] = request_bundle_created.id
    response_data['message'] = f"{request_bundle_created} bundle created!"
    response_data['ok'] = True

    return JsonResponse(response_data)
    
@login_required
def request_add(request: HttpRequest, form_id:str) -> JsonResponse:
    response_data = {}

    # not post check
    if request.method != 'POST':
        response_data['ok'] = False
        response_data['error'] = POST_ERR_MESSAGE
        return JsonResponse(response_data)
    
    # getting form
    form_model= REQUEST_FORMS.get(form_id, None)
    if form_model is None:
        response_data['ok'] = False
        response_data['error'] = f'Form {form_id} not found'
        return JsonResponse(response_data)
    
    FormModel: ModelForm = form_model(request.POST, user=request.user)
    
    # form checking
    if not FormModel.is_valid():
        response_data['ok'] = False
        response_data['error'] = FormModel.errors.as_text()
        return JsonResponse(response_data)

    # saving form listing and coupled items
    with transaction.atomic():
        request_bundle_form = FormModel.cleaned_data['request_bundle']
        request_item_group = forms.RequestItemGroup(request_bundle=request_bundle_form)
        request_item_group.save()
        request_item = forms.RequestItem(group=request_item_group)
        request_item.save()
        FormModel.instance.request = request_item
        record = FormModel.save()    

    # success message
    response_data['requestBundleValue'] = request_item_group.request_bundle.id
    response_data['message'] = f"{FormModel.table_name} called {record} requested!"
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
    form.data = form.data.copy()
    form.data['author'] = Professor.objects.get(pk=request.user.id)

    # form checking
    if not form.is_valid():
        response_data['ok'] = False
        print(form.errors)
        response_data['error'] = form.errors.as_text()
        return JsonResponse(response_data)

    # button checks
    if not (request.POST['button'] == "delete" or request.POST['button'] == "delete"):
        response_data['ok'] = False
        response_data['error'] = "Button data-value not recognized"
        return JsonResponse(response_data)
    
    ## button delete
    if request.POST['button'] == "delete":
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
    rendered_template = render(None, render_html, {'form': form}).content.decode()
    response_data = {
        'form_html': rendered_template,
        'ok': True    
    }
    return JsonResponse(response_data)
