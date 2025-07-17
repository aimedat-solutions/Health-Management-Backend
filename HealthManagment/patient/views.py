from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import DietPlan, LabReport, Question,PatientResponse,CustomUser,PatientDietQuestion, Option, DietPlanStatus,Exercise,ExerciseStatus,HealthStatus,DietPlanDate,DietPlanMeal
from .serializers import PatientResponseSerializer,EmptyLabReportSerializer, HealthStatusSerializer, LabReportSerializer, QuestionSerializer, DietQuestionSerializer, DietPlanSerializer, DietPlanStatusSerializer, BulkPatientResponseSerializer,ExerciseStatusSerializer
from users.permissions import PermissionsManager,IsDoctorUser,IsPatientUser
from rest_framework import viewsets, permissions,generics,status
from rest_framework.parsers import MultiPartParser, FormParser
from users.filters import DietQuestionFilter,DietPlanMealFilter
from django_filters.rest_framework import DjangoFilterBackend
from users.filters import LabReportFilter
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone
from datetime import timedelta,datetime
from django.conf import settings
from django.shortcuts import get_object_or_404

class LabReportViewSet(viewsets.ModelViewSet):
    permission_classes = [PermissionsManager]
    queryset = LabReport.objects.all()
    serializer_class = LabReportSerializer
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
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if not queryset.exists():
            serializer = EmptyLabReportSerializer({})
            return Response(serializer.data, status=status.HTTP_200_OK)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
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
        health_status_qs = HealthStatus.objects.filter(patient=request.user)
        serializer = HealthStatusSerializer(health_status_qs, many=True)

        data = {
            'health_reports': serializer.data,
            'lab_reports': LabReport.objects.filter(patient=request.user).count(),
        }
        return Response(data)

