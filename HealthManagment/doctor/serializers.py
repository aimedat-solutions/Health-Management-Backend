from rest_framework import serializers
from users.models import CustomUser, DietPlan, MealPortion, DietPlanDate, DietPlanMeal, Profile, HealthStatus

class HealthStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthStatus
        fields =  "__all__"

class PatientSerializer(serializers.ModelSerializer):
    profileImage = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    healthData = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["id", "profileImage", "name", "age", "healthData"]

    def get_profileImage(self, obj):
        return obj.profile.profile_image.url if obj.profile.profile_image else None

    def get_name(self, obj):
        return f"{obj.profile.first_name} {obj.profile.last_name}".strip()

    def get_age(self, obj):
        return obj.profile.age

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

    class Meta:
        model = DietPlanMeal
        fields = ["id", "meal_type", "time_range", "portions"]

    def get_time_range(self, obj):
        if obj.start_time and obj.end_time:
            try:
                return f"{obj.start_time.strftime('%I %p')} – {obj.end_time.strftime('%I %p')}"
            except:
                return None
        return None
class DietPlanDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlanDate
        fields = "__all__"

class DietPlanCreateSerializer(serializers.ModelSerializer):
    diet = serializers.DictField(write_only=True)
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

        return diet_plan


class DietPlanReadSerializer(serializers.ModelSerializer):
    meals = DietPlanMealSerializer(many=True, read_only=True)
    dates = serializers.SerializerMethodField()
    patient_name = serializers.CharField(source="patient.first_name", read_only=True)

    class Meta:
        model = DietPlan
        fields = ["id", "patient", "patient_name", "dates", "meals"]

    def get_dates(self, obj):
        return [date.date for date in obj.diet_dates.all()]