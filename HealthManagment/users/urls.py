from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import PatientListCreateView,ExerciseListCreateView,ExerciseDetailView, SendOrResendSMSAPIView,DietPlanViewSet,SectionDataView,CombinedSectionView,PatientDetailView,DoctorListCreateView,DoctorDetailView,UserEditView, UserListView, QuestionListCreateView, QuestionDetailView, CustomLoginView,UserRegistrationAPIView,LogoutAPIView

app_name = 'users'


router = DefaultRouter()
router.register(r'diet-plans', DietPlanViewSet, basename='diet-plans')

urlpatterns = [
    path('', include(router.urls)),
    path('diet-plans/<int:patient_id>/<str:selected_date>/', DietPlanViewSet.as_view({'get': 'retrieve'}), name='diet-plan-retrieve-date'),
    path('exercises/', ExerciseListCreateView.as_view(), name='exercise-list-create'),
    path('exercises/<int:pk>/', ExerciseDetailView.as_view(), name='exercise-detail'),
    path('userdetail/', UserListView.as_view(), name='user-list'),
    path('userdetail/<int:pk>/', UserEditView.as_view(), name='user-list'),
    path('register/', UserRegistrationAPIView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('send-sms/', SendOrResendSMSAPIView.as_view(), name='send-sms'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('patients/', PatientListCreateView.as_view(), name='patient-list-create'),
    path('patients/<int:pk>/', PatientDetailView.as_view(), name='patient-detail'),
    path('doctors/', DoctorListCreateView.as_view(), name='doctor-list-create'),
    path('doctors/<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('questions/', QuestionListCreateView.as_view(), name='question-list-create'),
    path('questions/<int:pk>/', QuestionDetailView.as_view(), name='question-detail'),
    
    path('questions-add/', CombinedSectionView.as_view(), name='submit-section'),
    path('get-section/<str:section_type>/<int:user_id>/', SectionDataView.as_view(), name='get-section'),
]
