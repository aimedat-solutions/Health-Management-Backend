from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import ExerciseDate, LabReport, Question,PatientResponse,CustomUser,PatientDietQuestion, Option, DietPlanStatus,Exercise,ExerciseStatus,HealthStatus,DietPlanDate,DietPlanMeal,DietPlan,ExtraMeal, DietPlanCompletedPortion,MealPortion
from .serializers import ( PatientResponseSerializer,EmptyLabReportSerializer, HealthStatusSerializer, LabReportSerializer, 
                          QuestionSerializer, DietQuestionSerializer, DietPlanSerializer, DietPlanStatusSerializer, CurrentMealSerializer, BulkPatientResponseSerializer,
                          ExerciseStatusSerializer, AssignedExerciseSerializer)
from users.permissions import PermissionsManager,IsDoctorUser,IsPatientUser
from rest_framework import viewsets, permissions,generics,status
from rest_framework import serializers
from users.filters import DietQuestionFilter,DietPlanMealFilter,LabReportFilter,ExerciseFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta,datetime
from django.conf import settings
from django.shortcuts import get_object_or_404
import json
from rest_framework.parsers import MultiPartParser, FormParser
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
            from .serializers import EmptyLabReportSerializer
            serializer = EmptyLabReportSerializer({})
            return Response(serializer.data, status=status.HTTP_200_OK)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
        Handles patient responses:
        - Accepts initial questions only once.
        - Accepts other questions only after initial questions are completed.
        - Supports single or multiple answers.
        - Ensures 'text' type options require text input.
        - All-or-nothing save: if any error, no responses are saved.
        - Example : {
                        "questions": [15, 16, 17, 21, 22,26,29,30,31,32,33,34], 
                        "15": "Yes", 
                        "16": "5 years", 
                        "17": ["Diet/Exercise","Metformin", "Insulin", {"option_id": 71, "value": "Others", "text": "I take herbal medicine"}], 
                        "21": "Yes", "22": ["Diet/Exercise","Metformin", "Insulin", {"option_id": 71, "value": "Others", "text": "I take herbal medicine"}], 
                        "26" : "Yes", "29" : ["Maternal", "Paternal", "Both", "Siblings"], 
                        "30" : "Yes", "31" : "Yes", 
                        "32" : ["Metformin", "Others"],
                        "33" : "Yes",
                        "34" : "2 weeks"
                    }
        """
        user = request.user
        data = request.data

        serializer = BulkPatientResponseSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        question_ids = serializer.validated_data["questions"]
        questions = Question.objects.filter(id__in=question_ids).prefetch_related("options")
        initial_questions = questions.filter(category="initial")
        other_questions = questions.filter(category="other")

        # Check initial/other question rules
        if not user.initial_question_completed and other_questions.exists():
            raise serializers.ValidationError(
                "You must complete all initial questions before answering other questions."
            )

        if user.initial_question_completed and initial_questions.exists():
            raise serializers.ValidationError(
                "Initial questions already completed. You can now only answer other questions."
            )

        saved_responses = []
        errors = []
        responses_to_create = []

        for question in questions:
            q_id = str(question.id)
            response_value = data.get(q_id)
            if q_id in [str(q) for q in question_ids] and response_value is None:
                errors.append({
                    "question_id": question.id,
                    "message": "Answer required but not provided"
                })
                continue
            if response_value is None:
                continue

            if not isinstance(response_value, list):
                response_value = [response_value]
            for val in response_value:
                if isinstance(val, dict) and "option_id" in val:
                    selected_option = Option.objects.filter(id=val["option_id"], question=question).first()
                    text_value = val.get("text")
                else:
                    selected_option = Option.objects.filter(question=question, value=val).first()
                    text_value = None
                # If option requires text but text is missing, register error
                if selected_option and selected_option.type == "text" and not text_value:
                    errors.append({
                        "question_id": question.id,
                        "option_id": selected_option.id,
                        "message": "Text required for this option"
                    })
                # Prepare valid responses for bulk create
                responses_to_create.append(
                    PatientResponse(
                        user=user,
                        question=question,
                        selected_option=selected_option,
                        response_text=text_value if text_value else (None if selected_option else val)
                    )
                )
                saved_responses.append({
                    "question_id": question.id,
                    "option_id": selected_option.id if selected_option else None,
                    "response_text": text_value if text_value else (None if selected_option else val)
                })
        # Validate that all main initial questions are answered
        if not user.initial_question_completed:
            total_initial = Question.objects.filter(category="initial", parent__isnull=True)
            required_main_ids = [q.id for q in total_initial]
            answered_main_ids = [int(q) for q in data.get("questions", []) if int(q) in required_main_ids]
            missing_ids = set(required_main_ids) - set(answered_main_ids)
            if missing_ids:
                errors.append({
                    "message": "Please answer all main questions.",
                    "missing_questions": list(missing_ids)
                })
        # **All-or-nothing save**
        if errors:
            return Response({
                "message": "Errors found, no responses saved.",
                "errors": errors
            }, status=status.HTTP_400_BAD_REQUEST)
        # Save all valid responses
        PatientResponse.objects.bulk_create(responses_to_create)
        # Update user flags
        user.initial_question_completed = True
        # user.is_first_login = False
        user.last_question_answered_at = timezone.now().date()
        user.save()
        return Response({
            "message": "All responses saved successfully!",
            # "saved_responses": saved_responses
        }, status=status.HTTP_201_CREATED)

class InitialQuestionsView(generics.ListAPIView):
    serializer_class = QuestionSerializer
    permission_classes =[PermissionsManager]
    codename = 'question'

    def list(self, request, *args, **kwargs):
        user = request.user
        user_status = CustomUser.objects.get(id=user.id)
        interval_days = int(getattr(settings, "QUESTIONS_DAYS", 10))
        interval = timedelta(days=interval_days)
        today = timezone.now().date()

        if user_status.is_first_login and not user_status.initial_question_completed:
            queryset = Question.objects.filter(category="initial", parent__isnull=True)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        if user_status.initial_question_completed:
            last_other_answer = (
                PatientResponse.objects
                .filter(user=user, question__category="other")
                .order_by("-created_at")
                .values_list("created_at", flat=True)
                .first()
            )

            if not last_other_answer:
                queryset = Question.objects.filter(category="other", parent__isnull=True)
                serializer = self.get_serializer(queryset, many=True)
                return Response(serializer.data)

            last_answer_date = last_other_answer.date()

            if today >= last_answer_date + interval:
                queryset = Question.objects.filter(category="other", parent__isnull=True)
                serializer = self.get_serializer(queryset, many=True)
                return Response(serializer.data)

            return Response(
                {"message": f"Next questions will be available on {last_answer_date + interval}."},
                status=status.HTTP_200_OK
            )
        return Response([], status=status.HTTP_200_OK)

class DietQuestionsView(generics.ListCreateAPIView):
    permission_classes = [PermissionsManager]
    serializer_class = DietQuestionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DietQuestionFilter
    codename = 'patientdietquestion'

    def get_queryset(self):
        return PatientDietQuestion.objects.filter(
            patient=self.request.user
        ).order_by("-date")

    # ================= GET =================
    def get(self, request):
        user = request.user

        if user.role != "patient":
            return Response(
                {"message": "Only patients can access diet questions."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = self.filter_queryset(self.get_queryset())

        last_diet = queryset.first()

        is_due = PatientDietQuestion.is_due_for_update(user)

        if not last_diet:
            return Response({
                "message": "No diet records found.",
                "diet_logs": [],
                "ask_diet_question": True
            }, status=200)

        return Response({
            "message": "Diet questions fetched successfully",
            "diet_logs": DietQuestionSerializer(
                queryset,
                many=True,
                context={"request": request}
            ).data,
            "last_entry": DietQuestionSerializer(
                last_diet,
                context={"request": request}
            ).data,
            "ask_diet_question": is_due
        }, status=200)

    # ================= POST =================
    def post(self, request):
        user = request.user

        if user.role != "patient":
            return Response(
                {"message": "Only patients can add diet details."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not user.initial_question_completed:
            return Response(
                {"message": "Complete the initial questions first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔥 3-DAY RULE CHECK
        if not PatientDietQuestion.is_due_for_update(user):
            return Response({
                "message": "You can update diet only after allowed days"
            }, status=400)

        today = timezone.now().date()

        # 🔥 CREATE NEW ENTRY (NOT UPDATE OLD)
        diet = PatientDietQuestion.objects.create(
            patient=user,
            date=today,
            breakfast=request.data.get("breakfast"),
            lunch=request.data.get("lunch"),
            eveningSnack=request.data.get("eveningSnack"),
            dinner=request.data.get("dinner"),
            breakfast_audio=request.FILES.get("breakfast_audio"),
            lunch_audio=request.FILES.get("lunch_audio"),
            eveningSnack_audio=request.FILES.get("eveningSnack_audio"),
            dinner_audio=request.FILES.get("dinner_audio"),
        )

        user.is_first_login = False
        user.save()

        return Response({
            "message": "Diet details saved successfully",
            "diet_details": DietQuestionSerializer(
                diet,
                context={"request": request}
            ).data,
            "ask_diet_question": False
        }, status=status.HTTP_201_CREATED)
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
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [PermissionsManager]
    codename = 'dietplanstatus'
    
    def post(self, request):
        """Patient updates ONE specific meal (breakfast/lunch/dinner/snack) for a given date"""
        patient = request.user
        diet_plan_meal_id = request.data.get("diet_plan")
        new_status = request.data.get("status")
        date_str = request.data.get("date")
        audio_file = request.FILES.get("audio_reason")
        selected_portion_ids = request.data.get("selected_portions", [])
        others = request.data.get("others", [])
        others_audio = request.FILES.get("extra_audio")
        others_image = request.FILES.get("others_image")

        # Basic validation
        if not all([diet_plan_meal_id, new_status, date_str]):
            return Response(
                {"error": "Required fields: diet_plan, status, date, selected_portions"},
                status=400
            )

        # Parse date
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format"}, status=400)
        
        now = datetime.now().date()
        time_difference = (now - target_date).days
        if time_difference > 2:
            return Response({"error": "Editing diet status is allowed only within 48 hours."}, status=403)


        # Fetch meal entry
        meal = get_object_or_404(DietPlanMeal, id=diet_plan_meal_id)

        # Check if patient owns this diet plan + date
        if not DietPlanDate.objects.filter(
            diet_plan=meal.diet_plan,
            date=target_date,
            diet_plan__patient=patient
        ).exists():
            return Response({"error": "Meal not assigned on this patient/date."}, status=403)

        # Read audio reason only for skipped
        audio_data = audio_file if new_status == "skipped" and audio_file else None

        # --- UPDATE STATUS ENTRY ---
        status_entry, _ = DietPlanStatus.objects.update_or_create(
            patient=patient,
            diet_plan=meal,
            date=target_date,
            defaults={"status": new_status, "reason_audio": audio_data}
        )

        # --- IF COMPLETED: HANDLE PORTIONS + EXTRAS ---
        if new_status == "completed":
            # Ensure JSON data is parsed
            if isinstance(selected_portion_ids, str):
                try:
                    selected_portion_ids = json.loads(selected_portion_ids)
                except:
                    selected_portion_ids = []

            # ✅ Clear previous portions for this meal+date
            DietPlanCompletedPortion.objects.filter(
                patient=patient, diet_plan_meal=meal, date=target_date
            ).delete()

            # ✅ Save selected portions
            for portion_id in selected_portion_ids:
                try:
                    portion = MealPortion.objects.get(id=portion_id)
                    DietPlanCompletedPortion.objects.create(
                        patient=patient,
                        diet_plan_meal=meal,
                        portion=portion,
                        date=target_date
                    )
                except MealPortion.DoesNotExist:
                    return Response(
                        {"error": f"Portion ID {portion_id} not found."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # ✅ Clear previous extra meals (avoid duplicates)
            ExtraMeal.objects.filter(
                patient=patient, diet_plan_meal=meal, date=target_date
            ).delete()

            # ✅ Save new extras
            if others or others_audio:
                try:
                    ExtraMeal.objects.create(
                        patient=patient,
                        diet_plan_meal=meal,
                        date=target_date,
                        item_name=others,
                        audio_entry=others_audio if others_audio else None,
                        image=others_image if others_image else None, 
                    )
                except Exception as e:
                    return Response(
                        {"error": f"Error saving extra meal: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        serializer = DietPlanStatusSerializer(status_entry)
        return Response(
            {
                "message": f"{meal.meal_type.capitalize()} for {date_str} updated successfully",
                "data": serializer.data
            },
            status=200
        )

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
        interval_days = int(getattr(settings, "QUESTIONS_DAYS", 10))
        interval = timedelta(days=interval_days)

        if not user.initial_question_completed:
            return Response({
                "status": "available",
                "type": "initial",
                "message": "Initial questions are available."
            })

        has_other = (
            PatientResponse.objects
            .filter(user=user, question__category="other")
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )

        if not has_other:
            return Response({
                "status": "available",
                "type": "other",
                "message": "Other questions are available."
            })
        last_other_answer_date = has_other.date()
        if today >= last_other_answer_date + interval:
            return Response({
                "status": "available",
                "type": "other",
                "message": "Next round of other questions is available."
            })

        next_date = last_other_answer_date  + interval if last_other_answer_date  else None
        return Response({
            "status": "wait",
            "next_question_date": next_date,
            "message": f"Next questions available on {next_date}" if next_date else "No previous answer date found."
        })