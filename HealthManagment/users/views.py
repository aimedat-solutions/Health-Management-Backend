from collections import defaultdict
from rest_framework import generics, permissions
from .models import ( Profile, Question,DietPlan,Exercise, CustomUser,UserLegalConsent,PatientResponse, 
                    Exercise,ExerciseDate,HealthStatus,AppContent,HealthEducation,HelpContent,ExerciseStatus,DietPlanStatus,DietPlanDate
                    )
from .serializers import ( ExerciseSerializer, ProfileSerializer, HealthEducationSerializer, DoctorRegistrationSerializer, QuestionSerializer,
                        QuestionAnswerSerializer,UserRegistrationSerializer,UserLoginSerializer,CustomUserDetailsSerializer,QuestionCreateSerializer,
                        PhoneNumberSerializer,HelpContentSerializer,LegalConsentSerializer,DoctorPatientResponseSerializer,DoctorQuestionResponseSerializer
                        )
from doctor.serializers import DietPlanReadSerializer, DietPlanCreateSerializer
from django.db.models import Count, Avg, F, Max
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
from users.permissions import PermissionsManager,IsSuperAdmin, IsAdmin, IsAdminOrSuperAdmin
from rest_framework import viewsets
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotAuthenticated
from .utils import send_otp, verify_otp
from .pagination import Pagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from .filters import (
    CustomUserFilter, DietPlanFilter, ExerciseFilter,
    QuestionFilter, HealthEducationFilter,
)
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
    permission_classes = [permissions.AllowAny]
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
    permission_classes = [permissions.AllowAny]
    serializer_class = PhoneNumberSerializer
    
    """
    API endpoint to send OTP to the user's phone number.
    """
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        environment = os.getenv('DJANGO_ENV', 'development')

        try:
            user = CustomUser.objects.get(phone_number=phone_number)

            if environment in ['production', 'staging']:
                send_otp(str(phone_number))  # Send OTP only in production or staging
                return Response({"message": "OTP sent for login.", "is_new_user": user.is_first_login}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "OTP sending is disabled in this environment."}, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            random_password = get_random_string(length=8)  # You can choose the length
            hashed_password = make_password(random_password)
            user = CustomUser(
                phone_number=phone_number, 
                role='patient', 
                username=str(phone_number), 
                is_first_login=True, 
            )
            user.set_password(hashed_password)
            user.save()
            group = Group.objects.get(name=user.role)
            user.groups.add(group)
            if not Profile.objects.filter(user=user).exists():
                Profile.objects.create(user=user)

            if environment in ['production', 'staging']:
                send_otp(str(phone_number))  # Send OTP only in production or staging
                return Response({"message": "OTP sent for registration.", "is_new_user": user.is_first_login}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "OTP sending is disabled in this environment."}, status=status.HTTP_200_OK)
        
        
