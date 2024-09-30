from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth.models import Group, Permission
from .utils import send_otp, verify_otp
from .models import Doctor, Question, Patient,DietPlan,Exercise, CustomUser, Option
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES)
    phone_number = serializers.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'email', 'role', 'phone_number')

    def create(self, validated_data):
        phone_number = validated_data.pop('phone_number', None)
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role']
        )
        group = Group.objects.get(name=validated_data['role'])
        user.groups.add(group)
        
        if phone_number:
            user.phone_number = phone_number
            user.save()
            send_otp(phone_number)
            print(send_otp)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(required=False)
    otp = serializers.CharField(required=False)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        phone_number = attrs.get('phone_number')
        otp = attrs.get('otp')

        if email and password:
            user = CustomUser.objects.filter(email=email).first()
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
        elif phone_number and otp:
            user = CustomUser.objects.filter(phone_number=phone_number).first()
            if not user:
                raise serializers.ValidationError("User with this phone number does not exist.")
            response = verify_otp(phone_number, otp)
            if response['type'] != 'success':
                raise serializers.ValidationError("OTP verification failed.")
        else:
            raise serializers.ValidationError("Must include either email and password or phone number and OTP.")

        attrs['user'] = user
        return attrs

class PhoneNumberSerializer(serializers.ModelSerializer):
    phone_number = PhoneNumberField()

    class Meta:
        model = CustomUser
        fields = ('phone_number',)
class CustomUserDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('pk', 'username', 'email', 'role', 'phone_number')
        read_only_fields = ('email',)

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'phone_number','password']
        extra_kwargs = {'password': {'write_only': True}}

class DoctorSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    class Meta:
        model = Doctor
        fields = ['id', 'user', 'specialty']

class PatientSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    class Meta:
        model = Patient
        fields = ['id', 'user', 'first_name', 'last_name', 'date_of_birth', 'gender', 'address', 'health_status']
        
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = User.objects.create(**user_data)
        patient = Patient.objects.create(user=user, **validated_data)
        return patient

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user')
        user = instance.user

        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.address = validated_data.get('address', instance.address)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.health_status = validated_data.get('health_status', instance.health_status)
        instance.save()

        user.role = user_data.get('role', user.role)
        user.is_active = user_data.get('is_active', user.is_active)
        user.is_staff = user_data.get('is_staff', user.is_staff)
        user.save()

        return instance

class DoctorSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()

    class Meta:
        model = Doctor
        fields = ['id', 'user', 'specialty']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = User.objects.create(**user_data)
        doctor = Doctor.objects.create(user=user, **validated_data)
        return doctor

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user')
        user = instance.user

        instance.specialty = validated_data.get('specialty', instance.specialty)
        instance.save()

        user.role = user_data.get('role', user.role)
        user.is_active = user_data.get('is_active', user.is_active)
        user.is_staff = user_data.get('is_staff', user.is_staff)
        user.save()

        return instance

class DietPlanSerializer(serializers.ModelSerializer):
    meal_plan = serializers.ListField(child=serializers.CharField())
    class Meta:
        model = DietPlan
        fields = ['id', 'patient', 'date', 'diet_name', 'time_of_day', 'meal_plan']

    def create(self, validated_data):
        request = self.context.get('request')
        patient = validated_data['patient']
        doctor = request.user.doctor
        if patient.doctor != doctor:
            raise serializers.ValidationError("You can only create diet plans for your own patients.")
        diet_plan = DietPlan.objects.create(**validated_data)
        return diet_plan

    def validate_meal_plan(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Meal plan must be a list of items.")
        return value

class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            'id', 'user', 'exercise_name', 'exercise_type', 'duration', 
            'intensity', 'calories_burned', 'date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']



class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'value']

class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'type', 'question_text', 'options', 'placeholder', 'max_length']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Only include 'placeholder' and 'max_length' for 'description' type
        if instance.type != 'description':
            representation.pop('placeholder', None)
            representation.pop('max_length', None)

        return representation  
class OptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['value']

# Serializer for creating questions with options
class QuestionCreateSerializer(serializers.ModelSerializer):
    options = OptionCreateSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['type', 'question_text', 'placeholder', 'max_length', 'options']
        extra_kwargs = {
            'placeholder': {'required': False},  # Make placeholder optional
            'max_length': {'required': False},   # Make max_length optional
        }
    
    def validate(self, data):
        # Ensure 'placeholder' and 'max_length' are optional but allowed for 'description' type
        if data['type'] != 'description' and ('placeholder' in data or 'max_length' in data):
            raise serializers.ValidationError("Only description type questions can have a placeholder or max_length.")
        
        return data

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        question = Question.objects.create(**validated_data)
        if question.type != 'description':
            for option_data in options_data:
                Option.objects.create(question=question, **option_data)
        
        return question
        
