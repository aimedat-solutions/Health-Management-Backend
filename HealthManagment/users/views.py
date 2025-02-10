from rest_framework import generics, permissions
from .models import Profile, Question,DietPlan,Exercise, CustomUser,Option,PatientResponse, LabReport,DoctorExerciseResponse,HealthStatus
from .serializers import ExerciseSerializer, ProfileSerializer, DietPlanSerializer, DoctorRegistrationSerializer, QuestionSerializer,QuestionAnswerSerializer,UserRegistrationSerializer,UserLoginSerializer,CustomUserDetailsSerializer,QuestionCreateSerializer,PhoneNumberSerializer,LabReportSerializer
from django.db.models import Count
from django.contrib.auth.models import Group
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from dj_rest_auth.views import LoginView
from datetime import date
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import authenticate
from .decryption import decrypt_password
from rest_framework.views import APIView
from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema
from users.permissions import PermissionsManager,IsSuperAdmin, IsAdmin
from rest_framework import viewsets
from rest_framework import serializers
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotAuthenticated
from .utils import send_otp, verify_otp
from .pagination import Pagination
from django_filters.rest_framework import DjangoFilterBackend
from .filters import CustomUserFilter, DietPlanFilter,ExerciseFilter
import os
class UserRegistrationAPIView(APIView):
    serializer_class = UserRegistrationSerializer
    def post(self, request):
        # decrypted_data = {}
        # for field, value in request.data.items():
        #     decrypted_data[field] = decrypt_password(value)
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            response_data = serializer.data
            response_data['access_token'] = access_token
            response_data['refresh_token'] = refresh_token
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomLoginView(LoginView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = UserLoginSerializer
    
    def post(self, request, *args, **kwargs):
    #     decrypted_data = {}
    #     for field, value in request.data.items():
    #         decrypted_data[field] = decrypt_password(value)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        is_new_user = user.is_first_login
        if is_new_user:
            user.is_first_login = False
            user.save()
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        response_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'is_new_user': is_new_user,   
        }
        response_data.update(CustomUserDetailsSerializer(user).data)
        return Response(response_data, status=status.HTTP_200_OK)
    
