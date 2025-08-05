from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import ExerciseDate, LabReport, Question,PatientResponse,CustomUser,PatientDietQuestion, Option, DietPlanStatus,Exercise,ExerciseStatus,HealthStatus,DietPlanDate,DietPlanMeal,DietPlan
from .serializers import ( PatientResponseSerializer,EmptyLabReportSerializer, HealthStatusSerializer, LabReportSerializer, 
                          QuestionSerializer, DietQuestionSerializer, DietPlanSerializer, DietPlanStatusSerializer, CurrentMealSerializer, BulkPatientResponseSerializer,
                          ExerciseStatusSerializer, AssignedExerciseSerializer)
from users.permissions import PermissionsManager,IsDoctorUser,IsPatientUser
from rest_framework import viewsets, permissions,generics,status
from rest_framework.parsers import MultiPartParser, FormParser
from users.filters import DietQuestionFilter,DietPlanMealFilter,LabReportFilter,ExerciseFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone
from django.utils.dateparse import parse_date
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
        - Accepts initial questions only once.
        - Accepts other questions only after initial questions are completed.
        - Supports single or multiple answers.
        - Example request for POST
        {
            "questions": ["1", "2", "3"],
            "1": "5-7 hours",
            "2": "First trimester (weeks 1-13)",
            "3": ["Option A", "Option B"]
        }

        """
        user = request.user
        data = request.data

        serializer = BulkPatientResponseSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        question_ids = serializer.validated_data["questions"]
        questions = Question.objects.filter(id__in=question_ids)
        initial_questions = questions.filter(category="initial")
        other_questions = questions.filter(category="other")

        if not user.initial_question_completed and other_questions.exists():
            return Response(
                {"message": "You must complete all initial questions before answering other questions."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.initial_question_completed and initial_questions.exists():
            return Response(
                {"message": "Initial questions already completed. You can now only answer other questions."},
                status=status.HTTP_400_BAD_REQUEST
            )

        responses_to_create = []
        for question in questions:
            q_id = str(question.id)
            response_value = data.get(q_id)

            if isinstance(response_value, list):
                for val in response_value:
                    selected_option = Option.objects.filter(question=question, value=val).first()
                    responses_to_create.append(PatientResponse(
                        user=user,
                        question=question,
                        selected_option=selected_option if selected_option else None,
                        response_text=None if selected_option else val
                    ))
            else:
                selected_option = Option.objects.filter(question=question, value=response_value).first()
                responses_to_create.append(PatientResponse(
                    user=user,
                    question=question,
                    selected_option=selected_option if selected_option else None,
                    response_text=None if selected_option else response_value
                ))

        PatientResponse.objects.bulk_create(responses_to_create)

        if not user.initial_question_completed:
            total_initial = Question.objects.filter(category="initial").count()
            answered_initial = PatientResponse.objects.filter(
                user=user, question__category="initial"
            ).values_list("question", flat=True).distinct().count()

            if answered_initial >= total_initial:
                user.initial_question_completed = True
                user.is_first_login = False
                user.last_question_answered_at = timezone.now().date()
                user.save()

        return Response({"message": "Responses saved successfully!"}, status=status.HTTP_201_CREATED)
class InitialQuestionsView(generics.ListAPIView):
    serializer_class = QuestionSerializer
    permission_classes =[PermissionsManager]
    codename = 'question'

    def list(self, request, *args, **kwargs):
        user = request.user
        user_status = CustomUser.objects.get(id=user.id)

        # If first login and hasn't answered initial questions yet → show "initial" questions
        if user_status.is_first_login and not user_status.initial_question_completed:
            queryset = Question.objects.filter(category="initial")
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        # If initial completed, get "other" questions
        if user_status.initial_question_completed:
            today = timezone.now().date()
            has_answered_today = PatientResponse.objects.filter(
                user=user, question__category="other", created_at__date=today
            ).exists()

            if has_answered_today:
                return Response(
                    {"message": "Next questions will be available soon."},
                    status=status.HTTP_200_OK
                )

            queryset = Question.objects.filter(category="other")
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        # Default: no questions
        return Response([], status=status.HTTP_200_OK)

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
            "eveningSnack": "Mixed nuts"
        }
        """
        user = request.user

        # Check if the user is a patient and has completed the initial questions
        if user.role != "patient":
            return Response({"message": "Only patients can add diet details."}, status=status.HTTP_403_FORBIDDEN)
        
        if not user.initial_question_completed:
            return Response({"message": "Complete the initial questions first."}, status=status.HTTP_400_BAD_REQUEST)

        patient_diet, created = PatientDietQuestion.objects.get_or_create(patient=user)

        allowed_days = int(getattr(settings, "DIET_QUESTION_ADD_DAYS", 3))  
        if not created and patient_diet.last_diet_update >= timezone.now().date() - timedelta(days=allowed_days):
            return Response({"message": "Diet details already submitted recently."}, status=status.HTTP_400_BAD_REQUEST)

        diet_fields = ["date", "breakfast", "lunch", "eveningSnack", "dinner", "breakfast_audio", "lunch_audio", "eveningSnack_audio", "dinner_audio"]
        for field in diet_fields:
            setattr(patient_diet, field, request.data.get(field, getattr(patient_diet, field)))

        patient_diet.save()
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

