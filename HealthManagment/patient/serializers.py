from rest_framework import serializers
from users.models import DietPlan, LabReport, Question, Option,PatientResponse,PatientDietSchedule

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



class PatientDietScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDietSchedule
        fields = ["patient", "last_diet_update", "is_due_for_update"]