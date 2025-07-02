from rest_framework import serializers
from users.models import DietPlan, LabReport, Question, HealthStatus,PatientResponse, PatientDietQuestion, DietPlanStatus, ExerciseStatus,DietPlanMeal,DietPlanDate
from users.serializers import OptionSerializer
from django.utils import timezone
class EmptyLabReportSerializer(serializers.Serializer):
    message = serializers.SerializerMethodField()

    def get_message(self, obj):
        return "This patient does not have any lab report until now."
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
    class Meta:
        model = DietPlanMeal
        fields = ['id','meal_type', 'time_range', 'portions', 'status']

    def get_portions(self, obj):
        return [p.name for p in obj.meal_portions.all()]
    
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

    
class LabReportSerializer(serializers.ModelSerializer):
    message = serializers.SerializerMethodField()
    class Meta:
        model = LabReport
        fields = '__all__'
        
    def get_message(self, obj):
        return "Lab report exists for the patient."
        
class HealthStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthStatus
        fields = '__all__'
class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)
    class Meta:
        model = Question
        fields = [
            "id", "question_text", "category", "type", "placeholder", "max_length",
            "created_at", "updated_at", "created_by", "updated_by", "options"
        ]
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
    
    class Meta:
        model = PatientDietQuestion
        fields = '__all__'   
        
    def get_ask_diet_question(self, obj):
        return obj.patient.ask_diet_question
    
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