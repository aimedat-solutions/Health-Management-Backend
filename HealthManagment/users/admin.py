from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Doctor, DietPlan,Question,Exercise, Patient, CustomUser,Option
admin.site.register(CustomUser)
admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(DietPlan)
admin.site.register(Exercise)
admin.site.register(Question)
admin.site.register(Option)