from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models import CustomUser, DietPlan, MealPortion, Exercise, LabReport, PatientResponse, PatientDietQuestion, PatientExerciseLog, DietPlanDate,ExerciseDate, ExerciseStatus
from django.shortcuts import get_object_or_404
from users.nutrition_service import fetch_nutrition_data
from .serializers import PatientSerializer, DietPlanCreateSerializer, MealPortionSerializer,DietPlanReadSerializer,PatientDietQuestionSerializer,PatientExerciseLogSerializer,ExcerciseDateAssignSerializer,DoctorExerciseResponseSerializer
from users.serializers import ExerciseDateSerializer
from patient.serializers import LabReportSerializer, PatientResponseSerializer
from users.permissions import PermissionsManager,IsDoctorUser, IsSuperAdmin, IsAdmin, IsDoctorOrAdmin
from rest_framework import viewsets, filters, generics
from django_filters.rest_framework import DjangoFilterBackend
from users.filters import CustomUserFilter, MealPortionFilter, DietPlanFilter
from users.pagination import Pagination
from django.db.models.functions import ExtractMonth, ExtractYear, Now
from django.db.models import IntegerField, F, ExpressionWrapper, Prefetch, Q
from django.utils.timezone import now
from datetime import date
class PatientManagementViewSet(viewsets.ModelViewSet):
    """
    Allows doctors to view and edit patient details.
    """
    permission_classes = [PermissionsManager,IsDoctorUser,]
    serializer_class = PatientSerializer
    queryset = CustomUser.objects.filter(role='patient')
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomUserFilter
    search_fields = ['profile__first_name', 'profile__last_name', 'email', 'phone_number']
    ordering_fields = ['profile__first_name', 'profile__last_name', 'profile__health_status', 'age', 'birth_month', 'date_joined']
    ordering = ['profile__first_name', 'age', 'birth_month', ] 
    codename = 'patientmanagement'
    
    def get_queryset(self):
        today = date.today()
        return (
            CustomUser.objects.filter(role='patient')
            .annotate(
                # Age
                age=ExpressionWrapper(
                    ExtractYear(Now()) - ExtractYear(F('profile__date_of_birth')),
                    output_field=IntegerField()
                ),
                # Birth month
                birth_month=ExtractMonth(F('profile__date_of_birth')),

                # Pregnancy month (approx, based on 28-day cycle)
                pregnancy_month=ExpressionWrapper(
                    ((Now() - F('profile__lmp_date')) / 28) + 1,
                    output_field=IntegerField()
                ),

                # Gestational age in weeks (integer)
                gestational_weeks=ExpressionWrapper(
                    (Now() - F('profile__lmp_date')) / 7,
                    output_field=IntegerField()
                )
            )
        )
    def retrieve(self, request, pk=None):
        patient = get_object_or_404(CustomUser, id=pk, role='patient')
        
        assigned_exercises = ExerciseDate.objects.filter(patient=patient).prefetch_related(
            Prefetch('status_entries', queryset=ExerciseStatus.objects.filter(user=patient), to_attr='patient_status')
        )
        diet_plans = DietPlan.objects.filter(patient=patient)
        lab_reports = LabReport.objects.filter(patient=patient)
        questions = PatientResponse.objects.filter(user=patient)

        data = {
            "patient_details": PatientSerializer(patient).data,
            "assigned_exercises": ExerciseDateSerializer(assigned_exercises, many=True).data,
            "assigned_diet_plans": DietPlanReadSerializer(diet_plans, many=True, context={'request': request}).data,
            "lab_reports": LabReportSerializer(lab_reports, many=True).data,
            "questions": PatientResponseSerializer(questions, many=True).data
        }
        return Response(data, status=status.HTTP_200_OK)
    

