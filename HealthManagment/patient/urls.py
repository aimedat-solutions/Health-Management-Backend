from django.urls import path, include
from .views import (
    LabReportViewSet,
    ViewHealthStatusView,PatientResponseViewSet,InitialQuestionsView,DietQuestionsView,
)
from rest_framework.routers import DefaultRouter
from users.views import DietPlanViewSet,ProfileAPIView,ExerciseListCreateView

router = DefaultRouter()
app_name = 'patient'
router.register(r'diet-plans', DietPlanViewSet, basename='dietplan')
router.register(r'answers-intial-questions', PatientResponseViewSet, basename='patientresponse')
router.register(r'lab-reports', LabReportViewSet, basename='labreport')

urlpatterns = [
    path('', include(router.urls)),
    path("initial-questions/", InitialQuestionsView.as_view(), name="initial-questions"),
    path("diet-questions/", DietQuestionsView.as_view(), name="diet-questions"),
    path('diet-plans/<int:pk>/update-status/', DietPlanViewSet.as_view({'post': 'update_status'}), name='dietplan-update-status'),
    path('view-health-status/', ViewHealthStatusView.as_view(), name='view-health-status'),
    path('exercises/', ExerciseListCreateView.as_view(), name='exercise-list-create'),
]