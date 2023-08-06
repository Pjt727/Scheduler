from django.contrib.auth.models import User
from django.db import models
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from claim.models import Meeting

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
    def __str__(self) -> str:
        return f"{self.title} {self.last_name}"
    