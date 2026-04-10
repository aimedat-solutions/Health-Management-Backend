from rest_framework import generics, permissions
from .models import ( Profile, Question,DietPlan,Exercise, CustomUser,UserLegalConsent,PatientResponse, 
                    Exercise,ExerciseDate,HealthStatus,AppContent,HealthEducation,HelpContent,ExerciseStatus,DietPlanStatus
                    )
from .serializers import ( ExerciseSerializer, ProfileSerializer, HealthEducationSerializer, DoctorRegistrationSerializer, QuestionSerializer,
                        QuestionAnswerSerializer,UserRegistrationSerializer,UserLoginSerializer,CustomUserDetailsSerializer,QuestionCreateSerializer,
                        PhoneNumberSerializer,HelpContentSerializer,LegalConsentSerializer
                        )
from django.db.models import Count,Avg
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
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotAuthenticated
from .utils import send_otp, verify_otp
from .pagination import Pagination
from django_filters.rest_framework import DjangoFilterBackend
from .filters import CustomUserFilter, DietPlanFilter,ExerciseFilter
import os
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from dotenv import load_dotenv
from django.utils import timezone
from datetime import timedelta

from .models import DailyStepCount
from .serializers import StepSyncSerializer, DailyStepSerializer,AppContentSerializer
from .services import (
    get_trimester,
    has_diabetes,
    calculate_step_goal,
    classify_steps,
    exercise_completed_today,
    daily_activity_message
)
load_dotenv()  # reads .env file

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
        if user.initial_question_completed and user.is_first_login:
            user.is_first_login = False
            user.save(update_fields=["is_first_login"])
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        response_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'is_new_user': user.is_first_login,   
            'initial_question_completed': user.initial_question_completed,
            'ask_diet_questions': user.ask_diet_question,
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
                    return Response({"message": "OTP sent for login.", "is_new_user": user.is_first_login}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "OTP sending is disabled in this environment."}, status=status.HTTP_200_OK)

            except CustomUser.DoesNotExist:
                random_password = get_random_string(length=8)  # You can choose the length
                hashed_password = make_password(random_password)
                user = CustomUser(
                    phone_number=phone_number, 
                    role='patient', 
                    username=phone_number, 
                    is_first_login=True, 
                )
                user.set_password(hashed_password)
                user.save()
                group = Group.objects.get(name=user.role)
                user.groups.add(group)
                if not Profile.objects.filter(user=user).exists():
                    Profile.objects.create(user=user)

                if environment in ['production', 'staging']:
                    send_otp(phone_number)  # Send OTP only in production or staging
                    return Response({"message": "OTP sent for registration.", "is_new_user": user.is_first_login}, status=status.HTTP_200_OK)
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
    
    def get_object(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile
    
    def get(self, request):
        profile = self.get_object()
        serializer = self.serializer_class(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        """
        Update the profile of the logged-in user.
        """
        profile = self.get_object()
        serializer = ProfileSerializer(profile, data=request.data, partial=True)  # allows partial updates
        if serializer.is_valid():
            serializer.save()
            serializer = self.serializer_class(profile, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserListCreateView(generics.ListCreateAPIView):
    """Superadmins and Admins can list users"""
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [PermissionsManager]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomUserFilter
    codename = 'user'
    
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Superadmins and Admins can manage users"""
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsSuperAdmin]
    
class AdminCreateView(generics.CreateAPIView):
    """Only Superadmins can create Admin users"""
    queryset = CustomUser.objects.filter(role='admin')
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        user = serializer.save(role="admin") 
        default_password = "Admin"         
        patient_group, created = Group.objects.get_or_create(name="admin")
        user.groups.add(patient_group)  
        user.set_password(default_password)
        user.save()

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
    # permission_classes = [PermissionsManager]
    serializer_class = DoctorRegistrationSerializer
    # codename = 'user'
    def post(self, request):
        print(request.data)
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
    serch_field = ['title']
    codename = 'exercise'
    
    # def get_queryset(self):
    #     return ExerciseDate.objects.filter(
    #         exercise__user=self.request.user
    #     ).select_related("exercise").order_by("date")
    
    # def get_serializer_context(self):
    #     context = super().get_serializer_context()
    #     date_str = self.request.query_params.get("date")
    #     if date_str:
    #         from datetime import datetime
    #         try:
    #             context["target_date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
    #         except ValueError:
    #             pass
    #     return context

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
        Get all answers:
        - If the user is a patient, return their own answers.
        - If the user is a doctor, return answers from patients assigned to them.
        """
        user = request.user
        if user.role == "patient":
            answers = PatientResponse.objects.filter(user=user)
        elif user.role == "doctor":
            # Assuming reverse FK from User (patients) to doctor is `assigned_doctor`
            answers = PatientResponse.objects.filter(user=user)
        else:
            return Response({"detail": "Unauthorized user."}, status=status.HTTP_403_FORBIDDEN)
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

            # ===== MY PATIENTS ONLY =====
            patients = CustomUser.objects.filter(
                role="patient",
                assigned_diets__doctor=user
            ).distinct()

            total_mothers = patients.count()

            # ===== HIGH RISK (from HealthStatus) =====
            high_risk = HealthStatus.objects.filter(
                patient__in=patients,
                health_status__in=["Poor", "Critical"]
            ).count()

            # ===== DUE IN 30 DAYS =====
            today = date.today()
            due_soon = Profile.objects.filter(
                user__in=patients,
                lmp_date__isnull=False
            ).filter(
                lmp_date__lte=today - timedelta(days=240),  # approx 8 months
            ).count()

            # ===== TRIMESTER DISTRIBUTION =====
            trimester = {"t1": 0, "t2": 0, "t3": 0}

            for p in Profile.objects.filter(user__in=patients):
                month = p.pregnancy_month
                if month:
                    if month <= 3:
                        trimester["t1"] += 1
                    elif month <= 6:
                        trimester["t2"] += 1
                    else:
                        trimester["t3"] += 1

            # ===== TODAY MISSED DIET =====
            today = timezone.now().date()

            diet_missed = DietPlanStatus.objects.filter(
                patient__in=patients,
                date=today,
                status="skipped"
            ).count()

            # ===== EXERCISE MISSED =====
            exercise_missed = ExerciseStatus.objects.filter(
                user__in=patients,
                status="skipped",
                updated_at__date=today
            ).count()

            # ===== RECENT MOTHERS LIST =====
            recent_mothers = []

            for p in patients[:10]:

                profile = getattr(p, "profile", None)
                health = HealthStatus.objects.filter(patient=p).last()

                recent_mothers.append({
                    "name": p.get_full_name() or p.profile.first_name,
                    "gestational_age": profile.gestational_age if profile else "NA",
                    "bp": health.blood_pressure if health else "NA",
                    "sugar": health.blood_sugar if health else "NA",
                    "bmi": health.bmi if health else "NA",
                    "risk": health.health_status if health else "Normal"
                })

            # ===== RESPONSE =====

            response_data.update({
                "active_mothers": total_mothers,
                "high_risk_cases": high_risk,
                "due_in_30_days": due_soon,

                "trimester_overview": trimester,

                "diet_missed_today": diet_missed,
                "exercise_missed_today": exercise_missed,

                "recent_mothers": recent_mothers,
            })
        elif role == "patient":
            total_diets = DietPlan.objects.filter(patient=user).count()
            total_exercises = ExerciseDate.objects.filter(patient=user).count()
            latest_health_status = HealthStatus.objects.filter(patient=user).order_by("-created_at").first()
            avg_calories_burned = (
                ExerciseStatus.objects
                .filter(user=user, status="completed")
                .aggregate(avg=Avg("calories_burned"))
                .get("avg") or 0
            )
            completed_exercises = ExerciseStatus.objects.filter(user=user).count()
            goal_achievement_rate = (
                round((completed_exercises / total_exercises) * 100, 2) if total_exercises else 0
            )

            response_data.update({
                "total_diets": total_diets,
                "total_exercises": total_exercises,
                "latest_health_status": latest_health_status.health_status if latest_health_status else "No status available",
                "average_calories_burned_per_week": avg_calories_burned,
                "goal_achievement_rate": goal_achievement_rate,
            })

        elif role == "admin":
            total_patients = CustomUser.objects.filter(role="patient").count()
            total_doctors = CustomUser.objects.filter(role="doctor").count()
            total_diet_plans = DietPlan.objects.count()
            total_exercises = Exercise.objects.count()
            monthly_growth = CustomUser.objects.filter(date_joined__month=2).count()

            top_doctors = (
                CustomUser.objects.filter(role="doctor")
                .annotate(
                    diet_count=Count("created_diets"),
                    exercise_count=Count("created_exercise_set")
                )
                .order_by("-diet_count", "-exercise_count")[:5]
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
                "top_doctors": [doctor.username for doctor in top_doctors],
                "most_popular_diet": most_popular_diet.title if most_popular_diet else None,
            })

        else:
            return Response({"error": "Invalid role"}, status=403)

        return Response(response_data)

class SyncStepsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StepSyncSerializer

    def post(self, request):
        serializer = StepSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        patient = request.user
        profile = patient.profile

        steps = serializer.validated_data["steps"]
        date = serializer.validated_data["date"]
        source = serializer.validated_data["source"]

        trimester = get_trimester(profile)
        diabetes = has_diabetes(patient)

        goal = calculate_step_goal(trimester, diabetes)
        status = classify_steps(steps, goal)

        obj, _ = DailyStepCount.objects.update_or_create(
            patient=patient,
            date=date,
            defaults={
                "steps": steps,
                "goal_steps": goal,
                "source": source,
                "status": status,
            }
        )

        exercise_done = exercise_completed_today(patient)

        return Response({
            "date": date,
            "steps": steps,
            "goal": goal,
            "status": status,
            "message": daily_activity_message(status, exercise_done),
        })


class TodayStepsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DailyStepSerializer

    def get(self, request):
        today = timezone.now().date()
        try:
            obj = DailyStepCount.objects.get(
                patient=request.user,
                date=today
            )
            data = DailyStepSerializer(obj).data
            data["message"] = daily_activity_message(
                obj.status,
                exercise_completed_today(request.user)
            )
            return Response(data)
        except DailyStepCount.DoesNotExist:
            return Response({
                "date": today,
                "steps": 0,
                "goal_steps": 0,
                "status": "low",
                "message": "No activity recorded yet today."
            })


class WeeklyStepsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = DailyStepCount.objects.filter(
            patient=request.user
        ).order_by("-date")[:7]

        return Response([
            {"date": s.date, "steps": s.steps}
            for s in reversed(qs)
        ])



class AppContentView(APIView):
    serializer_class = AppContentSerializer
    def get(self, request):
        content_type = request.GET.get("type")
        qs = AppContent.objects.filter(is_active=True)
        if content_type:
            qs = qs.filter(content_type=content_type)
        serializer = AppContentSerializer(qs, many=True)
        return Response(serializer.data)

class AcceptLegalView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LegalConsentSerializer

    def post(self, request):
        serializer = LegalConsentSerializer(
            data=request.data,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)

        UserLegalConsent.objects.create(
            user=request.user,
            **serializer.validated_data
        )

        return Response(
            {"message": "Legal consent accepted successfully"},
            status=status.HTTP_201_CREATED
        )

    
class HealthEducationView(APIView):
    serializer_class = HealthEducationSerializer

    def get(self, request):
        data = HealthEducation.objects.filter(is_active=True).order_by("order")
        serializer = HealthEducationSerializer(
            data,
            many=True,
            context={"request": request} 
        )
        return Response(serializer.data)
    
class HelpContentView(APIView):
    serializer_class = HelpContentSerializer
    def get(self, request):
        screen = request.query_params.get("screen")
        content_type = request.query_params.get("type")

        qs = HelpContent.objects.filter(is_active=True)
        if screen:
            qs = qs.filter(screen_name=screen)
        if content_type:
            qs = qs.filter(content_type=content_type)

        return Response(HelpContentSerializer(qs, many=True).data)
