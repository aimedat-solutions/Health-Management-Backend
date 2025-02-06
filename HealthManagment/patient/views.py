from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import DietPlan, LabReport, Question,PatientResponse
from .serializers import DietPlanSerializer, LabReportSerializer, QuestionSerializer
from users.permissions import PermissionsManager
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from .serializers import PatientResponseSerializer
from django_filters.rest_framework import DjangoFilterBackend
from users.filters import LabReportFilter
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet

class LabReportViewSet(viewsets.ModelViewSet):
    queryset = LabReport.objects.all()
    serializer_class = LabReportSerializer
    permission_classes = [PermissionsManager]
    codename = 'labreport'
    filter_backends = [DjangoFilterBackend, OrderingFilter] 
    filterset_class = LabReportFilter
    ordering_fields = ['date_of_report']  
    ordering = ['-date_of_report']  

    def get_queryset(self):
        user = self.request.user
        # Ensure user is authenticated
        if user.is_authenticated:
            if user.groups.filter(name='doctor').exists():  # Check if the user has the 'doctor' role
                return LabReport.objects.all()
            return LabReport.objects.filter(patient=user)
        return LabReport.objects.none()  # If the user is not authenticated, return no reports

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ViewHealthStatusView(APIView):
    """
    Allows patients to view their overall health status.
    """
    permission_classes = [PermissionsManager]

    def get(self, request):
        data = {
            'diet_plans': DietPlan.objects.filter(assigned_to=request.user).count(),
            'lab_reports': LabReport.objects.filter(patient=request.user).count(),
        }
        return Response(data)

class PatientResponseViewSet(viewsets.ModelViewSet):
    queryset = PatientResponse.objects.all()
    serializer_class = PatientResponseSerializer
    permission_classes = [PermissionsManager]
    codename = 'patientresponse'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return PatientResponse.objects.filter(user=user)
        elif user.role == 'doctor':
            return PatientResponse.objects.all()  # Doctors can see all responses
        return PatientResponse.objects.none()
        
    def perform_create(self, serializer):
        """
        Automatically associate the logged-in user with the response.
        """
        serializer.save(user=self.request.user)
        



































# from rest_framework import generics, permissions
# from users.models import Profile,  Question,DietPlan,Exercise, CustomUser,Option,PatientResponse, LabReport
# from .serializers import PatientSerializer,ExerciseSerializer, DietPlanSerializer, QuestionSerializer,QuestionAnswerSerializer,UserRegistrationSerializer,UserLoginSerializer,CustomUserDetailsSerializer,QuestionCreateSerializer,PhoneNumberSerializer,LabReportSerializer

# from django.contrib.auth.models import Group
# from rest_framework import views, status
# from rest_framework.response import Response
# from rest_framework.generics import GenericAPIView
# from rest_framework.permissions import AllowAny
# from rest_framework.authtoken.models import Token
# from dj_rest_auth.views import LoginView
# from datetime import date
# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework.authentication import authenticate
# from users.decryption import decrypt_password
# from rest_framework.views import APIView
# from django.conf import settings
# from django.contrib.auth import logout as django_logout
# from django.core.exceptions import ObjectDoesNotExist
# from drf_spectacular.utils import extend_schema
# from users.permissions import PermissionsManager
# from rest_framework import viewsets
# from rest_framework import serializers
# from rest_framework import generics
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.exceptions import NotAuthenticated
# from users.utils import send_otp, verify_otp
# from users.pagination import ProductPagination
# class UserRegistrationAPIView(APIView):
#     serializer_class = UserRegistrationSerializer
#     def post(self, request):
#         ## INECRIPTION ##
#         encrypted_phone_number = request.data.get('phone_number')
#         decrypted_phone_number = decrypt_password(encrypted_phone_number)
        
#         ## DECRIPTION ##
#         decrypted_data = {
#             'phone_number': decrypted_phone_number,
#         }
        
