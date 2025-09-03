from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models import CustomUser, DietPlan, MealPortion, Exercise, LabReport, PatientResponse, HealthStatus, DietPlanDate,ExerciseDate
from django.shortcuts import get_object_or_404
from .serializers import PatientSerializer, DietPlanCreateSerializer, MealPortionSerializer,DietPlanReadSerializer,DietPlanMealSerializer,ExcerciseDateAssignSerializer,DoctorExerciseResponseSerializer
from users.serializers import ExerciseDateSerializer
from patient.serializers import LabReportSerializer, PatientResponseSerializer
from users.permissions import PermissionsManager,IsDoctorUser, IsSuperAdmin, IsAdmin
from rest_framework import viewsets, filters, generics
from django_filters.rest_framework import DjangoFilterBackend
from users.filters import CustomUserFilter
from users.pagination import Pagination
from django.db.models.functions import ExtractMonth, ExtractYear, Now
from django.db.models import IntegerField, F, ExpressionWrapper
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
    ordering_fields = ['profile__first_name', 'age', 'birth_month', 'date_joined']
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
        
        assigned_exercises = ExerciseDate.objects.filter(patient=patient)
        diet_plans = DietPlan.objects.filter(patient=patient)
        lab_reports = LabReport.objects.filter(patient=patient)
        questions = PatientResponse.objects.filter(user=patient)

        data = {
            "patient_details": PatientSerializer(patient).data,
            "assigned_exercises": ExerciseDateSerializer(assigned_exercises, many=True).data,
            "assigned_diet_plans": DietPlanReadSerializer(diet_plans, many=True).data,
            "lab_reports": LabReportSerializer(lab_reports, many=True).data,
            "questions": PatientResponseSerializer(questions, many=True).data
        }
        return Response(data, status=status.HTTP_200_OK)
    

class MealPortionViewSet(viewsets.ModelViewSet):
    queryset = MealPortion.objects.all()
    serializer_class = MealPortionSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin, IsAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

class DietPlanViewSet(viewsets.ModelViewSet):
    """
    Allows doctors to create and retrieve diet plans for patients.
    
    example :
    
            {
              "patient": 1,
              "diet": {        
                        "breakfast":  {
                        "meal_portions": [1, 2]
                        },
                        "lunch":  {  
                        "meal_portions": [3, 4]
                        }   
                        },
              "dates": ["2025-03-21", "2025-03-22"]
            }    
    """
    queryset = DietPlan.objects.none()
    permission_classes = [PermissionsManager]
    serializer_class = DietPlanCreateSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["patient__username", "diet_dates"]
    codename = 'dietplan'

    def get_queryset(self):
        qs = DietPlan.objects.filter(doctor=self.request.user).prefetch_related(
            "meals__meal_portions",
            "diet_dates",
            "patient"
        )
        patient_id = self.request.query_params.get("patient_id")
        if patient_id:
            qs = qs.filter(patient__id=patient_id)
        return qs

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return DietPlanReadSerializer
        return DietPlanCreateSerializer

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        target_date = self.request.query_params.get('date')
        if target_date:
            from datetime import datetime
            try:
                context["target_date"] = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        return context

class ReviewHealthStatusView(APIView):
    """
    Allows doctors to review the health status of patients.
    """
    permission_classes = [PermissionsManager,IsDoctorUser]

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

            return Response({"message": "Exercises assigned successfully."}, status=status.HTTP_201_CREATED)
        
        def get(self, request):
            """
            Allows doctors to view assigned exercises.
            """
            doctor = request.user
            exercises = ExerciseDate.objects.filter(doctor=doctor)

            data = [
                {
                    "exercise_id": ex.exercise.id,
                    "exercise_name": ex.exercise.title,
                    "patient_name": ex.patient.profile.first_name + " " + ex.patient.profile.last_name,
                    "assigned_by": ex.doctor.profile.first_name + " " + ex.doctor.profile.last_name,
                    "status": ex.status_entries.first().status if ex.status_entries.exists() else "pending",
                    "date": ex.date
                }
                for ex in exercises
            ]
            return Response(data, status=200)
        
class DoctorExerciseReviewView(generics.CreateAPIView):
    serializer_class = DoctorExerciseResponseSerializer
    permission_classes = [IsAuthenticated]