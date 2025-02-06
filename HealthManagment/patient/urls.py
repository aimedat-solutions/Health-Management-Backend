from django.urls import path, include
from .views import (
    LabReportViewSet,
    ViewHealthStatusView,PatientResponseViewSet
)
from rest_framework.routers import DefaultRouter
from users.views import DietPlanViewSet,ProfileAPIView,CustomLoginView,SendOrResendSMSAPIView,LogoutAPIView,ExerciseListCreateView

router = DefaultRouter()
app_name = 'patient'
router.register(r'diet-plans', DietPlanViewSet, basename='diet-plans')
router.register(r'answer-responses', PatientResponseViewSet, basename='patientresponse')
router.register(r'lab-reports', LabReportViewSet, basename='labreport')

urlpatterns = [
    path('', include(router.urls)),
    # path('login/', CustomLoginView.as_view(), name='login'),
    # path('register/', SendOrResendSMSAPIView.as_view(), name='send-sms'),
    # path('profile/', ProfileAPIView.as_view(), name='profile-api'),    
    path('diet-plans/<int:patient_id>/<str:selected_date>/', DietPlanViewSet.as_view({'get': 'retrieve'}), name='diet-plan-retrieve-date'),
    path('view-health-status/', ViewHealthStatusView.as_view(), name='view-health-status'),
    path('exercises/', ExerciseListCreateView.as_view(), name='exercise-list-create'),
    # path('logout/', LogoutAPIView.as_view(), name='logout'),
]












# from django.urls import path,include
# from rest_framework.routers import DefaultRouter
# from .views import ( PatientListCreateView,
# SendOrResendSMSAPIView,DietPlanViewSet,PatientDetailView,
# QuestionAnswerListCreateView,
# CustomLoginView,UserRegistrationAPIView,LogoutAPIView,LabReportViewSet,
# )
# app_name = 'patient'


# router = DefaultRouter()
# router.register(r'diet-plans', DietPlanViewSet, basename='diet-plans')
# router.register(r'lab-reports', LabReportViewSet)

# urlpatterns = [
#     path('', include(router.urls)),
#     path('login/', CustomLoginView.as_view(), name='login'),
#     path('send-sms/', SendOrResendSMSAPIView.as_view(), name='send-sms'),
#     path('logout/', LogoutAPIView.as_view(), name='logout'),
#     path('profiles/', PatientListCreateView.as_view(), name='patient-list-create'),
#     path('profiles/<int:pk>/', PatientDetailView.as_view(), name='patient-detail'),
#     path("patientresponse/", QuestionAnswerListCreateView.as_view(), name="answers"),
# ]
