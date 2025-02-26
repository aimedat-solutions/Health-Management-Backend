from django.urls import path, include
from .views import (
    LabReportViewSet,
    ViewHealthStatusView,PatientResponseViewSet,InitialQuestionsView,DietQuestionsView,
)
from rest_framework.routers import DefaultRouter
from users.views import DietPlanViewSet,ProfileAPIView,ExerciseListCreateView

router = DefaultRouter()
app_name = 'patient'
router.register(r'diet-plans', DietPlanViewSet, basename='diet-plans')
router.register(r'answers-intial-questions', PatientResponseViewSet, basename='patientresponse')
router.register(r'lab-reports', LabReportViewSet, basename='labreport')

urlpatterns = [
    path('', include(router.urls)),
    path("initial-questions/", InitialQuestionsView.as_view(), name="initial-questions"),
    path("diet-questions/", DietQuestionsView.as_view(), name="diet-questions"),
    path('diet-plans/<int:patient_id>/<str:selected_date>/', DietPlanViewSet.as_view({'get': 'retrieve'}), name='diet-plan-retrieve-date'),
    path('view-health-status/', ViewHealthStatusView.as_view(), name='view-health-status'),
    path('exercises/', ExerciseListCreateView.as_view(), name='exercise-list-create'),
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
