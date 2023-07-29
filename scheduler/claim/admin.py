from django.contrib import admin
from .models import *

admin.site.register(Building)
admin.site.register(StartEndTime)
admin.site.register(TimeBlock)
admin.site.register(Department)
admin.site.register(AllocationGroup)
admin.site.register(DepartmentAllocation)
admin.site.register(Subject)
admin.site.register(Course)
admin.site.register(Section)
admin.site.register(Meeting)
admin.site.register(Term)