#         serializer = UserRegistrationSerializer(data=decrypted_data)
#         if serializer.is_valid():
#             user = serializer.save()
#             refresh = RefreshToken.for_user(user)
#             access_token = str(refresh.access_token)
#             refresh_token = str(refresh)
#             response_data = serializer.data
#             response_data['access_token'] = access_token
#             response_data['refresh_token'] = refresh_token
#             return Response(response_data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class CustomLoginView(LoginView):
#     permission_classes = [AllowAny]
#     authentication_classes = []
#     serializer_class = UserLoginSerializer
    
#     def post(self, request, *args, **kwargs):
#         # decrypted_data = {}
#         # for field, value in request.data.items():
#         #     decrypted_data[field] = decrypt_password(value)
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data['user']
#         is_new_user = user.is_first_login
#         if is_new_user:
#             # Mark the user's first login as completed
#             user.is_first_login = False
#             user.save()
#         refresh = RefreshToken.for_user(user)
#         access_token = str(refresh.access_token)
#         refresh_token = str(refresh)
#         response_data = {
#             'access_token': access_token,
#             'refresh_token': refresh_token,
#             'is_new_user': is_new_user,
#         }
#         response_data.update(CustomUserDetailsSerializer(user).data)
#         return Response(response_data, status=status.HTTP_200_OK)
    
# @extend_schema(methods=['GET'], exclude=True)
# class LogoutAPIView(APIView):
#     permission_classes = (AllowAny,)
#     throttle_scope = 'dj_rest_auth'

#     def get(self, request, *args, **kwargs):
#         if getattr(settings, 'ACCOUNT_LOGOUT_ON_GET', False):
#             response = self.logout(request)
#         else:
#             response = self.http_method_not_allowed(request, *args, **kwargs)

#         return self.finalize_response(request, response, *args, **kwargs)

#     def post(self, request, *args, **kwargs):
#         return self.logout(request)

#     def logout(self, request):
#         try:
#             request.user.auth_token.delete()
#         except (AttributeError, ObjectDoesNotExist):
#             pass

#         if getattr(settings, 'REST_SESSION_LOGIN', True):
#             django_logout(request)

#         response = Response(
#             {'detail': ('Successfully logged out.')},
#             status=status.HTTP_200_OK,
#         )

#         if getattr(settings, 'REST_USE_JWT', False):
#             from rest_framework_simplejwt.exceptions import TokenError
#             from rest_framework_simplejwt.tokens import RefreshToken

#             from .jwt_auth import unset_jwt_cookies
#             cookie_name = getattr(settings, 'JWT_AUTH_COOKIE', None)

#             unset_jwt_cookies(response)

#             if 'rest_framework_simplejwt.token_blacklist' in settings.INSTALLED_APPS:
#                 try:
#                     token = RefreshToken(request.data['refresh'])
#                     token.blacklist()
#                 except KeyError:
#                     response.data = {'detail': _(
#                         'Refresh token was not included in request data.')}
#                     response.status_code = status.HTTP_401_UNAUTHORIZED
#                 except (TokenError, AttributeError, TypeError) as error:
#                     if hasattr(error, 'args'):
#                         if 'Token is blacklisted' in error.args or 'Token is invalid or expired' in error.args:
#                             response.data = {'detail': _(error.args[0])}
#                             response.status_code = status.HTTP_401_UNAUTHORIZED
#                         else:
#                             response.data = {'detail': _(
#                                 'An error has occurred.')}
#                             response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#                     else:
#                         response.data = {'detail': _('An error has occurred.')}
#                         response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#             elif not cookie_name:
#                 message = _(
#                     'Neither cookies or blacklist are enabled, so the token '
#                     'has not been deleted server side. Please make sure the token is deleted client side.',
#                 )
#                 response.data = {'detail': message}
#                 response.status_code = status.HTTP_200_OK
#         return response

# class SendOrResendSMSAPIView(GenericAPIView):
#     serializer_class = PhoneNumberSerializer
    
