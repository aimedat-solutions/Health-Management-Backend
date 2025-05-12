from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from users.models import CustomUser, DietPlan, MealPortion, Exercise, LabReport, PatientResponse, HealthStatus, Profile
from django.shortcuts import get_object_or_404
from .serializers import PatientSerializer, DietPlanSerializer, MealPortionSerializer
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
        
        if not doctor.role == "doctor":  # Ensure the user is a doctor
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
        
        if patient_id:
            patient = get_object_or_404(CustomUser, id=patient_id, role='patient', assigned_doctor=doctor)
            # Fetch assigned data
            exercises = Exercise.objects.filter(user=patient)
            diet_plans = DietPlan.objects.filter(patient=patient)
            lab_reports = LabReport.objects.filter(patient=patient)
            questions = PatientResponse.objects.filter(user=patient)

            response_data = {
                "patient_details": PatientSerializer(patient).data,
                "assigned_exercises": ExerciseSerializer(exercises, many=True).data,
                "assigned_diet_plans": DietPlanSerializer(diet_plans, many=True).data,
                "lab_reports": LabReportSerializer(lab_reports, many=True).data,
                "questions": PatientResponseSerializer(questions, many=True).data
            }

            return Response(response_data, status=status.HTTP_200_OK)
        
        # If no patient_id is provided, return all patients
        patients = CustomUser.objects.filter(role='patient', assigned_doctor=doctor) 
        response_data = {"patients": PatientSerializer(patients, many=True).data}
        return Response(response_data, status=status.HTTP_200_OK)


class MealPortionViewSet(viewsets.ModelViewSet):
    queryset = MealPortion.objects.all()
    serializer_class = MealPortionSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin, IsAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

class DietPlanViewSet(viewsets.ModelViewSet):
    """
    Allows doctors can add diet for patients.
    example : {
                "patient": 1,
                "diet": {
                    "breakfast": {
                    "meal_portions": [1, 2]
                    },
                    "lunch": {
                    "meal_portions": [3, 4]
                    }
                },
                "dates": ["2025-03-21", "2025-03-22"]
            }
    """
    queryset = DietPlan.objects.all()
    serializer_class = DietPlanSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user  
        serializer.save(doctor=user)

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
                'diet_plans': patient.received_diet_plans.count(),
                'lab_reports': patient.lab_reports.count(),
            }
            data.append(health_status)
        return Response(data)