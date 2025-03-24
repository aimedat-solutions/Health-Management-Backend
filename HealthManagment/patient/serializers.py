from rest_framework import serializers
from users.models import DietPlan, LabReport, Question, Option,PatientResponse, PatientDietQuestion, DietPlanStatus, ExerciseStatus
from users.serializers import OptionSerializer
class DietPlanStatusSerializer(serializers.ModelSerializer):
    reason_audio = serializers.FileField(required=False)

    class Meta:
        model = DietPlanStatus
        fields = ['status', 'reason_audio', 'diet_plan' ]

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

class DietPlanSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    class Meta:
        model = DietPlan
        fields = '__all__'
        
    def get_status(self, obj):
        """Retrieve the latest diet plan status for the patient"""
        status_entry = obj.status_entries.order_by('-updated_at').first()
        return DietPlanStatusSerializer(status_entry).data if status_entry else None
    
class LabReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabReport
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