class PatientResponseViewSet(viewsets.ModelViewSet):
    queryset = PatientResponse.objects.all()
    serializer_class = PatientResponseSerializer
    permission_classes = [PermissionsManager]
    codename = 'patientresponse'

    def get_queryset(self):
        """Return all responses for the logged-in user."""
        user = self.request.user
        return PatientResponse.objects.filter(user=user)      
    
    def list(self, request, *args, **kwargs):
        """Override list() to return messages when necessary."""
        user = self.request.user
        user_status = get_object_or_404(CustomUser, id=user.id)

        if user_status.is_first_login:
            if not PatientResponse.objects.filter(user=user, question__category="initial").exists():
                return Response({"message": "Please answer the initial questions."}, status=status.HTTP_200_OK)

        if not user_status.initial_question_completed:
            return Response({"message": "Please complete the initial questions first."}, status=status.HTTP_200_OK)

        return super().list(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """
        - Accepts multiple question-answer pairs.
        - Saves all responses.
        - Checks if all initial questions are answered before updating user status.
        - Example request for POST
        {
            "questions": ["1", "2", "3"],
            "1": "5-7 hours",
            "2": "First trimester (weeks 1-13)",
            "3": "Ft"
        }

        """
        user = self.request.user
        if user.initial_question_completed:
            return Response(
                {"message": "You have already completed the initial questions. No further responses are needed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        data = request.data
        serializer = BulkPatientResponseSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        question_ids = serializer.validated_data["questions"]
        responses_to_create = []
        for q_id in question_ids:
            try:
                question = Question.objects.get(id=q_id)
                response_value = data.get(str(q_id))  # Get the answer for the question

                # Handle multiple-choice answers
                if isinstance(response_value, list):
                    for option_value in response_value:
                        selected_option = Option.objects.filter(question=question, value=option_value).first()
                        if selected_option:
                            responses_to_create.append(
                                PatientResponse(
                                    user=user,
                                    question=question,
                                    selected_option=selected_option,
                                    response_text=None
                                )
                            )
                        else:
                            responses_to_create.append(
                                PatientResponse(
                                    user=user,
                                    question=question,
                                    selected_option=None,
                                    response_text=option_value
                                )
                            )
                else:
                    selected_option = Option.objects.filter(question=question, value=response_value).first()
                    responses_to_create.append(
                        PatientResponse(
                            user=user,
                            question=question,
                            selected_option=selected_option,
                            response_text=None if selected_option else response_value
                        )
                    )

            except Question.DoesNotExist:
                return Response({"error": f"Question ID {q_id} not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Bulk create responses
        PatientResponse.objects.bulk_create(responses_to_create)

        # Check if all initial questions are answered
        total_initial_questions = Question.objects.filter(category="initial").count()
        answered_initial_questions = PatientResponse.objects.filter(
            user=user, question__category="initial"
        ).values_list("question", flat=True).distinct().count()

        if answered_initial_questions >= total_initial_questions:
            user.initial_question_completed = True
            user.is_first_login = False  
            user.save()

        return Response({"message": "Responses saved successfully!"}, status=status.HTTP_201_CREATED)
class InitialQuestionsView(generics.ListAPIView):
    serializer_class = QuestionSerializer
    permission_classes =[PermissionsManager]
    codename = 'initialquestion'

    def get_queryset(self):
        user = self.request.user
        user_status, created = CustomUser.objects.get_or_create(id=user.id)

        if user_status.is_first_login:
            if not user_status.initial_question_completed:
                return Question.objects.filter(category="initial")
            return Question.objects.filter(category="initial")  # Don't show again if already answered

        # If initial questions are not answered → Show empty
        if not user_status.initial_question_completed:
            return Question.objects.filter(category="initial")

        # If initial questions answered → Show diet questions
        return Question.objects.filter(category="diet")

class DietQuestionsView(generics.ListCreateAPIView):
    permission_classes = [PermissionsManager]
    serializer_class = DietQuestionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DietQuestionFilter
    queryset = PatientDietQuestion.objects.all()
    codename = 'patientdietquestion'
    
    def get_queryset(self):
        return PatientDietQuestion.objects.filter(patient=self.request.user)
    
    def get(self, request):
        """
        Retrieve the latest diet details for the patient.
        """
        user = request.user

        if user.role != "patient":
            return Response({"message": "Only patients can access diet questions."}, status=status.HTTP_403_FORBIDDEN)
        queryset = self.filter_queryset(self.get_queryset())
        last_diet = queryset.order_by('-last_diet_update').first()
        
        if not last_diet:
            return Response(
                {
                    "message": "No diet records found. Please submit your diet details.",
                    "ask_diet_question": user.ask_diet_question
                }, 
                status=status.HTTP_200_OK
            )
            
        if timezone.now().date() >= last_diet.last_diet_update + timedelta(days=int(settings.DIET_QUESTION_ADD_DAYS)):
            user.ask_diet_question = True  
            user.save()

        if not last_diet.is_due_for_update():
            return Response(
                {
                    "message": "Diet update not yet due.",
                    "diet_details": DietQuestionSerializer(last_diet).data,
                    "ask_diet_question": user.ask_diet_question
                }, 
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "message": "Diet details retrieved successfully.",
                "diet_details": DietQuestionSerializer(last_diet).data,
                "ask_diet_question": user.ask_diet_question
            },
            status=status.HTTP_200_OK
        )
        
    def post(self, request):
        """
        POST the patient's diet details.
        Expected Request:
        {
            "breakfast": "Oatmeal with fruits",
            "lunch": "Grilled chicken with salad",      
            "dinner": "Steamed fish with vegetables",
            eveningSnack": "Mixed nuts", 
            "mms": "3", 
            "preBreakfast": "1"
        }
        """
        user = request.user

        # Check if the user is a patient and has completed the initial questions
        if user.role != "patient":
            return Response({"message": "Only patients can add diet details."}, status=status.HTTP_403_FORBIDDEN)
        
        if not user.initial_question_completed:
            return Response({"message": "Complete the initial questions first."}, status=status.HTTP_400_BAD_REQUEST)

        patient_diet, created = PatientDietQuestion.objects.get_or_create(patient=user)

        # Ensure the diet question can only be submitted after the allowed interval
        allowed_days = int(getattr(settings, "DIET_QUESTION_ADD_DAYS", 7))  # Default to 7 days if setting is missing
        if not created and patient_diet.last_diet_update >= timezone.now().date() - timedelta(days=allowed_days):
            return Response({"message": "Diet details already submitted recently."}, status=status.HTTP_400_BAD_REQUEST)

        # Update diet details
        diet_fields = ["date", "breakfast", "lunch", "eveningSnack", "dinner", "mms", "preBreakfast"]
        for field in diet_fields:
            setattr(patient_diet, field, request.data.get(field, getattr(patient_diet, field)))

        patient_diet.save()

        # Set flag to False after submission
        user.ask_diet_question = False
        user.save()

        return Response(
            {
                "message": "Diet details saved successfully.",
                "diet_details": DietQuestionSerializer(patient_diet).data,
                "ask_diet_question": user.ask_diet_question
            },
            status=status.HTTP_201_CREATED
        )

class DietPlanView(generics.ListAPIView):
    serializer_class = DietPlanSerializer
    permission_classes = [PermissionsManager]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DietPlanMealFilter
    serch_field = ['date ']
    codename = 'dietplanmeal'

    def get_queryset(self):
        return DietPlanDate.objects.filter(
            diet_plan__patient=self.request.user
        ).select_related("diet_plan").prefetch_related(
            "diet_plan__meals__meal_portions"
        ).order_by("date")
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        date_str = self.request.query_params.get("date")
        if date_str:
            from datetime import datetime
            try:
                context["target_date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        return context
    
class CompleteSkipDietPlanView(APIView):
    serializer_class = DietPlanStatusSerializer
    permission_classes = [PermissionsManager]
    codename = 'dietplanstatus'
    
    def post(self, request):
        print(request.data)
        """Update diet plan meal status for a specific assigned date"""
        patient = request.user
        diet_plan_meal_id = request.data.get("diet_plan")
        new_status = request.data.get("status")
        date_str = request.data.get("date")
        audio_file = request.FILES.get("audio_reason")

        if not all([diet_plan_meal_id, new_status, date_str]):
            return Response(
                {"error": "Fields 'diet_plan', 'status', and 'date' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        meal = get_object_or_404(DietPlanMeal, id=diet_plan_meal_id)

        is_assigned = DietPlanDate.objects.filter(
            diet_plan=meal.diet_plan,
            date=target_date,
            diet_plan__patient=patient
        ).exists()

        if not is_assigned:
            return Response(
                {"error": "This meal is not assigned to you on the given date."},
                status=status.HTTP_403_FORBIDDEN
            )

        audio_data = audio_file.read() if new_status == "skipped" and audio_file else None

        status_entry, _ = DietPlanStatus.objects.update_or_create(
            patient=patient,
            diet_plan=meal,
            date=target_date,
            defaults={
                "status": new_status,
                "reason_audio": audio_data
            }
        )

        serializer = DietPlanStatusSerializer(status_entry)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CompleteSkipExerciseView(APIView):
    serializer_class = ExerciseStatusSerializer
    permission_classes = [PermissionsManager]  
    codename = 'exercisestatus'
    
    def post(self, request):
        """Mark exercise as skipped or completed"""
        user_id = request.user.id 
        exercise_id = request.data.get("exercise")
        new_status = request.data.get("status")  
        audio_file = request.FILES.get("audio_reason")  

        if not new_status or not exercise_id:
            return Response(
                {"error": "Both 'exercise' and 'status' are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        exercise = get_object_or_404(Exercise, id=exercise_id)

        audio_data = None
        if new_status == "skipped" and audio_file:
            audio_data = audio_file.read()  
            
        status_entry, created = ExerciseStatus.objects.update_or_create(
            user_id=user_id,  
            exercise=exercise,
            defaults={"status": new_status, "audio_reason": audio_data}
        )

        serializer = ExerciseStatusSerializer(status_entry)
        return Response(serializer.data, status=status.HTTP_200_OK)