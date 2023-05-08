from django.db import models, IntegrityError, transaction
from authentication.models import Professor
from django.utils.timezone import now

class RequestBundle(models.Model):
    verbose_name = "Request Bundle"

    title = models.CharField(max_length=50)
    reason = models.CharField(max_length=1024, blank=True, null=True, default=None)
    is_closed = models.BooleanField(blank=True, default=False)

    approver = models.ForeignKey(Professor, related_name="my_approve_request_bundles", blank=True, null=True, default=None, on_delete=models.CASCADE)
    requester = models.ForeignKey(Professor, related_name="my_request_bundles", on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.title
    
    def __repr__(self) -> str:
        return f"{self.title}: is_closed={self.is_closed}, approver={self.approver}, requester={self.requester}"


# Think of this class like a chat box of request messages that groups request items
class RequestMessageGroup(models.Model):
    verbose_name = "Request message Group"
    request_bundle = models.ForeignKey(RequestBundle, related_name="request_message_groups", on_delete=models.CASCADE)


class RequestMessage(models.Model):
    verbose_name = "Request Message"

    date = models.DateField(blank=True, default=now)
    message = models.CharField(max_length=1024, null=True, blank=True, default=None)

    group = models.ForeignKey(RequestMessageGroup, related_name="request_messages", on_delete=models.CASCADE)
    author = models.ForeignKey(Professor, related_name="author_request_messages", on_delete=models.CASCADE)

    class Meta:
        ordering= ['date']


# Think of this class like a line of all the changes for a particular request item
class RequestItemGroup(models.Model):
    verbose_name = "Request Item Group"
    request_bundle = models.ForeignKey(RequestBundle, related_name="request_item_groups", on_delete=models.CASCADE)

    def get_head(self):
        '''Returns the most recent request item which is the latest response'''
        try:
            head: RequestItem = self.request_items.first()
            return head
        except RequestItemGroup.DoesNotExist:
            return None
    
    def get_history(self):
        try:
            group_items = self.request_items.exclude(status=RequestItem.NOT_REQUESTED).exclude(id=self.get_head().id).all()
        except RequestItemGroup.DoesNotExist:
            group_items = []
        
        return group_items

    def is_closed(self):
        representative_request_item = self.get_head()
        return representative_request_item.status in (RequestItem.APPROVED, RequestItem.CANCELLED,)

class RequestItem(models.Model):
    verbose_name = "Request Item"

    NOT_REQUESTED = 'not_requested'
    REQUESTED = 'requested'
    CHANGED = 'changed'
    APPROVED = 'approved'
    DENIED = 'denied'
    CANCELLED = 'cancelled'
    DELETED = 'deleted'

    STATUSES = (
        (NOT_REQUESTED, 'Not requested'),
        (REQUESTED, 'Requested'),
        (CHANGED, 'Changed'),
        (APPROVED, 'Approved'),
        (DENIED, 'Denied'),
        (CANCELLED,'Cancelled'),
        (DELETED, 'Deleted')
    )
    status = models.CharField(max_length=20, choices=STATUSES, null=True, default=NOT_REQUESTED)
    date = models.DateField(blank=True, default=now)

    group = models.ForeignKey(RequestItemGroup, related_name="request_items", on_delete=models.CASCADE)
    request_message = models.ForeignKey(RequestMessage, related_name="request_items", null=True, blank=True, default=None, on_delete=models.CASCADE)

    def is_head(self) -> bool:
        return self is self.group.get_head()

    def previous(self):
        try:
            return RequestItem.objects.filter(group=self.group,date__lt=self.date).order_by('-date').first()
        except RequestItem.DoesNotExist:
            return None


    def get_item(self):
        '''Searches for the item that is subject of the request and returns it'''
        import claim.models as items
        REQUESTABLE_TABLES = (
            items.Building,
            items.Room,
            items.StartEndTime,
            items.TimeBlock,
            items.Department,
            items.DepartmentTimeBlockAllocation,
            items.Course,
            items.Section,
            items.Meeting,
        )

        for table in REQUESTABLE_TABLES:
            item = table.objects.filter(request=self).first()
            if item:
                return item

        raise self.DoesNotExist(f"{self} not found in any requestable tables")

    ## Need to do the updates on both check_parents and check_children in case only one of them is updated
    ## There would be a way to refactor the database so these checks are done when moving the records and update done using ON CHANGE but I think that would require a lot more tables

    def check_relations(self) -> None:
        '''Updates and validates the fk relationships and raises an exception IntegrityError if the relations are problematic'''
        if self.status == self.APPROVED:
            acceptable_parent_statuses = (self.APPROVED)
            acceptable_children_statuses = (self.NOT_REQUESTED, self.REQUESTED, self.CHANGED, self.APPROVED, self.DENIED, self.CANCELLED, self.DELETED) # any of them
            ### should never access a child error message
        elif self.status == self.REQUESTED or self.status == self.CHANGED:
            acceptable_parent_statuses = (self.CHANGED, self.REQUESTED, self.APPROVED)
            acceptable_children_statuses = (self.NOT_REQUESTED, self.REQUESTED, self.CHANGED, self.APPROVED, self.DENIED, self.CANCELLED, self.DELETED) # any of them
            ### should never access a child error message
        elif self.status == self.CANCELLED or self.status == self.DENIED:
            acceptable_parent_statuses = (self.NOT_REQUESTED, self.REQUESTED, self.CHANGED, self.APPROVED, self.DENIED, self.CANCELLED, self.DELETED) # any of them
            ### should never access a parent error message
            acceptable_children_statuses = (self.CANCELLED, self.DENIED, self.NOT_REQUESTED)
        elif self.status == self.DELETED:
            acceptable_parent_statuses = (self.NOT_REQUESTED, self.REQUESTED, self.CHANGED, self.APPROVED, self.DENIED, self.CANCELLED, self.DELETED) # any of them
            ### should never access a parent error message
            acceptable_children_statuses = (self.DELETED)
        else:
            raise TypeError(f"to_status {self.status} not recognized")
        

        instance = self.get_item() # should always be head of the group
        if self.group.get_head() != self:
            raise IntegrityError("Something went terribly wrong :(")

        for field in instance._meta.get_fields():
            if isinstance(field, models.ManyToOneRel): # instance is parent of this field
                # need to update all children that referred to the previous instance if they are a head
                previous_self = self.previous()
                if previous_self is not None:
                    previous_fk_instances: models.QuerySet = getattr(previous_self.get_item(), field.name)
                    previous_fk_instances.annotate(is_head=models.F('request')).filter(is_head=True).update(request=self)

                fk_instances_queryset: models.QuerySet = getattr(instance, field.name)
                fk_instances = fk_instances_queryset.all()
                # TODO maybe change this logic to a query instead of for loops for speed improvement
                for fk_instance in fk_instances:
                    child_request_item: RequestItem = fk_instance.request
                    if child_request_item.status not in acceptable_children_statuses:
                        # TODO would be cutesy to a have a more low-level explanation if the professor teacher cs classes
                        raise IntegrityError(f"The {self} can not be {self.status} because {child_request_item} relies on it.")

            elif isinstance(field, models.ForeignKey):  # instance is child of this field
                fk_instance = getattr(instance, field.name)
                parent_request_item: RequestItem = getattr(fk_instance, 'request', None)
                if parent_request_item is None: continue
                
                # Updating the fk instance to the most recent submission
                head = parent_request_item.group.get_head()
                if fk_instance != parent_request_item.group.get_head():
                    fk_instance = head.get_item()
                    setattr(instance, field.name, fk_instance)
                    instance.save()
                    parent_request_item: RequestItem = fk_instance.request
                
                if parent_request_item.status not in acceptable_parent_statuses:
                    # TODO would be cutesy to a have a more low-level explanation if the professor teacher cs classes
                    raise IntegrityError(f"The {self} can not be {self.status} because it relies on the {parent_request_item} on its {fk_instance.verbose_name} entry.")
        
    def __str__(self) -> str:
        return f"Request for {self.get_item()}"


# from .forms import SubmitRequestBundle
@transaction.atomic
def submit_requests(form, request_item_ids: list[int]):
    request_message_group = RequestMessageGroup(request_bundle=form.cleaned_data['request_bundle'])
    request_message_group.save()
    form.instance.group = request_message_group
    form.save()
     
    request_items_queryset = RequestItem.objects.filter(pk__in=request_item_ids)
    request_items_queryset.update(status=RequestItem.REQUESTED, date=now())
    
    for request_item in request_items_queryset.all():
        request_item.check_relations()

@transaction.atomic
def delete_requests(request_item_ids: list[int]):
    request_items_queryset = RequestItem.objects.filter(pk__in=request_item_ids)
    request_items_queryset.update(status=RequestItem.DELETED)

    for request_item in request_items_queryset.all():
        request_item.check_relations()
    RequestItemGroup.objects.filter(pk__in=request_items_queryset.values_list('group', flat=True)).delete()
                