#     """
#     API endpoint to send OTP to the user's phone number.
#     """
#     def post(self, request):
#         phone_number = request.data.get("phone_number", None)

#         if phone_number:
#             try:
#                 # Check if the user already exists (for login flow)
#                 user = CustomUser.objects.get(phone_number=phone_number)
#                 send_otp(phone_number)  # Send OTP
#                 user.save()
#                 return Response({"message": "OTP sent for login.", "is_new_user": False}, status=status.HTTP_200_OK)

#             except CustomUser.DoesNotExist:
#                 # If the user does not exist (for registration flow)
#                 user = CustomUser(phone_number=phone_number, role='patient', username=phone_number, is_first_login=True, password=CustomUser.objects.make_random_password(),)
#                 user.save()
#                 group = Group.objects.get(name=user.role)
#                 user.groups.add(group)
#                 send_otp(phone_number)   # Send OTP
                
#                 return Response({"message": "OTP sent for registration.", "is_new_user": True}, status=status.HTTP_200_OK)
#         else:
#             return Response({"error": "Phone number is required"}, status=status.HTTP_400_BAD_REQUEST)
        
# class UserListView(generics.ListAPIView):
#     queryset = CustomUser.objects.all()
#     serializer_class = CustomUserDetailsSerializer
    
# class UserEditView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = CustomUser.objects.all()
#     serializer_class = CustomUserDetailsSerializer
#     permission_classes = [PermissionsManager]
#     codename = 'doctor'
# class PatientListCreateView(generics.ListCreateAPIView):
#     queryset = Profile.objects.all()
#     serializer_class = PatientSerializer
#     permission_classes = [PermissionsManager]
#     codename = 'profile'

# class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Profile.objects.all()
#     serializer_class = PatientSerializer
#     permission_classes = [PermissionsManager]
#     codename = 'profile'
            
# class DietPlanViewSet(viewsets.ModelViewSet):
#     queryset = DietPlan.objects.all()
#     serializer_class = DietPlanSerializer
#     permission_classes = [PermissionsManager]
#     codename = 'dietplan'

#     def perform_create(self, serializer):
#         patient_id = self.request.data.get('patient_id')
#         try:
#             patient = Profile.objects.get(id=patient_id)
#         except Profile.DoesNotExist:
#             raise serializers.ValidationError("Patient does not exist.")
#         serializer.save(patient=patient)
    
#     def retrieve(self, request, patient_id, selected_date):
#         try:
#             # Convert selected_date to a date object
#             selected_date = date.fromisoformat(selected_date)
#             # Retrieve the diet plan for the specific date
#             diet_plan = DietPlan.objects.filter(patient_id=patient_id, date=selected_date)

#             if not diet_plan.exists():
#                 return Response({"error": "Diet plan not found for the selected date."}, status=status.HTTP_404_NOT_FOUND)

#             serializer = DietPlanSerializer(diet_plan, many=True)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except ValueError:
#             return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
#     # def get_queryset(self):
#     #     user = self.request.user
#     #     if hasattr(user, 'doctor' and 'admin'):
#     #         return DietPlan.objects.filter(patient__doctor=user.doctor)
#     #     return DietPlan.objects.none()

# class QuestionListCreateView(generics.ListCreateAPIView):
#     queryset = Question.objects.all()
#     pagination_class = ProductPagination
#     permission_classes = [PermissionsManager]
#     codename = 'doctor'

#     def get_serializer_class(self):
#         if self.request.method == 'POST':
#             return QuestionCreateSerializer
#         return QuestionSerializer

#     def perform_create(self, serializer):
#         serializer.save()
# class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Question.objects.all()
#     serializer_class = QuestionCreateSerializer
#     lookup_field = 'id'
#     permission_classes = [PermissionsManager]
#     codename = 'doctor'

#     def get_serializer_class(self):
#         if self.request.method in ['PUT', 'PATCH']:
#             return QuestionCreateSerializer
#         return QuestionSerializer

