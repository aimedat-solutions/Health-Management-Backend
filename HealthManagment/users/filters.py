from django.db.models import Q
from django_filters import rest_framework as filters
from .models import (
    CustomUser, DietPlan, LabReport, Exercise, RoleChoices,
    PatientDietQuestion, DietPlanDate, ExerciseDate, Question,
    MealPortion, PatientResponse, PatientExerciseLog, HealthEducation
)
from notification.models import Notification
import django_filters

class DietPlanMealFilter(filters.FilterSet):
    date = filters.DateFilter(field_name="date", lookup_expr="exact")

    class Meta:
        model = DietPlanDate
        fields = ['date']

class DietPlanFilter(filters.FilterSet):
    patient_name = filters.CharFilter(method='filter_patient_name', label='Patient name')
    doctor_name = filters.CharFilter(method='filter_doctor_name', label='Doctor name')
    date = django_filters.DateFilter(field_name="diet_dates__date", lookup_expr="exact")
    date_range = filters.DateFromToRangeFilter(field_name="diet_dates__date")
    blood_sugar_range = filters.CharFilter(field_name="blood_sugar_range", lookup_expr='icontains')
    meal_time = filters.CharFilter(field_name="meal_time", lookup_expr='icontains')
    trimester = filters.CharFilter(field_name="trimester", lookup_expr='icontains')

    class Meta:
        model = DietPlan
        fields = ['patient_name', 'doctor_name', 'date', 'date_range', 'blood_sugar_range', 'meal_time', 'trimester']

    def filter_patient_name(self, queryset, name, value):
        return queryset.filter(
            Q(patient__profile__first_name__icontains=value) |
            Q(patient__profile__last_name__icontains=value)
        )

    def filter_doctor_name(self, queryset, name, value):
        return queryset.filter(
            Q(doctor__profile__first_name__icontains=value) |
            Q(doctor__profile__last_name__icontains=value)
        )

class LabReportFilter(filters.FilterSet):
    patient_name = filters.CharFilter(method='filter_patient_name', label='Patient name')
    phone_number = filters.CharFilter(field_name="patient__phone_number", lookup_expr='icontains')
    uploaded_by = filters.CharFilter(field_name="uploaded_by__username", lookup_expr='icontains')
    date_of_report = filters.DateFilter(field_name="date_of_report")
    date_of_report_range = filters.DateFromToRangeFilter(field_name="date_of_report")
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = LabReport
        fields = ['phone_number', 'patient_name', 'uploaded_by', 'date_of_report', 'date_of_report_range', 'search']

    def filter_patient_name(self, queryset, name, value):
        return queryset.filter(
            Q(patient__profile__first_name__icontains=value) |
            Q(patient__profile__last_name__icontains=value)
        )

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(report_name__icontains=value) |
            Q(patient__phone_number__icontains=value)
        )

