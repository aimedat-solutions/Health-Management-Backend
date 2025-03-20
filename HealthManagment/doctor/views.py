from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import CustomUser, DietPlan, MealPortion
from .serializers import PatientSerializer, DietPlanSerializer, MealPortionSerializer
from users.permissions import PermissionsManager
from rest_framework import viewsets, filters
class PatientManagementView(APIView):
    """
    Allows doctors to view and edit patient details.
    """
    permission_classes = [PermissionsManager]
    serializer_class = PatientSerializer

    def get(self, request):
        patients = CustomUser.objects.filter(role='patient')
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)

    def patch(self, request, patient_id):
        try:
            patient = CustomUser.objects.get(id=self, role='patient')
        except CustomUser.DoesNotExist:
            return Response({'error': 'Patient not found.'}, status=404)

        serializer = PatientSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class MealPortionViewSet(viewsets.ModelViewSet):
    queryset = MealPortion.objects.all()
    serializer_class = MealPortionSerializer
    permission_classes = [IsAuthenticated]
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
    permission_classes = [PermissionsManager]

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
























# from rest_framework import generics, permissions
# from users.models import Profile, Question,DietPlan,Exercise, CustomUser,Option,PatientResponse, LabReport
# from .serializers import PatientSerializer,ExerciseSerializer, DietPlanSerializer, DoctorRegistrationSerializer, QuestionSerializer,QuestionAnswerSerializer,QuestionCreateSerializer,LabReportSerializer

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
    
# class DoctorRegistrationAPIView(APIView):
#     serializer_class = DoctorRegistrationSerializer
#     def post(self, request):
#         serializer = DoctorRegistrationSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#             # Use the serializer to represent the user data
#             user_data = DoctorRegistrationSerializer(user).data
#             return Response({
#                 "message": "Doctor registered successfully.",
#                 "user_details": user_data
#             }, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        
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
    
    
    
    
    
    
    
    
