from django.urls import path, include
from .views import (
    LabReportViewSet,
    ViewHealthStatusView,PatientResponseViewSet,InitialQuestionsView,DietQuestionsView,DietQuestionStatusView,
    CompleteSkipDietPlanView, DietPlanView,CompleteSkipExerciseView,PatientAssignedExercisesView,QuestionFlowStatusView,
    CurrentOrNextMealView
    
)
from rest_framework.routers import DefaultRouter
from users.views import ProfileAPIView,ExerciseListCreateView

router = DefaultRouter()
app_name = 'patient'
router.register(r'answers-intial-questions', PatientResponseViewSet, basename='patientresponse')
router.register(r'lab-reports', LabReportViewSet, basename='labreport')

urlpatterns = [
    path('', include(router.urls)),
    path('question-flow-status/', QuestionFlowStatusView.as_view(), name='question-flow-status'),
    path("initial-questions/", InitialQuestionsView.as_view(), name="initial-questions"),
    path("diet-questions/", DietQuestionsView.as_view(), name="diet-questions"),
    path("diet-question/status/", DietQuestionStatusView.as_view(), name="diet-question-status"),
    path("diet/current-meal/", CurrentOrNextMealView.as_view(), name="current-diet-meal"),
    path('diet-plan/', DietPlanView.as_view(), name='diet_plan_list'),
    path('diet-plan-status-update/', CompleteSkipDietPlanView.as_view(), name='skip-complete_diet_plan'),
    path('view-health-status/', ViewHealthStatusView.as_view(), name='view-health-status'),
    path('exercises/', PatientAssignedExercisesView.as_view(), name='exercise-list'),
    path("exercise/status-update/", CompleteSkipExerciseView.as_view(), name="exercise-update-status"),
]