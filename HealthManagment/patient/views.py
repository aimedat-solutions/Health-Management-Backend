from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import DietPlan, LabReport, Question,PatientResponse,CustomUser,PatientDietSchedule
from .serializers import PatientResponseSerializer, LabReportSerializer, QuestionSerializer,PatientDietScheduleSerializer
from users.permissions import PermissionsManager
from rest_framework import viewsets, permissions,generics,status
from rest_framework.decorators import action
from users.serializers import QuestionCreateSerializer
from django_filters.rest_framework import DjangoFilterBackend
from users.filters import LabReportFilter
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone
from django.utils.timezone import now
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
        """
        Logic for showing questions with messages:
        - If `is_first_login=True` → Show initial questions.
        - If `is_first_login=False` and initial questions are NOT answered → Return a message.
        - If `initial_question_completed=True` → Show diet questions.
        """
        user = self.request.user
        user_status, created = CustomUser.objects.get_or_create(id=user.id)

        if user_status.is_first_login:
            questions = Question.objects.filter(category="initial")
            if questions.exists():
                return questions
            return Response({"message": "Please answer the initial questions."}, status=status.HTTP_200_OK)

        if not user_status.initial_question_completed:
            return Response({"message": "Please complete the initial questions first."}, status=status.HTTP_200_OK)

        return Question.objects.filter(category="diet")     
    
    def list(self, request, *args, **kwargs):
        """Override list() to return messages when necessary."""
        user = self.request.user
        user_status = get_object_or_404(CustomUser, id=user.id)

        if user_status.is_first_login:
            if not Question.objects.filter(category="initial").exists():
                return Response({"message": "Please answer the initial questions."}, status=status.HTTP_200_OK)

        if not user_status.initial_question_completed:
            return Response({"message": "Please complete the initial questions first."}, status=status.HTTP_200_OK)

        return super().list(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """
        - Save patient responses.
        - Track question completions.
        - Update flags for `first_time_user` and `initial_question_completed`.
        """
        user = self.request.user
        response = serializer.save(user=user)
        question = response.question  

        if question.category == "initial":
            user.initial_question_completed = True
            user.is_first_login = False  # No longer a first-time user
            user.save()

        elif question.category == "diet":
            # Track last diet question answered
            user.last_diet_question_answered = now()
            user.save()

        return Response({"message": "Response saved!"}, status=status.HTTP_201_CREATED)
        

class InitialQuestionsView(generics.ListAPIView):
    serializer_class = QuestionSerializer
    permission_classes =[PermissionsManager]

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
    serializer_class = QuestionCreateSerializer
    queryset = Question.objects.all()

    def get(self, request):
        user = request.user
        schedule, created = PatientDietSchedule.objects.get_or_create(patient=user)

        if not user.initial_question_completed:
            return Response(
                {"message": "Please complete the initial assessment to access diet questions."}, 
                status=status.HTTP_200_OK
            )
        diet_questions = Question.objects.filter(category="diet")
        return Response(QuestionCreateSerializer(diet_questions, many=True).data, status=status.HTTP_200_OK)
    
class PatientDietScheduleViewSet(viewsets.ModelViewSet):
    queryset = PatientDietSchedule.objects.all()
    serializer_class = PatientDietScheduleSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        schedule = self.get_object()

        # Update Diet Every 15 Days
        if schedule.is_due_for_update():
            schedule.last_diet_update = now()
            schedule.save()
            return Response({"message": "Diet updated!"}, status=status.HTTP_200_OK)

        return Response({"message": "Not due for update!"}, status=status.HTTP_400_BAD_REQUEST)