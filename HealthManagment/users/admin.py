from django.contrib import admin
from .models import (
    CustomUser, Profile, Exercise, DoctorExerciseResponse, Question, PatientDietSchedule,
    Option, DietPlan, PatientResponse, LabReport, HealthStatus
)

admin.site.site_header = "MHealth Admin"
admin.site.index_title = "Welcome to MHealth Management Dashboard"

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'phone_number', 'email', 'role', 'is_verified', 'is_active','is_staff']
    search_fields = ['username', 'phone_number', 'email']
    list_filter = ['role', 'is_verified', 'is_active', 'date_joined']

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'first_name', 'last_name', 'gender', 'age', 'height', 'weight']
    search_fields = ['user__username', 'first_name', 'last_name']
    list_filter = ['gender']

class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['user', 'exercise_name', 'exercise_type', 'duration', 'intensity', 'calories_burned', 'date']
    search_fields = ['exercise_name', 'user__username']
    list_filter = ['exercise_type', 'intensity', 'date']

class DoctorExerciseResponseAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'user', 'exercise', 'review']
    search_fields = ['doctor__username', 'user__username', 'exercise__exercise_name']
    list_filter = ['doctor']

class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'type', 'max_length']
    search_fields = ['question_text']
    list_filter = ['type']

class OptionAdmin(admin.ModelAdmin):
    list_display = ['question', 'value']
    search_fields = ['value', 'question__question_text']

class DietPlanAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'title', 'meal_time', 'blood_sugar_range', 'trimester', 'date']
    search_fields = ['patient__username', 'doctor__username', 'title']
    list_filter = ['meal_time', 'blood_sugar_range', 'trimester', 'date']

class PatientResponseAdmin(admin.ModelAdmin):
    list_display = ['user', 'question', 'response_text', 'created_at']
    search_fields = ['user__username', 'question__question_text']
    list_filter = ['created_at']

class LabReportAdmin(admin.ModelAdmin):
    list_display = ['patient', 'report_name', 'date_of_report']
    search_fields = ['patient__username', 'report_name']
    list_filter = ['date_of_report']

class HealthStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'calories', 'height', 'weight', 'months', 'status']
    search_fields = ['user__username']
    list_filter = ['months']

# Register all models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Exercise, ExerciseAdmin)
admin.site.register(DoctorExerciseResponse, DoctorExerciseResponseAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Option, OptionAdmin)
admin.site.register(DietPlan, DietPlanAdmin)
admin.site.register(PatientResponse, PatientResponseAdmin)
admin.site.register(PatientDietSchedule)
admin.site.register(LabReport, LabReportAdmin)
admin.site.register(HealthStatus, HealthStatusAdmin)
