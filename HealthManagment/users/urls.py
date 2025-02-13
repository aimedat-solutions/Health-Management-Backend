from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import ( ExerciseListCreateView,ExerciseDetailView,
SendOrResendSMSAPIView,AdminCreateView,DoctorListCreateView,DoctorDetailView,
UserListCreateView, UserDetailView,QuestionListCreateView, QuestionDetailView, ProfileAPIView,
CustomLoginView,LogoutAPIView,DietPlanViewSet
)
app_name = 'users'


router = DefaultRouter()
router.register(r'diet-plans', DietPlanViewSet, basename='diet-plans')

urlpatterns = [
    path('', include(router.urls)),
    path('admins/create/', AdminCreateView.as_view(), name='admin-create'),
    path('profile/', ProfileAPIView.as_view(), name='profile-api'),
    path('users', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('login/', CustomLoginView.as_view(), name='login'),
    # path('send-sms/', SendOrResendSMSAPIView.as_view(), name='send-sms'),
    # path('logout/', LogoutAPIView.as_view(), name='logout'),
    
    path('doctors/', DoctorListCreateView.as_view(), name='doctor-list-create'),
    path('doctors/<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('questions/', QuestionListCreateView.as_view(), name='question-list-create'),
    path('questions/<int:id>/', QuestionDetailView.as_view(), name='question-detail'),
    path('exercises/', ExerciseListCreateView.as_view(), name='exercise-list-create'),
    path('exercises/<int:pk>/', ExerciseDetailView.as_view(), name='exercise-detail'),
]
