from django.contrib import admin
from .models import (
    CustomUser, Profile, Exercise, DoctorExerciseResponse, Question, PatientDietQuestion,
    Option, DietPlanMeal, PatientResponse, LabReport, HealthStatus
)

admin.site.site_header = "MHealth Admin"
admin.site.index_title = "Welcome to MHealth Management Dashboard"

# Register all models
admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Exercise)
admin.site.register(DoctorExerciseResponse)
admin.site.register(Question)
admin.site.register(Option)
admin.site.register(DietPlanMeal)
admin.site.register(PatientResponse)
admin.site.register(PatientDietQuestion)
admin.site.register(LabReport)
admin.site.register(HealthStatus)
