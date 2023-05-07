from django.contrib.auth.models import User
from django.db import models

class Professor(User):
    verbose_name = "Professor"

    title = models.CharField(max_length=20, null=True, default="Professor")
    is_department_head =models.BooleanField(blank=True, null=True, default=False)
    credits = models.IntegerField(default=0)

    class Meta:
            app_label = 'django.contrib.auth'

    def __str__(self) -> str:
        return f"{self.title} {self.last_name}"