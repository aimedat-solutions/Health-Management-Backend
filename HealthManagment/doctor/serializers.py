from rest_framework import serializers
from users.models import CustomUser, Profile, DietPlan, MealPortion, DietPlanDate, DietPlanMeal, DietPlanStatus, HealthStatus,ExerciseDate,DoctorExerciseResponse,PatientDietQuestion
from django.utils import timezone
class HealthStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthStatus
        fields =  "__all__"
        
class ProfileSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    pregnancy_month = serializers.ReadOnlyField()
    gestational_age = serializers.ReadOnlyField()
    edd = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = [
            "first_name", "last_name", "date_of_birth", "age",
            "gender", "occupation", "address", "specialization",
            "profile_image", "height", "weight", "lmp_date",
            "pregnancy_month", "gestational_age", "edd",
        ]
class PatientSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    healthData = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = [
            "id", "role", "username", "phone_number", "email", "is_verified","is_first_login", "initial_question_completed", "ask_diet_question", 
            "last_diet_question_answered","last_question_answered_at",
            "profile", "healthData",
        ]

    def get_healthData(self, obj):
        health_status = HealthStatus.objects.filter(patient=obj).first()
        return HealthStatusSerializer(health_status).data if health_status else {}

class MealPortionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPortion
        fields = "__all__"

class DietPlanMealSerializer(serializers.ModelSerializer):
    portions = MealPortionSerializer(source="meal_portions", many=True)
    time_range = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    statuses_by_date = serializers.SerializerMethodField()
    class Meta:
        model = DietPlanMeal
        fields = ["id", "meal_type", "time_range", "portions", "status", "statuses_by_date"]

    def get_time_range(self, obj):
        if obj.start_time and obj.end_time:
            try:
                return f"{obj.start_time.strftime('%I %p')} – {obj.end_time.strftime('%I %p')}"
            except:
                return None
        return None
    
    def get_status(self, obj):
        request = self.context.get('request')
        target_date = self.context.get("target_date") or timezone.now().date()

        if not request or not request.user.is_authenticated:
            return "pending"

        status_obj = DietPlanStatus.objects.filter(
            patient=obj.diet_plan.patient,
            diet_plan=obj,
            date=target_date
        ).first()

        return status_obj.status if status_obj else "pending"

    def get_statuses_by_date(self, obj):
        statuses = DietPlanStatus.objects.filter(
            patient=obj.diet_plan.patient,
            diet_plan=obj
        ).order_by("date")

        return [
            {
                "date": s.date,
                "status": s.status,
                "reason_audio": s.reason_audio.url if s.reason_audio else None,
            }
            for s in statuses
        ]
    
class DietPlanDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlanDate
        fields = "__all__"
class DietPlanMealValueSerializer(serializers.Serializer):
    meal_portions = serializers.ListField(
        child=serializers.IntegerField(),  # IDs of MealPortion
        allow_empty=True
    )
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
class DietPlanCreateSerializer(serializers.ModelSerializer):
    diet = serializers.DictField(child=DietPlanMealValueSerializer(), write_only=True)
    dates = serializers.ListField(child=serializers.DateField(), write_only=True)

    class Meta:
        model = DietPlan
        fields = ["id", "patient", "diet", "dates"]

    def create(self, validated_data):
        diet_data = validated_data.pop("diet")
        dates_data = validated_data.pop("dates")

        diet_plan = DietPlan.objects.create(**validated_data)

        for meal_type, meal_details in diet_data.items():
            meal_portions = meal_details.get("meal_portions", [])
            start_time = meal_details.get("start_time")  
            end_time = meal_details.get("end_time")      

            meal_instance = DietPlanMeal.objects.create(
                diet_plan=diet_plan,
                meal_type=meal_type,
                start_time=start_time,
                end_time=end_time
            )
            meal_instance.meal_portions.set(meal_portions)

        for date in dates_data:
            DietPlanDate.objects.create(diet_plan=diet_plan, date=date)
            
        patient = diet_plan.patient
        if hasattr(patient, "verified"):
            patient.is_verified = True
            patient.verified = True
            patient.save(update_fields=["verified", "is_verified"])

        return diet_plan


class DietPlanReadSerializer(serializers.ModelSerializer):
    meals = DietPlanMealSerializer(many=True, read_only=True)
    dates = serializers.SerializerMethodField()
    patient_name = serializers.CharField(source="patient.profile.first_name", read_only=True)
    doctor_id = serializers.IntegerField(source="doctor.id", read_only=True)
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = DietPlan
        fields = ["id", "patient", "patient_name", "doctor_id", "doctor_name", "dates", "meals"]

    def get_doctor_name(self, obj):
        profile = getattr(obj.doctor, "profile", None)
        first_name = getattr(profile, "first_name", "") or ""
        last_name = getattr(profile, "last_name", "") or ""
        return f"{first_name} {last_name}".strip() or "Doctor"

    def get_dates(self, obj):
        return [date.date for date in obj.diet_dates.all()]
    
    
class ExcerciseDateAssignSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    exercise_ids = serializers.ListField(child=serializers.IntegerField())
    dates = serializers.ListField(child=serializers.DateField())
    
class DoctorExerciseResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorExerciseResponse
        fields = '__all__'
           
class PatientDietQuestionSerializer(serializers.ModelSerializer):
    breakfast_audio = serializers.SerializerMethodField()
    lunch_audio = serializers.SerializerMethodField()
    eveningSnack_audio = serializers.SerializerMethodField()
    dinner_audio = serializers.SerializerMethodField()

    class Meta:
        model = PatientDietQuestion
        fields = "__all__"

    def get_full_url(self, obj, field):
        request = self.context.get("request")
        file = getattr(obj, field)
        if file:
            return request.build_absolute_uri(file.url)
        return None

    def get_breakfast_audio(self, obj):
        return self.get_full_url(obj, "breakfast_audio")

    def get_lunch_audio(self, obj):
        return self.get_full_url(obj, "lunch_audio")

    def get_eveningSnack_audio(self, obj):
        return self.get_full_url(obj, "eveningSnack_audio")

    def get_dinner_audio(self, obj):
        return self.get_full_url(obj, "dinner_audio")