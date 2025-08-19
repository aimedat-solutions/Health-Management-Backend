
from django.urls import path,include
from .views import (
    PatientManagementViewSet,
    DietPlanViewSet,
    MealPortionViewSet,
    ReviewHealthStatusView,
    DoctorAssignExerciseView,
    DoctorExerciseReviewView,
)
from rest_framework.routers import DefaultRouter
from users.views import (
QuestionAnswerListCreateView,
DashboardView,DoctorRegistrationAPIView,
ExerciseListCreateView
)
from patient.views import LabReportViewSet
app_name = 'doctor'


router = DefaultRouter()
router.register(r"assign-dietplans", DietPlanViewSet, basename='dietplan')
router.register(r"patients", PatientManagementViewSet, basename='patient')

labreport_list = LabReportViewSet.as_view({"get": "list"})

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path("lab-reports/", labreport_list, name="labreport-list"),
    path('doctor-register/', DoctorRegistrationAPIView.as_view(), name='register'),
    path('exercises/', ExerciseListCreateView.as_view(), name='exercise-list-create'),
    path('assign-excercise/',DoctorAssignExerciseView.as_view(), name='assign-exercise'),
    path("exercise-review/", DoctorExerciseReviewView.as_view(), name="doctor-review"),
    path('review-health-status/', ReviewHealthStatusView.as_view(), name='review-health-status'),
    path("patientresponse/", QuestionAnswerListCreateView.as_view(), name="answers"),
]