class DietQuestionStatusView(APIView):
    """
    GET: Returns whether the patient should be asked diet questions (every 3 days).
    POST: Allows skipping the question by setting ask_diet_question = False.
    """
    permission_classes = [PermissionsManager]
    codename = "patientdietquestion"

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role != "patient":
            return Response({"detail": "Only patients can access this."}, status=403)

        interval_days = int(getattr(settings, "DIET_QUESTION_ADD_DAYS", 3))
        today = timezone.now().date()

        last_entry = PatientDietQuestion.objects.filter(patient=user).order_by("-date").first()

        # Skipped last time — return skip response
        if user.ask_diet_question is False and not last_entry:
            return Response({
                "should_ask": False,
                "last_answered_date": None,
                "next_due_date": None
            })

        # If patient submitted last time
        if last_entry:
            last_date = last_entry.date
            next_due_date = last_date + timedelta(days=interval_days)

            if today >= next_due_date and not user.ask_diet_question:
                user.ask_diet_question = True
                user.save(update_fields=["ask_diet_question"])

            return Response({
                "should_ask": user.ask_diet_question,
                "last_answered_date": last_date,
                "next_due_date": next_due_date
            })

        # First time or ask_diet_question manually true
        if user.ask_diet_question:
            return Response({
                "should_ask": True,
                "last_answered_date": None,
                "next_due_date": today
            })

        # Fallback (shouldn't reach here usually)
        return Response({
            "should_ask": False,
            "last_answered_date": None,
            "next_due_date": None
        })

    def post(self, request, *args, **kwargs):
        """
        Patient skips diet questions — mark as skipped.
        """
        user = request.user
        if user.role != "patient":
            return Response({"detail": "Only patients can perform this action."}, status=403)

        user.ask_diet_question = False
        user.save(update_fields=["ask_diet_question"])

        return Response({
            "message": "Diet question skipped.",
            "should_ask": False
        })
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

class CurrentOrNextMealView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.localtime()
        today = now.date()
        time_now = now.time()

        diet_plan = DietPlan.objects.filter(
            patient=user,
            diet_dates__date=today
        ).prefetch_related('meals__meal_portions').first()

        if not diet_plan:
            diet_plan = DietPlan.objects.filter(
                patient=user,
                diet_dates__date__gt=today
            ).order_by('diet_dates__date').prefetch_related('meals__meal_portions').first()

            if not diet_plan:
                return Response({"detail": "No diet plan assigned for today or upcoming days."}, status=200)

            plan_date = diet_plan.diet_dates.order_by('date').first().date
        else:
            plan_date = today

        meals = diet_plan.meals.filter(start_time__isnull=False, end_time__isnull=False).order_by("start_time")

        for meal in meals:
            start = meal.start_time
            end = meal.end_time

            status_obj = DietPlanStatus.objects.filter(
                patient=user, diet_plan=meal, date=plan_date
            ).first()
            status = status_obj.status if status_obj else "pending"

            if status in ["completed", "skipped"]:
                continue

            if time_now < start:
                tag = "upcoming"
            elif start <= time_now <= end:
                tag = "ongoing"
            else:
                tag = "missed"

            if tag in ["upcoming", "ongoing"]:
                time_window = f"{start.strftime('%I %p').lstrip('0')} – {end.strftime('%I %p').lstrip('0')}"

                data = {
                    "meal_id": meal.id,
                    "meal_type": meal.get_meal_type_display(),
                    "time_window": time_window,
                    "portions": [p.name for p in meal.meal_portions.all()],
                    "status": status,
                    "diet_date": str(plan_date)
                }
                return Response({"current_meal": data}, status=200)

        return Response({"detail": "No upcoming or pending meals for today."}, status=200)
    
class PatientAssignedExercisesView(APIView):
    serializer_class = AssignedExerciseSerializer
    permission_classes = [PermissionsManager]
    codename = 'exercisedate'

    def get(self, request):
        patient = request.user
        date = request.query_params.get('date')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = ExerciseDate.objects.filter(patient=patient)

        if date:
            parsed_date = parse_date(date)
            if parsed_date:
                queryset = queryset.filter(date=parsed_date)

        elif start_date and end_date:
            start = parse_date(start_date)
            end = parse_date(end_date)
            if start and end:
                queryset = queryset.filter(date__range=(start, end))

        serializer = AssignedExerciseSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
class CompleteSkipExerciseView(APIView):
    serializer_class = ExerciseStatusSerializer
    permission_classes = [PermissionsManager]  
    codename = 'exercisestatus'
    
    def post(self, request):
        """Mark exercise as skipped or completed"""
        user_id = request.user.id 
        id = request.data.get("exercise")
        new_status = request.data.get("status")  
        audio_file = request.FILES.get("audio_reason")  

        if not new_status or not id:
            return Response(
                {"error": "Both 'exercise' and 'status' are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        exercise = get_object_or_404(ExerciseDate, id=id)

        audio_data = None
        if new_status == "skipped" and audio_file:
            audio_data = audio_file.read()  
            
        status_entry, created = ExerciseStatus.objects.update_or_create(
            user_id=user_id,  
            exercise=exercise,
            defaults={"status": new_status, "reason_audio": audio_data}
        )

        serializer = ExerciseStatusSerializer(status_entry)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class QuestionFlowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        interval = timedelta(days=int(getattr(settings, "QUESTIONS_DAYS", 15)))
        last_answered = user.last_question_answered_at

        if not user.initial_question_completed:
            return Response({
                "status": "available",
                "type": "initial",
                "message": "Initial questions are available."
            })

        has_other = PatientResponse.objects.filter(
            user=user, question__category="other"
        ).exists()

        if not has_other:
            return Response({
                "status": "available",
                "type": "other",
                "message": "Other questions are available."
            })

        if last_answered and today >= last_answered + interval:
            return Response({
                "status": "available",
                "type": "other",
                "message": "Next round of other questions is available."
            })

        next_date = last_answered + interval if last_answered else None
        return Response({
            "status": "wait",
            "next_question_date": next_date,
            "message": f"Next questions available on {next_date}"
        })