@extend_schema(methods=['GET'], exclude=True)
class LogoutAPIView(APIView):
    permission_classes = (AllowAny,)
    throttle_scope = 'dj_rest_auth'

    def get(self, request, *args, **kwargs):
        if getattr(settings, 'ACCOUNT_LOGOUT_ON_GET', False):
            response = self.logout(request)
        else:
            response = self.http_method_not_allowed(request, *args, **kwargs)

        return self.finalize_response(request, response, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.logout(request)

    def logout(self, request):
        try:
            request.user.auth_token.delete()
        except (AttributeError, ObjectDoesNotExist):
            pass

        if getattr(settings, 'REST_SESSION_LOGIN', True):
            django_logout(request)

        response = Response(
            {'detail': ('Successfully logged out.')},
            status=status.HTTP_200_OK,
        )

        if getattr(settings, 'REST_USE_JWT', False):
            from rest_framework_simplejwt.exceptions import TokenError
            from rest_framework_simplejwt.tokens import RefreshToken

            from .jwt_auth import unset_jwt_cookies
            cookie_name = getattr(settings, 'JWT_AUTH_COOKIE', None)

            unset_jwt_cookies(response)

            if 'rest_framework_simplejwt.token_blacklist' in settings.INSTALLED_APPS:
                try:
                    token = RefreshToken(request.data['refresh'])
                    token.blacklist()
                except KeyError:
                    response.data = {'detail': _(
                        'Refresh token was not included in request data.')}
                    response.status_code = status.HTTP_401_UNAUTHORIZED
                except (TokenError, AttributeError, TypeError) as error:
                    if hasattr(error, 'args'):
                        if 'Token is blacklisted' in error.args or 'Token is invalid or expired' in error.args:
                            response.data = {'detail': _(error.args[0])}
                            response.status_code = status.HTTP_401_UNAUTHORIZED
                        else:
                            response.data = {'detail': _(
                                'An error has occurred.')}
                            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                    else:
                        response.data = {'detail': _('An error has occurred.')}
                        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            elif not cookie_name:
                message = _(
                    'Neither cookies or blacklist are enabled, so the token '
                    'has not been deleted server side. Please make sure the token is deleted client side.',
                )
                response.data = {'detail': message}
                response.status_code = status.HTTP_200_OK
        return response

class SendOrResendSMSAPIView(GenericAPIView):
    serializer_class = PhoneNumberSerializer
    
    """
    API endpoint to send OTP to the user's phone number.
    """
    def post(self, request):
        phone_number = request.data.get("phone_number", None)
        environment = os.getenv('DJANGO_ENV', 'development')

        if phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)

                if environment in ['production', 'staging']:
                    send_otp(phone_number)  # Send OTP only in production or staging
                    return Response({"message": "OTP sent for login.", "is_new_user": False}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "OTP sending is disabled in this environment."}, status=status.HTTP_200_OK)

            except CustomUser.DoesNotExist:
                user = CustomUser(
                    phone_number=phone_number, 
                    role='patient', 
                    username=phone_number, 
                    is_first_login=True, 
                    password=CustomUser.objects.make_random_password()
                )
                user.save()
                group = Group.objects.get(name=user.role)
                user.groups.add(group)
                if not Profile.objects.filter(user=user).exists():
                    Profile.objects.create(user=user)

                if environment in ['production', 'staging']:
                    send_otp(phone_number)  # Send OTP only in production or staging
                    return Response({"message": "OTP sent for registration.", "is_new_user": True}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "OTP sending is disabled in this environment."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Phone number is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        
class ProfileAPIView(APIView):

    """
    API for retrieving and updating user profiles.
    """
    permission_classes = [PermissionsManager]
    serializer_class = ProfileSerializer
    codename = 'profile'

    def get(self, request):
        """
        Retrieve the profile of the logged-in user.
        """
        try:
            profile = request.user
            serializer = ProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        """
        Update the profile of the logged-in user.
        """
        try:
            profile = request.user
            serializer = ProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
class UserListCreateView(generics.ListCreateAPIView):
    """Superadmins and Admins can list users"""
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsSuperAdmin | IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomUserFilter
    
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Superadmins and Admins can manage users"""
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsSuperAdmin | IsAdmin]
    
class AdminCreateView(generics.CreateAPIView):
    """Only Superadmins can create Admin users"""
    queryset = CustomUser.objects.filter(role='admin')
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        serializer.save(role='admin')

class DoctorListCreateView(generics.ListCreateAPIView):
    """Only Admins can create and list Doctors"""
    queryset = CustomUser.objects.filter(role='doctor')
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        serializer.save(role='doctor')

class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Only Admins can manage Doctors"""
    queryset = CustomUser.objects.filter(role='doctor')
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsAdmin]
 
    
class DoctorRegistrationAPIView(APIView):
    serializer_class = DoctorRegistrationSerializer
    def post(self, request):
        serializer = DoctorRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Use the serializer to represent the user data
            user_data = DoctorRegistrationSerializer(user).data
            return Response({
                "message": "Doctor registered successfully.",
                "user_details": user_data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        
class DietPlanViewSet(viewsets.ModelViewSet):
    queryset = DietPlan.objects.all()
    serializer_class = DietPlanSerializer
    permission_classes = [PermissionsManager]
    codename = 'dietplan'
    filterset_class = DietPlanFilter

    def perform_create(self, serializer):
        patient_id = self.request.data.get('patient_id')
        try:
            patient = Profile.objects.get(id=patient_id)
        except Profile.DoesNotExist:
            raise serializers.ValidationError("Patient does not exist.")
        # Validate the date from the request
        diet_date_str = self.request.data.get('date')
        if not diet_date_str:
            raise serializers.ValidationError({"date": "This field is required."})

        try:
            diet_date = date.fromisoformat(diet_date_str)
        except ValueError:
            raise serializers.ValidationError({"date": "Invalid date format. Use YYYY-MM-DD."})

        # Check for future dates
        if diet_date > date.today():
            raise serializers.ValidationError({"date": "You cannot add a diet plan for a future date."})

        # Check for duplicate diet plans for the same date
        if DietPlan.objects.filter(patient=patient, date=diet_date).exists():
            raise serializers.ValidationError({"date": f"A diet plan already exists for {diet_date_str}."})

        # Enforce the 3-day rule
        last_diet_plan = DietPlan.objects.filter(patient=patient).order_by('-date').first()
        if last_diet_plan and (diet_date - last_diet_plan.date).days < 3:
            raise serializers.ValidationError(
                {"date": f"You can only add a diet plan every 3 days. Last plan was on {last_diet_plan.date}."}
            )
        serializer.save(patient=patient)
    
    def retrieve(self, request, patient_id, selected_date):
        try:
            # Convert selected_date to a date object
            selected_date = date.fromisoformat(selected_date)
            # Retrieve the diet plan for the specific date
            diet_plan = DietPlan.objects.filter(patient_id=patient_id, date=selected_date)

            if not diet_plan.exists():
                return Response({"error": "Diet plan not found for the selected date."}, status=status.HTTP_404_NOT_FOUND)

            serializer = DietPlanSerializer(diet_plan, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'doctor'):
            return DietPlan.objects.filter(patient__doctor=user.doctor)
        return DietPlan.objects.none()


class QuestionListCreateView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    pagination_class = Pagination
    permission_classes = [PermissionsManager]
    codename = 'question'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuestionCreateSerializer
        return QuestionSerializer

    def perform_create(self, serializer):
        serializer.save()
class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionCreateSerializer
    lookup_field = 'id'
    permission_classes = [PermissionsManager]
    codename = 'question'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return QuestionCreateSerializer
        return QuestionSerializer

    def perform_update(self, serializer):
        serializer.save()
    
class ExerciseListCreateView(generics.ListCreateAPIView):
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSerializer
    permission_classes = [PermissionsManager]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExerciseFilter
    codename = 'exercise'

class ExerciseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSerializer
    permission_classes = [PermissionsManager]
    codename = 'exercise'

    

class QuestionAnswerListCreateView(APIView):
    serializer_class = QuestionAnswerSerializer
    permission_classes = [PermissionsManager]
    codename = 'patientresponse'
    
    def get(self, request):
        """
        Get all answers by the logged-in user.
        """
        answers = PatientResponse.objects.filter(user=request.user)
        serializer = QuestionAnswerSerializer(answers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Submit answers for specific questions.
        """
        data = request.data
        data["user"] = request.user.id  # Attach the logged-in user

        serializer = QuestionAnswerSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardView(APIView):
    permission_classes = [PermissionsManager]  # Ensure only authenticated users can access

    def get(self, request):
        """
        API Endpoint to fetch dashboard details for Doctor, Patient, and Admin.
        Returns relevant analytics based on user role.
        """
        user = request.user
        role = getattr(user, "role", None)  # Ensure role exists

        if not role:
            return Response({"error": "User role not found"}, status=400)

        response_data = {"role": role}

        if role == "doctor":
            total_patients = CustomUser.objects.filter(role="patient", created_diets__doctor=user).distinct().count()
            total_diet_plans = DietPlan.objects.filter(doctor=user).count()
            active_patients = CustomUser.objects.filter(
                role="patient", assigned_diets__doctor=user, healthstatus__status="Improving"
            ).distinct().count()

            patient_engagement_rate = (
                round((active_patients / total_patients) * 100, 2) if total_patients else 0
            )

            total_diet_plans_count = DietPlan.objects.filter(doctor=user).count()
            diet_effectiveness = (
                round(
                    HealthStatus.objects.filter(user__role="patient", status="Improving").count() /
                    total_diet_plans_count * 100, 2
                ) if total_diet_plans_count else 0
            )

            total_exercises = Exercise.objects.filter(patient__in=CustomUser.objects.filter(role="patient")).count()
            completed_exercises = Exercise.objects.filter(patient__in=CustomUser.objects.filter(role="patient"), completed=True).count()

            exercise_compliance = (
                round((completed_exercises / total_exercises) * 100, 2) if total_exercises else 0
            )

            response_data.update({
                "total_patients": total_patients,
                "total_diet_plans": total_diet_plans,
                "patient_engagement_rate": patient_engagement_rate,
                "diet_effectiveness": diet_effectiveness,
                "exercise_compliance_rate": exercise_compliance,
            })

        elif role == "patient":
            total_diets = DietPlan.objects.filter(patient=user).count()
            total_exercises = Exercise.objects.filter(patient=user).count()
            latest_health_status = HealthStatus.objects.filter(user=user).order_by("-created_at").first()
            avg_calories_burned = Exercise.objects.filter(patient=user).aggregate(Avg("calories_burned"))["calories_burned__avg"] or 0

            completed_exercises = Exercise.objects.filter(patient=user, completed=True).count()
            goal_achievement_rate = (
                round((completed_exercises / total_exercises) * 100, 2) if total_exercises else 0
            )

            response_data.update({
                "total_diets": total_diets,
                "total_exercises": total_exercises,
                "latest_health_status": latest_health_status.status if latest_health_status else "No status available",
                "average_calories_burned_per_week": avg_calories_burned,
                "goal_achievement_rate": goal_achievement_rate,
            })

        elif role == "admin":
            total_patients = CustomUser.objects.filter(role="patient").count()
            total_doctors = CustomUser.objects.filter(role="doctor").count()
            total_diet_plans = DietPlan.objects.count()
            total_exercises = Exercise.objects.count()
            monthly_growth = CustomUser.objects.filter(date_joined__month=2).count()

            top_doctor = (
                CustomUser.objects.filter(role="doctor")
                .annotate(patient_count=Count("created_diets"))
                .order_by("-patient_count")
                .first()
            )

            most_popular_diet = (
                DietPlan.objects.annotate(patient_count=Count("patient"))
                .order_by("-patient_count")
                .first()
            )

            response_data.update({
                "total_patients": total_patients,
                "total_doctors": total_doctors,
                "total_diet_plans": total_diet_plans,
                "total_exercises": total_exercises,
                "monthly_growth": monthly_growth,
                "top_doctor": top_doctor.username if top_doctor else None,
                "most_popular_diet": most_popular_diet.title if most_popular_diet else None,
            })

        else:
            return Response({"error": "Invalid role"}, status=403)

        return Response(response_data)
