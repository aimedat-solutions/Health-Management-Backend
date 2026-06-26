
from django.urls import path,include
from .views import (
    PatientManagementViewSet,
    DietPlanViewSet,
    MealPortionViewSet,
    ReviewHealthStatusView,
    DoctorAssignExerciseView,
    DoctorExerciseReviewView,
    DoctorDietLogsView,
    DoctorExerciseLogsView,
    LabReportEntryViewSet
)
from rest_framework.routers import DefaultRouter
from users.views import (
QuestionAnswerListCreateView,DoctorRegistrationAPIView,
ExerciseListCreateView
)
from patient.views import LabReportViewSet
app_name = 'doctor'


router = DefaultRouter()
router.register(r"assign-dietplans", DietPlanViewSet, basename='dietplan')
router.register(r"patients", PatientManagementViewSet, basename='patient')
router.register(r"mealportions", MealPortionViewSet, basename='mealportion')

labreport_list = LabReportViewSet.as_view({"get": "list"})
labreportentry_list = LabReportEntryViewSet.as_view({"get": "list", "post": "create"})
labreportentry_detail = LabReportEntryViewSet.as_view({
    "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"
})

urlpatterns = [
    path('', include(router.urls)),
    path("lab-reports/", labreport_list, name="labreport-list"),
    path("lab-reports/<int:lab_report_id>/entries/", labreportentry_list, name="labreportentry-list"),
    path("lab-report-entries/<int:pk>/", labreportentry_detail, name="labreportentry-detail"),
    path('doctor-register/', DoctorRegistrationAPIView.as_view(), name='register'),
    path('exercises/', ExerciseListCreateView.as_view(), name='exercise-list-create'),
    path('assign-excercise/', DoctorAssignExerciseView.as_view(), name='assign-exercise'),
    path("exercise-review/", DoctorExerciseReviewView.as_view(), name="doctor-review"),
    path('review-health-status/', ReviewHealthStatusView.as_view(), name='review-health-status'),
    path("patientresponse/", QuestionAnswerListCreateView.as_view(), name="answers"),
    path("diet-questions-logs/", DoctorDietLogsView.as_view()),
    path("exercise-logs/", DoctorExerciseLogsView.as_view()),
]
