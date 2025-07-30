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
class PatientManagementView(APIView):
    """
    Allows doctors to view and edit patient details.
    """
    permission_classes = [PermissionsManager,IsDoctorUser,]
    serializer_class = PatientSerializer

    def get(self, request, patient_id=None):
        """
        - If patient_id is provided, return full details including assigned exercises, diet plans, lab reports, and questions.
        - If patient_id is not provided, return a list of all patients.
        """
        doctor = request.user
        
        if doctor.role != "doctor":  # Ensure the user is a doctor
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
        
        if patient_id:
            patient = get_object_or_404(CustomUser, id=patient_id, role='patient')
            assigned_exercises = ExerciseDate.objects.filter(patient=patient)
            
            
            diet_plans = DietPlan.objects.filter(patient=patient)
            lab_reports = LabReport.objects.filter(patient=patient)
            questions = PatientResponse.objects.filter(user=patient)

            response_data = {
                "patient_details": PatientSerializer(patient).data,
                "assigned_exercises": ExerciseDateSerializer(assigned_exercises, many=True).data,
                "assigned_diet_plans": DietPlanReadSerializer(diet_plans, many=True).data,
                "lab_reports": LabReportSerializer(lab_reports, many=True).data,
                "questions": PatientResponseSerializer(questions, many=True).data
            }

            return Response(response_data, status=status.HTTP_200_OK)
        
        # If no patient_id is provided, return all patients
        patients = CustomUser.objects.filter(role='patient') 
        response_data = {"patients": PatientSerializer(patients, many=True).data}
        return Response(response_data, status=status.HTTP_200_OK)
    
    def patch(self, request, patient_id=None):
        """
        Doctor can assign a patient to themselves.
        """
        user = request.user
        if user.role != "doctor":
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

        if not patient_id:
            return Response({"error": "Patient ID is required to assign."}, status=status.HTTP_400_BAD_REQUEST)

        patient = get_object_or_404(CustomUser, id=patient_id, role='patient')

        if patient.assigned_doctor:
            return Response({"error": "This patient is already assigned to a doctor."}, status=status.HTTP_400_BAD_REQUEST)

        patient.assigned_doctor = user
        patient.save()

        return Response({"message": f"Patient {patient.get_full_name()} has been assigned to you."}, status=status.HTTP_200_OK)

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
    search_fields = ["patient__username"]
    codename = 'dietplan'

    def get_queryset(self):
        qs = DietPlan.objects.filter(doctor=self.request.user).prefetch_related(
            "meals__meal_portions",
            "diet_dates",
            "patient"
        )
        return qs

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return DietPlanReadSerializer
        return DietPlanCreateSerializer

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user)

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
            patient_id = request.query_params.get("patient_id")
            if not patient_id:
                return Response({"detail": "patient_id is required"}, status=400)

            doctor = request.user
            exercises = ExerciseDate.objects.filter(doctor=doctor, patient__id=patient_id)

            data = [
                {
                    "exercise_id": ex.exercise.id,
                    "exercise_name": ex.exercise.title,
                    "date": ex.date
                }
                for ex in exercises
            ]
            return Response(data, status=200)
        
class DoctorExerciseReviewView(generics.CreateAPIView):
    serializer_class = DoctorExerciseResponseSerializer
    permission_classes = [IsAuthenticated]