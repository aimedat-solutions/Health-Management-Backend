from rest_framework import serializers
from users.models import ExerciseDate, LabReport, Question, HealthStatus,PatientResponse, PatientDietQuestion, PatientExerciseLog, DietPlanStatus, ExerciseStatus,DietPlanMeal,DietPlanDate,DietPlanCompletedPortion,ExtraMeal
from users.serializers import OptionSerializer
from django.utils import timezone
from datetime import date
class EmptyLabReportSerializer(serializers.Serializer):
    message = serializers.SerializerMethodField()

    def get_message(self, obj):
        return "Patients are does not have any lab report until now."
class DietPlanStatusSerializer(serializers.ModelSerializer):
    reason_audio = serializers.FileField(required=False)

    class Meta:
        model = DietPlanStatus
        fields = ['status', 'date', 'reason_audio', 'diet_plan']

    def create(self, validated_data):
        """Convert audio file to binary before saving"""
        audio_file = validated_data.pop('reason_audio', None)

        if audio_file:
            validated_data['reason_audio'] = audio_file.read()  # Convert file to binary

        return DietPlanStatus.objects.create(**validated_data)

    def get_reason_audio(self, obj):
        """Return the binary data as a base64 encoded string"""
        if obj.reason_audio:
            import base64
            return base64.b64encode(obj.reason_audio).decode('utf-8')
        return None

class DietPlanMealSerializer(serializers.ModelSerializer):
    portions = serializers.SerializerMethodField()
    time_range = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    others = serializers.SerializerMethodField()
    class Meta:
        model = DietPlanMeal
        fields = ['id','meal_type', 'time_range', 'portions', 'status', 'others']

    def get_portions(self, obj):
        return [{"id": p.id, "name": p.name} for p in obj.meal_portions.all()]
    
    def get_time_range(self, obj):
        if obj.start_time and obj.end_time:
            try:
                return f"{obj.start_time.strftime('%#I %p')} – {obj.end_time.strftime('%#I %p')}"
            except:
                return f"{obj.start_time.strftime('%H:%M')} – {obj.end_time.strftime('%H:%M')}"
        return None
    
    def get_status(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        date = self.context.get("target_date", timezone.now().date())

        if user and user.is_authenticated:
            status_obj = DietPlanStatus.objects.filter(
                patient=user,
                diet_plan=obj,   # obj is DietPlanMeal
                date=date
            ).first()

            return status_obj.status if status_obj else "pending"

        return "pending"
    
    def get_others(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        date = self.context.get("target_date", timezone.now().date())

        if user:
            extra_items = ExtraMeal.objects.filter(
                patient=user,
                diet_plan_meal=obj,
                date=date
            )
            return [
                {
                    "id": e.id,
                    "text": e.item_name,
                    # "quantity": e.quantity,
                    # "notes": e.notes,
                    "audio_entry": bool(e.audio_entry)
                } for e in extra_items
            ]
        return []
    
class DietPlanSerializer(serializers.ModelSerializer):
    meals = serializers.SerializerMethodField()

    class Meta:
        model = DietPlanDate
        fields = ['date', 'meals']

    def get_meals(self, obj):
        MEAL_ORDER = ['breakfast', 'lunch', 'snacks', 'dinner']
        all_meals = obj.diet_plan.meals.all()
        meals_map = {meal.meal_type: meal for meal in all_meals}

        sorted_meals = [
            meals_map[meal_type]
            for meal_type in MEAL_ORDER
            if meal_type in meals_map
        ]

        return DietPlanMealSerializer(
            sorted_meals,
            many=True,
            context={**self.context, "target_date": obj.date}
        ).data
class CurrentMealSerializer(serializers.Serializer):
    meal_id = serializers.CharField() 
    meal_type = serializers.CharField()
    time_window = serializers.CharField()
    portions = serializers.ListField(child=serializers.CharField())
    status = serializers.CharField()
    diet_date = serializers.DateField()
    
class DietPlanStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlanStatus
        fields = "__all__"


class DietPlanCompletedPortionSerializer(serializers.ModelSerializer):
    portion_name = serializers.CharField(source="portion.name", read_only=True)

    class Meta:
        model = DietPlanCompletedPortion
        fields = ["id", "diet_plan_meal", "portion", "portion_name", "date"]


class ExtraMealSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraMeal
        fields = "__all__"
    
class LabReportSerializer(serializers.ModelSerializer):
    message = serializers.SerializerMethodField()
    class Meta:
        model = LabReport
        fields = '__all__'
        
    def get_message(self, obj):
        return "Lab report exists for the patient."
    
    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        validated_data['date_of_report'] = date.today()
        return super().create(validated_data)
        
class HealthStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthStatus
        fields = '__all__'
class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)
    sub_questions = serializers.SerializerMethodField()
    class Meta:
        model = Question
        fields = [
            "id", "question_image", "question_text", "category", "type", "placeholder", "max_length",
            "condition_value", "options", "sub_questions"]
    
    def get_sub_questions(self, obj):
        sub_qs = obj.sub_questions.all()
        return QuestionSerializer(sub_qs, many=True, context=self.context).data
class PatientResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientResponse
        fields = '__all__'   
        
class BulkPatientResponseSerializer(serializers.Serializer):
    questions = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )

    def validate(self, data):
        """Ensure all question IDs exist before processing"""
        question_ids = data.get("questions", [])
        existing_questions = set(Question.objects.filter(id__in=question_ids).values_list("id", flat=True))

        # Check for invalid question IDs
        invalid_questions = set(question_ids) - existing_questions
        if invalid_questions:
            raise serializers.ValidationError(f"Invalid question IDs: {list(invalid_questions)}")

        return data      
