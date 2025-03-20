
from django.urls import path,include
from .views import (
    PatientManagementView,
    DietPlanViewSet,
    MealPortionViewSet,
    ReviewHealthStatusView,
)
from rest_framework.routers import DefaultRouter
from users.views import (
QuestionAnswerListCreateView,
DashboardView,DoctorRegistrationAPIView,
)
from patient.views import LabReportViewSet
app_name = 'doctor'


router = DefaultRouter()
router.register(r"dietplans", DietPlanViewSet)

labreport_list = LabReportViewSet.as_view({"get": "list"})

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path("lab-reports/", labreport_list, name="labreport-list"),
    path('doctor-register/', DoctorRegistrationAPIView.as_view(), name='register'),
    path('patients/', PatientManagementView.as_view(), name='view-patients'),
    path('patients/<int:patient_id>/', PatientManagementView.as_view(), name='edit-patient'),
    path('review-health-status/', ReviewHealthStatusView.as_view(), name='review-health-status'),
    path("patientresponse/", QuestionAnswerListCreateView.as_view(), name="answers"),
]
