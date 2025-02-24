from rest_framework import serializers
from users.models import DietPlan, LabReport, Question, Option,PatientResponse,PatientDietQuestion

class DietPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlan
        fields = '__all__'

class LabReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabReport
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
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
    class Meta:
        model = PatientDietQuestion
        fields = '__all__'   