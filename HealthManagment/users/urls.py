from django.urls import path
from .views import PatientListCreateView, SectionDataView,CombinedSectionView,PatientDetailView,DoctorListCreateView,DoctorDetailView,UserEditView, UserListView, QuestionListCreateView, QuestionDetailView, CustomLoginView,UserRegistrationAPIView,LogoutAPIView
app_name = 'users'
urlpatterns = [
    path('userdetail/', UserListView.as_view(), name='user-list'),
    path('userdetail/<int:pk>/', UserEditView.as_view(), name='user-list'),
    path('register/', UserRegistrationAPIView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
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