class ProfileAPIView(APIView):

    """
    API for retrieving and updating user profiles.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer
    
    def get_object(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile
    
    def get(self, request):
        profile = self.get_object()
        serializer = self.serializer_class(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        """
        Update the profile and email of the logged-in user.
        """
        profile = self.get_object()
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            email = request.data.get("email")
            if email and request.user.email != email:
                request.user.email = email
                request.user.save(update_fields=["email"])
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
    """Admins and Superadmins can manage users"""
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    
class AdminCreateView(generics.CreateAPIView):
    """Admins and Superadmins can create Admin users"""
    queryset = CustomUser.objects.filter(role='admin')
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def perform_create(self, serializer):
        user = serializer.save(role="admin") 
        default_password = "Admin"         
        patient_group, created = Group.objects.get_or_create(name="admin")
        user.groups.add(patient_group)  
        user.set_password(default_password)
        user.save()

class DoctorListCreateView(generics.ListCreateAPIView):
    """Admins can create and list Doctors, Superadmins have full access"""
    queryset = CustomUser.objects.filter(role='doctor')
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = CustomUserFilter
    search_fields = ["profile__first_name", "profile__last_name", "email", "phone_number"]

    def perform_create(self, serializer):
        user = serializer.save(role='doctor')
        doctor_group, created = Group.objects.get_or_create(name="doctor")
        user.groups.add(doctor_group)
        if not Profile.objects.filter(user=user).exists():
            Profile.objects.create(user=user)

class DoctorDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admins can view/update Doctors, Superadmins have full access including delete"""
    queryset = CustomUser.objects.filter(role='doctor')
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsAdminOrSuperAdmin]
 
    
class DoctorRegistrationAPIView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = DoctorRegistrationSerializer
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
    filter_backends = [DjangoFilterBackend]
    filterset_class = QuestionFilter

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
        user = request.user
        if user.role == "patient":
            answers = PatientResponse.objects.filter(user=user)
            serializer = QuestionAnswerSerializer(answers, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif user.role == "doctor":
            latest_per_question = PatientResponse.objects.values(
                'user_id', 'question_id'
            ).annotate(latest_id=Max('id')).values('latest_id')

            answers = PatientResponse.objects.filter(
                id__in=latest_per_question
            ).select_related(
                'question', 'user', 'selected_option', 'question__parent'
            ).order_by('user_id', 'question__parent_id', 'question_id', 'created_at')

            patient_id_filter = request.query_params.get("patient_id")
            if patient_id_filter:
                answers = answers.filter(user_id=patient_id_filter)

            date_filter = request.query_params.get("date")
            if date_filter:
                answers = answers.filter(created_at__date=date_filter)

            grouped_by_patient = defaultdict(list)
            for answer in answers:
                grouped_by_patient[answer.user.id].append(answer)

            result = []
            for patient_id, responses in grouped_by_patient.items():
                patient = responses[0].user
                profile = getattr(patient, "profile", None)
                first_name = getattr(profile, "first_name", "") or ""
                last_name = getattr(profile, "last_name", "") or ""

                top_level = [r for r in responses if r.question.parent_id is None]
                sub_responses = defaultdict(list)
                for r in responses:
                    if r.question.parent_id is not None:
                        sub_responses[r.question.parent_id].append(r)

                serialized_responses = []
                for response in top_level:
                    response_context = {'request': request, 'sub_responses': sub_responses}
                    serialized_responses.append(
                        DoctorQuestionResponseSerializer(response, context=response_context).data
                    )

                result.append({
                    "patient_id": patient_id,
                    "patient_name": f"{first_name} {last_name}".strip() or patient.username,
                    "phone_number": str(patient.phone_number) if patient.phone_number else "",
                    "responses": serialized_responses,
                })

            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Unauthorized user."}, status=status.HTTP_403_FORBIDDEN)

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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = getattr(user, "role", None)

        if not role:
            return Response({"error": "User role not found"}, status=400)

        response_data = {"role": role, "username": user.profile.first_name if hasattr(user, "profile") else user.username}

        if role == "doctor":

            today = timezone.now().date()

            patients = CustomUser.objects.filter(
                role="patient",
                assigned_diets__doctor=user
            ).distinct()

            total_mothers = patients.count()

            high_risk = HealthStatus.objects.filter(
                patient__in=patients,
                health_status__in=["Poor", "Critical"]
            ).values("patient").distinct().count()

            due_soon = Profile.objects.filter(
                user__in=patients,
                lmp_date__isnull=False,
                lmp_date__lte=date.today() - timedelta(days=240)
            ).count()

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

            diet_qs = DietPlanStatus.objects.filter(
                patient__in=patients,
                date=today,
                status="skipped"
            )

            diet_missed_patients = diet_qs.values("patient").distinct().count()
            diet_missed_total = diet_qs.count()

            exercise_qs = ExerciseStatus.objects.filter(
                user__in=patients,
                status="skipped",
                updated_at__date=today
            )

            exercise_missed_patients = exercise_qs.values("user").distinct().count()
            exercise_missed_total = exercise_qs.count()

            total_diet_plans = DietPlan.objects.filter(doctor=user).count()
            
            diet_completed_today = DietPlanStatus.objects.filter(
                patient__in=patients,
                date=today,
                status="completed"
            ).count()

            alerts = []

            critical_cases = HealthStatus.objects.filter(
                patient__in=patients,
                health_status="Critical"
            ).select_related("patient")

            for c in critical_cases[:10]:
                alerts.append({
                    "name": c.patient.get_full_name(),
                    "message": "Critical health condition",
                    "type": "critical"
                })

            profiles = Profile.objects.filter(user__in=patients).select_related("user")
            health_map = {
                h.patient_id: h
                for h in HealthStatus.objects.filter(patient__in=patients)
            }

            recent_mothers = []

            for p in profiles[:10]:
                user_obj = p.user
                health = health_map.get(user_obj.id)

                recent_mothers.append({
                    "id": user_obj.id,
                    "name": f"{p.first_name or ''} {p.last_name or ''}".strip(),
                    "phone_number": str(user_obj.phone_number) if user_obj.phone_number else "",
                    "gestational_age": p.gestational_age or "NA",
                    "bp": getattr(health, "blood_pressure", "NA"),
                    "sugar": getattr(health, "blood_sugar", "NA"),
                    "edd": p.edd or "NA",
                    "bmi": p.bmi or "NA",
                    "health_status": getattr(health, "health_status", "Stable")
                })

            response_data.update({
                "active_mothers": total_mothers,
                "high_risk_cases": high_risk,
                "due_in_30_days": due_soon,
                "total_diet_plans": total_diet_plans,

                "trimester_overview": trimester,

                "diet_missed_today": diet_missed_patients,
                "diet_missed_total": diet_missed_total,
                "diet_completed_today": diet_completed_today,

                "exercise_missed_today": exercise_missed_patients,
                "exercise_missed_total": exercise_missed_total,

                "alerts": alerts,

                "recent_mothers": recent_mothers,
            })

        elif role == "patient":

            today = timezone.now().date()

            total_diets = DietPlan.objects.filter(patient=user).count()
            total_exercises = ExerciseDate.objects.filter(patient=user).count()

            latest_health_status = HealthStatus.objects.filter(
                patient=user
            ).order_by("-created_at").first()

            avg_calories_burned = (
                ExerciseStatus.objects
                .filter(user=user, status="completed")
                .aggregate(avg=Avg("calories_burned"))
                .get("avg") or 0
            )

            completed_exercises = ExerciseStatus.objects.filter(user=user).count()

            goal_achievement_rate = (
                round((completed_exercises / total_exercises) * 100, 2)
                if total_exercises else 0
            )

            profile = getattr(user, "profile", None)
            pregnancy_details = {}
            if profile:
                pregnancy_details = {
                    "gestational_age": profile.gestational_age,
                    "edd": profile.edd,
                    "pregnancy_month": profile.pregnancy_month,
                    "bmi": profile.bmi,
                    "bmi_category": profile.bmi_category,
                }

            today_diet_status = DietPlanStatus.objects.filter(
                patient=user,
                date=today
            ).values("status").annotate(count=Count("id"))
            
            today_meals = {item["status"]: item["count"] for item in today_diet_status}

            today_exercise_status = ExerciseStatus.objects.filter(
                user=user,
                updated_at__date=today
            ).values("status").annotate(count=Count("id"))
            
            today_exercises = {item["status"]: item["count"] for item in today_exercise_status}

            today_steps = DailyStepCount.objects.filter(
                patient=user,
                date=today
            ).first()

            upcoming_diet_plans = DietPlanDate.objects.filter(
                diet_plan__patient=user,
                date__gte=today
            ).order_by("date")[:5]

            response_data.update({
                "total_diets": total_diets,
                "total_exercises": total_exercises,
                "latest_health_status": latest_health_status.health_status if latest_health_status else "No status",
                "average_calories_burned_per_week": avg_calories_burned,
                "goal_achievement_rate": goal_achievement_rate,
                "pregnancy_details": pregnancy_details,
                "today_meals": today_meals,
                "today_exercises": today_exercises,
                "today_steps": {
                    "steps": today_steps.steps if today_steps else 0,
                    "goal": today_steps.goal_steps if today_steps else 0,
                    "status": today_steps.status if today_steps else "low",
                } if today_steps else {"steps": 0, "goal": 0, "status": "low"},
                "upcoming_diet_dates": [d.date for d in upcoming_diet_plans],
            })

        elif role in ["admin", "superadmin"]:

            today = timezone.now().date()
            this_month_start = today.replace(day=1)

            total_patients = CustomUser.objects.filter(role="patient").count()
            total_doctors = CustomUser.objects.filter(role="doctor").count()
            total_diet_plans = DietPlan.objects.count()
            total_exercises = Exercise.objects.count()
            total_admins = CustomUser.objects.filter(role="admin").count()

            new_patients_this_month = CustomUser.objects.filter(
                role="patient",
                date_joined__gte=this_month_start
            ).count()
            new_doctors_this_month = CustomUser.objects.filter(
                role="doctor",
                date_joined__gte=this_month_start
            ).count()

            diet_missed_today = DietPlanStatus.objects.filter(
                date=today,
                status="skipped"
            ).count()
            diet_completed_today = DietPlanStatus.objects.filter(
                date=today,
                status="completed"
            ).count()
            
            exercise_missed_today = ExerciseStatus.objects.filter(
                status="skipped",
                updated_at__date=today
            ).count()
            exercise_completed_today = ExerciseStatus.objects.filter(
                status="completed",
                updated_at__date=today
            ).count()

            critical_cases = HealthStatus.objects.filter(
                health_status="Critical"
            ).select_related("patient").count()

            diet_completion_rate = 0
            total_diet_statuses_today = DietPlanStatus.objects.filter(date=today).count()
            if total_diet_statuses_today > 0:
                diet_completion_rate = round(
                    (diet_completed_today / total_diet_statuses_today) * 100, 2
                )

            doctor_patient_counts = (
                CustomUser.objects.filter(role="doctor")
                .annotate(patient_count=Count("created_diets__patient", distinct=True))
                .values("id", "username")
                .annotate(
                    first_name=F("profile__first_name"),
                    last_name=F("profile__last_name")
                )
                .order_by("-patient_count")[:10]
            )

            recent_patients = (
                CustomUser.objects.filter(role="patient")
                .select_related("profile")
                .order_by("-date_joined")[:5]
                .values(
                    "id", "date_joined",
                    "profile__first_name", "profile__last_name"
                )
            )

            response_data.update({
                "total_patients": total_patients,
                "total_doctors": total_doctors,
                "total_diet_plans": total_diet_plans,
                "total_exercises": total_exercises,
                "total_admins": total_admins,
                "new_patients_this_month": new_patients_this_month,
                "new_doctors_this_month": new_doctors_this_month,
                "diet_missed_today": diet_missed_today,
                "diet_completed_today": diet_completed_today,
                "exercise_missed_today": exercise_missed_today,
                "exercise_completed_today": exercise_completed_today,
                "critical_cases": critical_cases,
                "diet_completion_rate": diet_completion_rate,
                "top_doctors": list(doctor_patient_counts),
                "recent_patients": list(recent_patients),
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
    permission_classes = [permissions.AllowAny]
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

    
class HealthEducationViewSet(viewsets.ModelViewSet):
    serializer_class = HealthEducationSerializer
    queryset = HealthEducation.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = HealthEducationFilter

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrSuperAdmin()]
        return []

    def get_queryset(self):
        qs = HealthEducation.objects.all().order_by("order")
        if self.action == 'list':
            user = self.request.user
            is_admin = bool(
                user.is_authenticated
                and IsAdminOrSuperAdmin().has_permission(self.request, self)
            )
            if not is_admin:
                qs = qs.filter(is_active=True)
        return qs
    
    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
class HelpContentViewSet(viewsets.ModelViewSet):
    serializer_class = HelpContentSerializer
    queryset = HelpContent.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminOrSuperAdmin()]
        return []

    def get_queryset(self):
        qs = HelpContent.objects.all().order_by("step_order")
        if self.action == 'list':
            user = self.request.user
            is_admin = bool(
                user.is_authenticated
                and IsAdminOrSuperAdmin().has_permission(self.request, self)
            )
            if not is_admin:
                qs = qs.filter(is_active=True)
            screen = self.request.query_params.get("screen")
            content_type = self.request.query_params.get("type")
            if screen:
                qs = qs.filter(screen_name=screen)
            if content_type:
                qs = qs.filter(content_type=content_type)
        return qs

class AdminDietPlanListView(generics.ListAPIView):
    """Admin/Superadmin can view all diet plans with doctor and patient info"""
    serializer_class = DietPlanReadSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DietPlanFilter

    def get_queryset(self):
        qs = DietPlan.objects.prefetch_related(
            "meals__meal_portions",
            "diet_dates",
            "patient",
            "doctor"
        ).order_by("-id")
        
        doctor_id = self.request.query_params.get("doctor_id")
        patient_id = self.request.query_params.get("patient_id")
        date = self.request.query_params.get("date")
        
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if date:
            qs = qs.filter(diet_dates__date=date)
        
        return qs.distinct()

class AdminDoctorDietPlansView(generics.ListAPIView):
    """Admin/Superadmin can view diet plans assigned by a specific doctor"""
    serializer_class = DietPlanReadSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DietPlanFilter

    def get_queryset(self):
        doctor_id = self.kwargs.get('doctor_id')
        qs = DietPlan.objects.filter(doctor_id=doctor_id).prefetch_related(
            "meals__meal_portions",
            "diet_dates",
            "patient",
            "doctor"
        ).order_by("-id")
        
        patient_id = self.request.query_params.get("patient_id")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        
        return qs.distinct()

class AdminDoctorPatientsView(generics.ListAPIView):
    """Admin/Superadmin can view all patients assigned to a specific doctor"""
    serializer_class = CustomUserDetailsSerializer
    permission_classes = [IsAdminOrSuperAdmin]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = CustomUserFilter
    search_fields = ["profile__first_name", "profile__last_name", "email", "phone_number"]

    def get_queryset(self):
        doctor_id = self.kwargs.get('doctor_id')
        return CustomUser.objects.filter(
            role='patient',
            assigned_diets__doctor_id=doctor_id
        ).distinct().order_by("-id")