class MealPortionViewSet(viewsets.ModelViewSet):
    queryset = MealPortion.objects.all()
    serializer_class = MealPortionSerializer
    permission_classes = [IsDoctorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = MealPortionFilter
    search_fields = ["name"]

    def _enrich_with_nutrition(self, instance):
        print(f"--- AI Nutrition: fetching data for '{instance.name}' ---")
        data = fetch_nutrition_data(instance.name)
        print(data)
        if data:
            for field, value in data.items():
                setattr(instance, field, value)
            instance.save(update_fields=list(data.keys()))
            print(f"--- AI Nutrition: saved data for '{instance.name}' (calories={data.get('calories')}) ---")
        else:
            print(f"--- AI Nutrition: no data found for '{instance.name}' ---")

    def perform_create(self, serializer):
        instance = serializer.save()
        self._enrich_with_nutrition(instance)

    def perform_update(self, serializer):
        name_changed = (
            self.get_object().name != serializer.validated_data.get("name")
        )
        instance = serializer.save()
        if name_changed:
            self._enrich_with_nutrition(instance)

class DietPlanViewSet(viewsets.ModelViewSet):
    """
    Allows doctors and admins to create and retrieve diet plans for patients.
    """
    queryset = DietPlan.objects.none()
    permission_classes = [PermissionsManager]
    serializer_class = DietPlanCreateSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = DietPlanFilter
    search_fields = ["patient__username", "diet_dates"]
    codename = "dietplan"

    def get_queryset(self):

        user = self.request.user

        qs = DietPlan.objects.prefetch_related(
            "meals__meal_portions",
            "diet_dates",
            "patient"
        )

        # ==========================
        # ADMIN ACCESS
        # ==========================
        if user.role in ["admin", "superadmin"]:
            pass

        # ==========================
        # DOCTOR ACCESS
        # ==========================
        else:
            qs = qs.filter(doctor=user)

        # ==========================
        # FILTER BY PATIENT
        # ==========================
        patient_id = self.request.query_params.get("patient_id")

        if patient_id:
            qs = qs.filter(patient__id=patient_id)

        return qs.order_by("-id")

    def get_serializer_class(self):

        if self.action in ["list", "retrieve"]:
            return DietPlanReadSerializer

        return DietPlanCreateSerializer

    def perform_create(self, serializer):
        diet_plan = serializer.save(
            doctor=self.request.user
        )

        from notification.services import send_notification

        # Notify patient when diet plan is assigned
        send_notification(
            user=diet_plan.patient,
            title="New Diet Plan Assigned",
            message=f"A new diet plan has been assigned to you by Dr. {self.request.user.profile.first_name or self.request.user.username}",
            n_type="diet",
            data={"diet_plan_id": diet_plan.id}
        )

        # Notify doctor when a new patient is assigned (first diet plan for this patient)
        is_first = DietPlan.objects.filter(
            doctor=self.request.user,
            patient=diet_plan.patient
        ).count() == 1

        if is_first:
            patient_name = diet_plan.patient.profile.first_name or diet_plan.patient.username
            send_notification(
                user=self.request.user,
                title="New Patient Assigned",
                message=f"Patient {patient_name} has been assigned to you",
                n_type="general",
                data={"patient_id": diet_plan.patient.id}
            )

    def get_serializer_context(self):

        context = super().get_serializer_context()

        target_date = self.request.query_params.get("date")

        if target_date:
            from datetime import datetime

            try:
                context["target_date"] = datetime.strptime(
                    target_date,
                    "%Y-%m-%d"
                ).date()

            except ValueError:
                pass

        return context
class ReviewHealthStatusView(APIView):
    """
    Allows doctors to review the health status of patients.
    """
    permission_classes = [PermissionsManager, IsDoctorUser]
    codename = 'healthstatus'

    def get(self, request):
        if not hasattr(request.user, 'role') or request.user.role != 'doctor':
            return Response({'error': 'Access denied'}, status=403)
        patients = CustomUser.objects.filter(role='patient')
        data = []
        for patient in patients:
            health_status = {
                'patient_id': patient.id,
                'username': patient.username,
                'diet_plans': patient.assigned_diets.count(),
                'lab_reports': patient.lab_reports.count(),
            }
            data.append(health_status)
        return Response(data)
    
    
class DoctorAssignExerciseView(APIView):
        """
        Allows doctors to assign exercises to patients.
        """
        permission_classes = [PermissionsManager, IsDoctorUser]
        serializer_class = ExcerciseDateAssignSerializer
        codename = 'exercisedate'

        def post(self, request):
            serializer = ExcerciseDateAssignSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            patient_id = serializer.validated_data['patient_id']
            exercise_ids = serializer.validated_data['exercise_ids']
            dates = serializer.validated_data['dates']

            patient = get_object_or_404(CustomUser, id=patient_id, role='patient')
            doctor = request.user 

            for ex_id in exercise_ids:
                exercise = get_object_or_404(Exercise, id=ex_id)
                for date in dates:
                    ExerciseDate.objects.get_or_create(
                        exercise=exercise,
                        date=date,
                        doctor=doctor,
                        patient=patient 
                    )

            # Notify patient when exercises are assigned
            from notification.services import send_notification
            exercise_names = [get_object_or_404(Exercise, id=eid).title for eid in exercise_ids]
            send_notification(
                user=patient,
                title="New Exercises Assigned",
                message=f"Exercises assigned: {', '.join(exercise_names)}",
                n_type="exercise",
                data={"exercise_ids": exercise_ids}
            )

            return Response({"message": "Exercises assigned successfully."}, status=status.HTTP_201_CREATED)
        
        def get(self, request):
            """
            Allows doctors to view assigned exercises.
            """
            doctor = request.user
            exercises = ExerciseDate.objects.filter(doctor=doctor).select_related(
                "exercise", "patient__profile", "doctor__profile"
            )

            data = [
                {
                    "exercise_id": ex.exercise.id if ex.exercise else None,
                    "exercise_name": ex.exercise.title if ex.exercise else "Exercise",

                    "patient_id": ex.patient.id if ex.patient else None,
                    "patient_name": (
                        f"{getattr(ex.patient.profile, 'first_name', '') or ''} "
                        f"{getattr(ex.patient.profile, 'last_name', '') or ''}"
                    ).strip() or "Patient",

                    "assigned_by": (
                        f"{getattr(ex.doctor.profile, 'first_name', '') or ''} "
                        f"{getattr(ex.doctor.profile, 'last_name', '') or ''}"
                    ).strip() or "Doctor",

                    "status": (
                        ex.status_entries.first().status
                        if ex.status_entries.exists()
                        else "pending"
                    ),

                    "date": ex.date
                }
                for ex in exercises
            ]

            return Response(data, status=200)
        
class DoctorExerciseReviewView(generics.CreateAPIView):
    serializer_class = DoctorExerciseResponseSerializer
    permission_classes = [PermissionsManager, IsDoctorUser]
    codename = 'exercisedate'
    


class DoctorDietLogsView(APIView):
    permission_classes = [PermissionsManager, IsDoctorUser]
    codename = 'dietplan'

    def get(self, request):
        queryset = PatientDietQuestion.objects.all().order_by("-date")
        patient_id = request.query_params.get("patient_id")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        phone_number = request.query_params.get("phone_number")
        if phone_number:
            queryset = queryset.filter(patient__phone_number__icontains=phone_number)
        serializer = PatientDietQuestionSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


class DoctorExerciseLogsView(APIView):
    permission_classes = [PermissionsManager, IsDoctorUser]
    codename = 'patientexerciselog'

    def get(self, request):
        queryset = PatientExerciseLog.objects.all().order_by("-date")
        patient_id = request.query_params.get("patient_id")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(patient__profile__first_name__icontains=search) |
                Q(patient__profile__last_name__icontains=search) |
                Q(date__icontains=search)
            )
        serializer = PatientExerciseLogSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)