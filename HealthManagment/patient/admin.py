from django.contrib import admin
from users.models import DietPlanStatus,ExerciseStatus,ExtraMeal,DietPlanCompletedPortion
# Register your models here.
admin.site.register(DietPlanStatus)
admin.site.register(ExerciseStatus)
admin.site.register(ExtraMeal)
admin.site.register(DietPlanCompletedPortion)
