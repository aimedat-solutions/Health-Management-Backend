from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import ( ExerciseListCreateView,ExerciseDetailView,HealthEducationView,
 SendOrResendSMSAPIView,AdminCreateView,DoctorListCreateView,DoctorDetailView,
 UserListCreateView, UserDetailView,QuestionListCreateView, QuestionDetailView, ProfileAPIView,
 CustomLoginView,SyncStepsView, TodayStepsView, WeeklyStepsView,AppContentView,HelpContentView,
 AcceptLegalView,AdminDietPlanListView,AdminDoctorDietPlansView,AdminDoctorPatientsView
)
from doctor.views import MealPortionViewSet
app_name = 'users'


router = DefaultRouter()
router.register(r"mealportions", MealPortionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('admins/create/', AdminCreateView.as_view(), name='admin-create'),
    path('profile/', ProfileAPIView.as_view(), name='profile-api'),
    path('users', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('login/', CustomLoginView.as_view(), name='login'),
    
    path('doctors/', DoctorListCreateView.as_view(), name='doctor-list-create'),
    path('doctors/<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('questions/', QuestionListCreateView.as_view(), name='question-list-create'),
    path('questions/<int:id>/', QuestionDetailView.as_view(), name='question-detail'),
    path('exercises/', ExerciseListCreateView.as_view(), name='exercise-list-create'),
    path('exercises/<int:pk>/', ExerciseDetailView.as_view(), name='exercise-detail'),
    
    
    path("legal-accept/", AcceptLegalView.as_view()),
    path("app-content/", AppContentView.as_view()),
    path("help-content/", HelpContentView.as_view()),
    path("health-education/", HealthEducationView.as_view()),
    path("steps/sync/", SyncStepsView.as_view()),
    path("steps/today/", TodayStepsView.as_view()),
    path("steps/weekly/", WeeklyStepsView.as_view()),
    
    path('dietplans/', AdminDietPlanListView.as_view(), name='admin-dietplan-list'),
    path('doctors/<int:doctor_id>/dietplans/', AdminDoctorDietPlansView.as_view(), name='admin-doctor-dietplans'),
    path('doctors/<int:doctor_id>/patients/', AdminDoctorPatientsView.as_view(), name='admin-doctor-patients'),
]
