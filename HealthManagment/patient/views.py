from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import DietPlan, LabReport, Question,PatientResponse,CustomUser,PatientDietQuestion, Option
from .serializers import PatientResponseSerializer, LabReportSerializer, QuestionSerializer,DietQuestionSerializer,BulkPatientResponseSerializer
from users.permissions import PermissionsManager
from rest_framework import viewsets, permissions,generics,status
from rest_framework.decorators import action
from users.serializers import QuestionCreateSerializer
from django_filters.rest_framework import DjangoFilterBackend
from users.filters import LabReportFilter
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.shortcuts import get_object_or_404

class LabReportViewSet(viewsets.ModelViewSet):
    queryset = LabReport.objects.all()
    serializer_class = LabReportSerializer
    permission_classes = [PermissionsManager]
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
        data = {
            'diet_plans': DietPlan.objects.filter(assigned_to=request.user).count(),
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

class DietQuestionsView(APIView):
    permission_classes = [PermissionsManager]
    serializer_class = DietQuestionSerializer
    queryset = PatientDietQuestion.objects.all()
    codename = 'patientdietquestion'

    def get(self, request):
        """
        Retrieve the latest diet details for the patient.
        """
        user = request.user

        if user.role != "patient":
            return Response({"message": "Only patients can access diet questions."}, status=status.HTTP_403_FORBIDDEN)
        
        last_diet = PatientDietQuestion.objects.filter(patient=user).order_by('-last_diet_update').first()
        
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

        if user.initial_question_completed and user.role != "patient":
            return Response({"message": "Only patients can add diet detials."}, status=status.HTTP_403_FORBIDDEN)

        patient_diet, created = PatientDietQuestion.objects.get_or_create(patient=user)

        if not created and patient_diet.last_diet_update >= timezone.now().date() - timedelta(days=int(settings.DIET_QUESTION_ADD_DAYS)):
            return Response({"message": "Already Submited Diet detials...!"}, status=status.HTTP_400_BAD_REQUEST)

        # Update diet details
        patient_diet.breakfast = request.data.get("breakfast", patient_diet.breakfast)
        patient_diet.lunch = request.data.get("lunch", patient_diet.lunch)
        patient_diet.eveningSnack = request.data.get("eveningSnack", patient_diet.eveningSnack)
        patient_diet.dinner = request.data.get("dinner", patient_diet.dinner)
        patient_diet.mms = request.data.get("mms", patient_diet.mms)
        patient_diet.preBreakfast = request.data.get("preBreakfast", patient_diet.preBreakfast)
        patient_diet.last_diet_update = timezone.now()

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