#     def perform_update(self, serializer):
#         serializer.save()
    
# class ExerciseListCreateView(generics.ListCreateAPIView):
#     serializer_class = ExerciseSerializer
#     # permission_classes = [IsAuthenticated]
#     permission_classes = [PermissionsManager]
#     codename = 'exercise'

#     def get_queryset(self):
#         # Return only exercises for the authenticated user
#         return Exercise.objects.filter(user=self.request.user)

#     def perform_create(self, serializer):
#         # Link the exercise to the authenticated user
#         serializer.save(user=self.request.user)
        
#     def permission_denied(self, request, message=None, code=None):
#         if not request.user or not request.user.is_authenticated:
#             raise NotAuthenticated(detail="Custom message: You are not authenticated. Please log in.")

# class ExerciseDetailView(generics.RetrieveUpdateDestroyAPIView):
#     serializer_class = ExerciseSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         # Ensure users can only access their own exercises
#         return Exercise.objects.filter(user=self.request.user) 
    

# class QuestionAnswerListCreateView(APIView):
#     serializer_class = QuestionAnswerSerializer
#     permission_classes = [IsAuthenticated]
   
#     def get(self, request):
#         """
#         Get all answers by the logged-in user.
#         """
#         answers = PatientResponse.objects.filter(user=request.user)
#         serializer = QuestionAnswerSerializer(answers, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

#     def post(self, request):
#         """
#         Submit answers for specific questions.
#         """
#         data = request.data
#         data["user"] = request.user.id  # Attach the logged-in user

#         serializer = QuestionAnswerSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# # LabReport ViewSet
# class LabReportViewSet(viewsets.ModelViewSet):
#     queryset = LabReport.objects.all()
#     serializer_class = LabReportSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         user = self.request.user
#         # Ensure user is authenticated
#         if user.is_authenticated:
#             if user.groups.filter(name='doctor').exists():  # Check if the user has the 'doctor' role
#                 return LabReport.objects.all()
#             return LabReport.objects.filter(patient=user)
#         return LabReport.objects.none()  # If the user is not authenticated, return no reports

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         return Response(serializer.data, status=status.HTTP_201_CREATED)

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance)
#         return Response(serializer.data)

#     def update(self, request, *args, **kwargs):
#         partial = kwargs.pop('partial', False)
#         instance = self.get_object()
#         serializer = self.get_serializer(instance, data=request.data, partial=partial)
#         serializer.is_valid(raise_exception=True)
#         self.perform_update(serializer)
#         return Response(serializer.data)

#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         self.perform_destroy(instance)
#         return Response(status=status.HTTP_204_NO_CONTENT)

# class DashboardView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         # Retrieve data for the logged-in patient (user)
#         patient = request.user

#         # Get data related to the patient
#         total_diets = DietPlan.objects.filter(patient=patient).count()
#         total_exercises = Exercise.objects.filter(user=patient).count()
#         total_lab_reports = LabReport.objects.filter(patient=patient).count()

#         # Return the summary data as a response
#         dashboard_data = {
#             "total_diets": total_diets,
#             "total_exercises": total_exercises,
#             "total_lab_reports": total_lab_reports,
#         }
#         return Response(dashboard_data)
    
    
    
    
    
    
    
    
    
    
    
    
# from django.shortcuts import render
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import redirect

# @login_required
# def doctor_dashboard(request):
#     return render(request, 'templates/dashboard.html')

# @login_required
# def patient_dashboard(request):
#     return render(request, 'templates/patientdashboard.html')

# @login_required
# def admin_dashboard(request):
#     return render(request, 'templates/admindashboard.html')

# def role_based_redirect(request):
#     if request.user.role == 'doctor':
#         return redirect('users:doctor-dashboard')
#     elif request.user.role == 'patient':
#         return redirect('users:patient-dashboard')
#     elif request.user.is_superuser:
#         return redirect('users:admin-dashboard')
#     return redirect('users:login')