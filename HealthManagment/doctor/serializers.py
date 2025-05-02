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
    meal_portions = serializers.PrimaryKeyRelatedField(queryset=MealPortion.objects.all(), many=True)

    class Meta:
        model = DietPlanMeal
        fields = "__all__"

class DietPlanDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlanDate
        fields = "__all__"

class DietPlanSerializer(serializers.ModelSerializer):
    diet = serializers.DictField(write_only=True)
    dates = serializers.ListField(child=serializers.DateField(), write_only=True)

    class Meta:
        model = DietPlan
        fields = ["id", "patient",  "diet", "dates"]

    def create(self, validated_data):
        diet_data = validated_data.pop("diet")  
        dates_data = validated_data.pop("dates")

        diet_plan = DietPlan.objects.create(**validated_data)

        # Creating meals
        for meal_type, meal_details in diet_data.items():
            meal_portions = meal_details.get("meal_portions", [])
            meal_instance = DietPlanMeal.objects.create(diet_plan=diet_plan, meal_type=meal_type)
            meal_instance.meal_portions.set(meal_portions)

        # Process each date
        for date in dates_data:
            DietPlanDate.objects.create(diet_plan=diet_plan, date=date)

        return diet_plan