class DietQuestionSerializer(serializers.ModelSerializer):
    ask_diet_question = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientDietQuestion
        fields = '__all__'   
        
    def get_ask_diet_question(self, obj):
        return obj.patient.ask_diet_question
    
    def get_date(self, obj):
        if obj.date:
            return obj.date.date().isoformat() if hasattr(obj.date, 'date') else obj.date
        return None
class ExerciseStatusSerializer(serializers.ModelSerializer):
    reason_audio = serializers.FileField(required=False)

    class Meta:
        model = ExerciseStatus
        fields = ["exercise", "status", "reason_audio"]

    def create(self, validated_data):
        """Convert audio file to binary before saving"""
        audio_file = validated_data.pop('reason_audio', None)

        if audio_file:
            validated_data['reason_audio'] = audio_file.read() 

        return DietPlanStatus.objects.create(**validated_data)

    def get_reason_audio(self, obj):
        """Return the binary data as a base64 encoded string"""
        if obj.reason_audio:
            import base64
            return base64.b64encode(obj.reason_audio).decode('utf-8')
        return None
    
class AssignedExerciseSerializer(serializers.ModelSerializer):
    exercise_id = serializers.IntegerField(source='exercise.id')
    exercise_title = serializers.CharField(source='exercise.title')
    exercise_description = serializers.CharField(source='exercise.description')
    image_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    assigned_by = serializers.CharField(source='doctor.first_name')
    status = serializers.SerializerMethodField()

    class Meta:
        model = ExerciseDate
        fields = ['id', 'exercise_id', 'exercise_title', 'exercise_description',  'image_url', 'video_url','date', 'assigned_by', 'status']
        
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.exercise.image_content and request:
            return request.build_absolute_uri(obj.exercise.image_content.url)
        return None

    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.exercise.video_content and request:
            return request.build_absolute_uri(obj.exercise.video_content.url)
        return None
        
    def get_status(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        date = self.context.get("target_date", timezone.now().date())

        if user and user.is_authenticated:
            status_obj = ExerciseStatus.objects.filter(
                user=user,
                exercise=obj   
            ).first()

            return status_obj.status if status_obj else "pending"

        return "pending"

class ExerciseLogSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()

    class Meta:
        model = PatientExerciseLog
        fields = '__all__'

    def get_date(self, obj):
        if obj.date:
            return obj.date.date().isoformat() if hasattr(obj.date, 'date') else obj.date
        return None
