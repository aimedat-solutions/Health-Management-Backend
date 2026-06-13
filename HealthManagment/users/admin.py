from django.contrib import admin
from .models import (
    CustomUser, Profile, Exercise, DoctorExerciseResponse, Question, PatientDietQuestion, PatientExerciseLog, ExerciseLogEntry, HealthEducation,HelpContent,
    Option, DietPlanMeal, PatientResponse, LabReport, HealthStatus,MealPortion,DietPlan,DietPlanDate,ExerciseDate,DailyStepCount,AppContent
)

admin.site.site_header = "MHealth Admin"
admin.site.index_title = "Welcome to MHealth Management Dashboard"

# Register all models
admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Exercise)
admin.site.register(ExerciseDate)
admin.site.register(DoctorExerciseResponse)
admin.site.register(Question)
admin.site.register(Option)
admin.site.register(DietPlan)
admin.site.register(DietPlanDate)
admin.site.register(DietPlanMeal)
admin.site.register(MealPortion)
admin.site.register(PatientResponse)

admin.site.register(AppContent)

class ExerciseLogEntryInline(admin.TabularInline):
    model = ExerciseLogEntry
    extra = 1
    fields = ('time_slot', 'activity_type', 'duration_minutes', 'effort_level', 'symptoms', 'custom_symptom')

@admin.register(PatientExerciseLog)
class PatientExerciseLogAdmin(admin.ModelAdmin):
    list_display = ('patient', 'date', 'entry_count', 'created_at')
    list_filter = ('date',)
    search_fields = ('patient__phone_number', 'patient__username')
    inlines = [ExerciseLogEntryInline]

    def entry_count(self, obj):
        return obj.entries.count()
    entry_count.short_description = 'Entries'

admin.site.register(PatientDietQuestion)
admin.site.register(LabReport)
admin.site.register(HealthStatus)
admin.site.register(HealthEducation)
@admin.register(DailyStepCount)
class DailyStepAdmin(admin.ModelAdmin):
    list_display = ("patient", "date", "steps", "goal_steps", "status", "source")
    list_filter = ("status", "source")

@admin.register(HelpContent)
class HelpContentAdmin(admin.ModelAdmin):
    list_display = (
        "content_type",
        "screen_name",
        "title",
        "step_order",
        "is_active",
    )
    list_filter = ("content_type", "screen_name", "is_active")
    ordering = ("screen_name", "step_order")