from django_filters import rest_framework as filters
from .models import CustomUser, DietPlan, LabReport,Exercise

class DietPlanFilter(filters.FilterSet):
    patient_name = filters.CharFilter(field_name="patient__username", lookup_expr='icontains')
    created_by = filters.CharFilter(field_name="created_by__username", lookup_expr='icontains')
    date = filters.DateFilter(field_name="date")
    date_range = filters.DateFromToRangeFilter(field_name="date")
    calorie_intake = filters.RangeFilter(field_name="calorie_intake")

    class Meta:
        model = DietPlan
        fields = ['patient_name', 'created_by', 'date', 'date_range', 'calorie_intake']
        
class LabReportFilter(filters.FilterSet):
    patient_name = filters.CharFilter(field_name="patient__username", lookup_expr='icontains')
    uploaded_by = filters.CharFilter(field_name="uploaded_by__username", lookup_expr='icontains')
    report_date = filters.DateFilter(field_name="report_date")
    report_date_range = filters.DateFromToRangeFilter(field_name="report_date")

    class Meta:
        model = LabReport
        fields = ['patient_name', 'uploaded_by', 'report_date', 'report_date_range']   
        
class CustomUserFilter(filters.FilterSet):
    role = filters.ChoiceFilter(field_name="role", choices=CustomUser.ROLE_CHOICES)
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