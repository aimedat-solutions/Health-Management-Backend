from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models import CustomUser, DietPlan, MealPortion, Exercise, LabReport, PatientResponse, HealthStatus, DietPlanMeal
from django.shortcuts import get_object_or_404
from .serializers import PatientSerializer, DietPlanCreateSerializer, MealPortionSerializer,DietPlanReadSerializer,DietPlanMealSerializer
from users.serializers import ExerciseSerializer
from patient.serializers import LabReportSerializer, PatientResponseSerializer
from users.permissions import PermissionsManager,IsDoctorUser, IsSuperAdmin, IsAdmin
from rest_framework import viewsets, filters
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
            # Fetch assigned data
            exercises = Exercise.objects.filter(user=patient)
            diet_plans = DietPlan.objects.filter(patient=patient)
            lab_reports = LabReport.objects.filter(patient=patient)
            questions = PatientResponse.objects.filter(user=patient)

            response_data = {
                "patient_details": PatientSerializer(patient).data,
                "assigned_exercises": ExerciseSerializer(exercises, many=True).data,
                "assigned_diet_plans": DietPlanMealSerializer(diet_plans, many=True).data,
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