from django_filters import rest_framework as filters
from .models import CustomUser, DietPlan, LabReport,Exercise,RoleChoices
import django_filters

class DietPlanFilter(filters.FilterSet):
    """
    Filter set for DietPlan model.
    """
    patient_name = filters.CharFilter(field_name="patient__username", lookup_expr='icontains')
    doctor_name = filters.CharFilter(field_name="doctor__username", lookup_expr='icontains')
    date = django_filters.DateFilter(field_name="date", lookup_expr="exact")
    date_range = filters.DateFromToRangeFilter(field_name="date")
    blood_sugar_range = filters.CharFilter(field_name="blood_sugar_range", lookup_expr='icontains')
    meal_time = filters.CharFilter(field_name="meal_time", lookup_expr='icontains')
    trimester = filters.CharFilter(field_name="trimester", lookup_expr='icontains')

    class Meta:
        model = DietPlan
        fields = ['patient_name', 'doctor_name', 'date', 'date_range', 'blood_sugar_range', 'meal_time', 'trimester']
        
class LabReportFilter(filters.FilterSet):
    patient_name = filters.CharFilter(field_name="patient__username", lookup_expr='icontains')
    uploaded_by = filters.CharFilter(field_name="uploaded_by__username", lookup_expr='icontains')
    report_date = filters.DateFilter(field_name="report_date")
    report_date_range = filters.DateFromToRangeFilter(field_name="report_date")

    class Meta:
        model = LabReport
        fields = ['patient_name', 'uploaded_by', 'report_date', 'report_date_range']   
        
class CustomUserFilter(filters.FilterSet):
    role = filters.ChoiceFilter(field_name="role", choices=RoleChoices.choices)
    email = filters.CharFilter(field_name="email", lookup_expr='icontains')
    first_name = filters.CharFilter(field_name="first_name", lookup_expr='icontains')
    last_name = filters.CharFilter(field_name="last_name", lookup_expr='icontains')

    class Meta:
        model = CustomUser
        fields = ['role', 'email', 'first_name', 'last_name']


class ExerciseFilter(filters.FilterSet):
    patient_name = filters.CharFilter(field_name="user__username", lookup_expr='icontains')
    date = filters.DateFilter(field_name="date")
    date_range = filters.DateFromToRangeFilter(field_name="date")
    

    class Meta:
        model = Exercise
        fields = ['exercise_name', 'exercise_type', 'date', 'date_range', 'patient_name']