class CustomUserFilter(filters.FilterSet):
    role = filters.ChoiceFilter(field_name="role", choices=RoleChoices.choices)
    email = filters.CharFilter(field_name="email", lookup_expr='icontains')
    phone_number = filters.CharFilter(field_name="phone_number", lookup_expr='icontains')
    first_name = filters.CharFilter(field_name="profile__first_name", lookup_expr='icontains')
    last_name = filters.CharFilter(field_name="profile__last_name", lookup_expr='icontains')
    age = filters.NumberFilter(field_name="profile__age", lookup_expr="exact")
    age__gte = filters.NumberFilter(field_name="profile__age", lookup_expr="gte")
    age__lte = filters.NumberFilter(field_name="profile__age", lookup_expr="lte")
    date_joined__gte = filters.DateFilter(field_name="date_joined", lookup_expr="gte")
    date_joined__lte = filters.DateFilter(field_name="date_joined", lookup_expr="lte")
    is_verified = filters.BooleanFilter(field_name="is_verified")
    is_first_login = filters.BooleanFilter(field_name="is_first_login")
    risk = filters.CharFilter(field_name="profile__health_status", lookup_expr='icontains')
    month = filters.NumberFilter(method='filter_month')
    status = filters.CharFilter(method='filter_status')
    filter = filters.CharFilter(method='filter_tab')

    class Meta:
        model = CustomUser
        fields = [
            'role', 'email', 'phone_number', 'first_name', 'last_name',
            'age', 'age__gte', 'age__lte',
            'date_joined__gte', 'date_joined__lte',
            'is_verified', 'is_first_login', 'risk', 'month', 'status', 'filter',
        ]

    def filter_month(self, queryset, name, value):
        from django.utils.timezone import now
        from datetime import timedelta
        n = int(value)
        today = now().date()
        start = today - timedelta(days=n * 28)
        end = today - timedelta(days=(n - 1) * 28)
        return queryset.filter(profile__lmp_date__gte=start, profile__lmp_date__lt=end)

    def filter_status(self, queryset, name, value):
        if value == 'active':
            return queryset.filter(initial_question_completed=True)
        elif value == 'onboarding':
            return queryset.filter(initial_question_completed=False)
        return queryset

    def filter_tab(self, queryset, name, value):
        if value == 'verified':
            return queryset.filter(is_verified=True)
        elif value in ('poor', 'critical'):
            return queryset.filter(profile__health_status__iexact=value)
        return queryset

class ExerciseFilter(filters.FilterSet):
    class Meta:
        model = Exercise
        fields = ['title', 'id', 'description']

class DietQuestionFilter(filters.FilterSet):
    date = filters.DateFilter(field_name='last_diet_update')

    class Meta:
        model = PatientDietQuestion
        fields = ['date']

class QuestionFilter(filters.FilterSet):
    question_text = filters.CharFilter(lookup_expr='icontains')
    parent__isnull = filters.BooleanFilter(field_name="parent", lookup_expr="isnull", label="Top-level only")

    class Meta:
        model = Question
        fields = ['category', 'type', 'question_text', 'parent__isnull']

class MealPortionFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    calories__gte = filters.NumberFilter(field_name="calories", lookup_expr="gte")
    calories__lte = filters.NumberFilter(field_name="calories", lookup_expr="lte")
    protein__gte = filters.NumberFilter(field_name="protein", lookup_expr="gte")
    protein__lte = filters.NumberFilter(field_name="protein", lookup_expr="lte")
    fat__gte = filters.NumberFilter(field_name="fat", lookup_expr="gte")
    fat__lte = filters.NumberFilter(field_name="fat", lookup_expr="lte")
    carbohydrates__gte = filters.NumberFilter(field_name="carbohydrates", lookup_expr="gte")
    carbohydrates__lte = filters.NumberFilter(field_name="carbohydrates", lookup_expr="lte")

    class Meta:
        model = MealPortion
        fields = [
            'name', 'ai_generated', 'serving_unit',
            'calories__gte', 'calories__lte',
            'protein__gte', 'protein__lte',
            'fat__gte', 'fat__lte',
            'carbohydrates__gte', 'carbohydrates__lte',
        ]

class NotificationFilter(filters.FilterSet):
    created_at__gte = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = filters.DateFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Notification
        fields = ['is_read', 'notification_type', 'created_at__gte', 'created_at__lte']

class PatientResponseFilter(filters.FilterSet):
    created_at__gte = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = filters.DateFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = PatientResponse
        fields = ['question__category', 'question', 'created_at__gte', 'created_at__lte']

class PatientExerciseLogFilter(filters.FilterSet):
    date__gte = filters.DateFilter(field_name="date", lookup_expr="gte")
    date__lte = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = PatientExerciseLog
        fields = ['date', 'date__gte', 'date__lte']

class HealthEducationFilter(filters.FilterSet):
    class Meta:
        model = HealthEducation
        fields = ['category', 'is_active', 'title']