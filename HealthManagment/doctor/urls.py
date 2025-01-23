

from django.urls import path
from .views import (
    PatientManagementView,
    AssignDietPlanView,
    ReviewHealthStatusView,
)
from users.views import DoctorRegistrationAPIView,ProfileAPIView
urlpatterns = [
    path('register/', DoctorRegistrationAPIView.as_view(), name='register-doctor'),
    path('profile/', ProfileAPIView.as_view(), name='profile-api'),   
    path('patients/', PatientManagementView.as_view(), name='view-patients'),
    path('patients/<int:patient_id>/', PatientManagementView.as_view(), name='edit-patient'),
    path('assign-diet-plan/', AssignDietPlanView.as_view(), name='assign-diet-plan'),
    path('review-health-status/', ReviewHealthStatusView.as_view(), name='review-health-status'),
]



















# from django.urls import path,include
# from rest_framework.routers import DefaultRouter
# from .views import (
# DietPlanViewSet, QuestionAnswerListCreateView,
# LabReportViewSet,DashboardView,DoctorRegistrationAPIView,
# )
# app_name = 'doctor'


# router = DefaultRouter()
# # router.register(r'diet-plans', DietPlanViewSet, basename='diet-plans')
# # router.register(r'lab-reports', LabReportViewSet)

# urlpatterns = [
#     path('', include(router.urls)),
#     path('dashboard/', DashboardView.as_view(), name='dashboard'),
#     path('diet-plans/<int:patient_id>/<str:selected_date>/', DietPlanViewSet.as_view({'get': 'retrieve'}), name='diet-plan-retrieve-date'),
#     path('doctor-register/', DoctorRegistrationAPIView.as_view(), name='register'),
  
#     path("patientresponse/", QuestionAnswerListCreateView.as_view(), name="answers"),
# ]
