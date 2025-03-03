from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth.models import Group, Permission
from .utils import send_otp, verify_otp
from .models import  Question, Profile,DietPlan,Exercise, CustomUser, Option, PatientResponse,LabReport,DietPlanStatus
import re,os
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    
    phone_number = serializers.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ('role', 'phone_number')

    # def validate_username(self, value):
    #     # Ensure the username does not contain numbers
    #     if re.search(r'\d', value):
    #         raise serializers.ValidationError("Username should not contain numbers.")
    #     # Check if the username already exists
    #     if CustomUser.objects.filter(username=value).exists():
    #         raise serializers.ValidationError("A user with this username already exists.")
    #     return value

    # def validate_email(self, value):
    #     # Check if the email already exists
    #     if CustomUser.objects.filter(email=value).exists():
    #         raise serializers.ValidationError("A user with this email already exists.")
    #     return value

    def validate_phone_number(self, value):
        # Ensure the phone number is valid (e.g., contains only digits and has a valid length)
        if not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError("Enter a valid phone number. It should be between 9 and 15 digits.")
        # Check if the phone number already exists
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_role(self, value):
        # Disallow creating users with the admin role directly
        if value == 'admin':
            raise serializers.ValidationError("Admin role cannot be created directly.")
        return value

    def create(self, validated_data):
        phone_number = validated_data.pop('phone_number', None)
        role = validated_data.pop('role', None)
        user = CustomUser.objects.create_user(
            username=phone_number,  
            role=role,
            password=CustomUser.objects.make_random_password(),  # Auto-generate password if not given
        )
        # Add the user to the appropriate group based on their role
        group = Group.objects.get(name=role)
        Profile.objects.create(user=user)
        user.groups.add(group)
        
        # If a phone number is provided, add it to the user and send an OTP
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
        
        environment = os.getenv('DJANGO_ENV', 'development')

        if email and password:
            user = CustomUser.objects.filter(username=email).first()
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
        elif phone_number and otp:
            user = CustomUser.objects.filter(phone_number=phone_number).first()
            if not user:
                raise serializers.ValidationError("User with this phone number does not exist.")
            if environment in ['production', 'staging']:
                # Verify OTP in production and staging
                response = verify_otp(phone_number, otp)
                if response['type'] != 'success':
                    raise serializers.ValidationError("OTP verification failed.")
            else:
                # In non-production environments, verify with random OTP `1234`
                if otp != '1234':
                    raise serializers.ValidationError("Invalid OTP.")
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
        fields = ('pk', 'username', 'email', 'role', 'first_name', 'last_name', 'phone_number', "created_at", "created_by", "updated_at", "updated_by")
        read_only_fields = ('email',)

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'phone_number','password']
        extra_kwargs = {'password': {'write_only': True}}


class ProfileSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='user.role', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    class Meta:
        model = Profile
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth', 'age', 'gender',
            'address', 'specialization', 'profile_image', 'calories', 
            'height', 'weight', 'role', 'phone_number', 
        ]
        
    
class DoctorRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number']  # Include only relevant fields
        read_only_fields = ['id', 'role'] 

    def create(self, validated_data):
        phone_number = validated_data.get('phone_number')

        try:
            user = CustomUser.objects.get(phone_number=phone_number)
            send_otp(phone_number)
            return user
        except CustomUser.DoesNotExist:
            validated_data['role'] = 'doctor'
            base_username = slugify(phone_number)
            username = base_username
            num_suffix = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}_{num_suffix}"
                num_suffix += 1
            
            validated_data['username'] = username
            validated_data['password'] = CustomUser.objects.make_random_password()
            group = Group.objects.get(name=validated_data['role'])
            user = CustomUser.objects.create(**validated_data)
            
            Profile.objects.create(user=user)
            user.groups.add(group)
            user.save()
            send_otp(phone_number)
            return user
        
class DietPlanStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlanStatus
        fields = "__all__"
        
class DietPlanSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    meal_plan = serializers.ListField(child=serializers.CharField())
    class Meta:
        model = DietPlan
        fields = "__all__"
    
    def get_status(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            status = DietPlanStatus.objects.filter(patient=request.user, diet_plan=obj).first()
            return status.status if status else "pending"
        return "pending"


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            'id', 'user', 'exercise_name', 'exercise_type', 'duration', 'image_content', 'video_content',
            'intensity', 'calories_burned', 'date', "created_at", "created_by", "updated_at", "updated_by"
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']



class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'value',"created_at", "created_by", "updated_at", "updated_by"]

class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'type', 'question_text', 'options', 'placeholder', 'max_length',"created_at", "created_by", "updated_at", "updated_by"]
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Only include 'placeholder' and 'max_length' for 'description' type
        if instance.type != 'description':
            representation.pop('placeholder', None)
            representation.pop('max_length', None)

        return representation  
class OptionCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False) 
    class Meta:
        model = Option
        fields = '__all__'

# Serializer for creating questions with options
class QuestionCreateSerializer(serializers.ModelSerializer):
    options = OptionCreateSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'category', 'type', 'placeholder', 'max_length', 'options']
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
        for option_data in options_data:
            Option.objects.create(question=question, **option_data)
        
        return question
    
    def update(self, instance, validated_data):
        # Update question fields
        instance.type = validated_data.get('type', instance.type)
        instance.question_text = validated_data.get('question_text', instance.question_text)
        instance.placeholder = validated_data.get('placeholder', instance.placeholder)
        instance.max_length = validated_data.get('max_length', instance.max_length)
        instance.save()

        # Update or create options
        options_data = validated_data.get('options', [])
        current_options = {opt.id: opt for opt in instance.options.all()}
        processed_option_ids = set()

        for option_data in options_data:
            option_id = option_data.get('id')
            option_value = option_data['value']

            if option_id:
                # Update existing option
                option = current_options.get(option_id)
                if option:
                    option.value = option_value
                    option.save()
                    processed_option_ids.add(option.id)
            else:
                # Create new option
                new_option = Option.objects.create(question=instance, value=option_value)
                processed_option_ids.add(new_option.id)

        # Response structure
        updated_options = [
            {"id": opt.id, "value": opt.value} for opt in instance.options.all()
        ]
        return {
            "type": instance.type,
            "question_text": instance.question_text,
            "placeholder": instance.placeholder,
            "max_length": instance.max_length,
            "options": updated_options,
        }
        
class QuestionAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.question_text", read_only=True)
    user_info = serializers.CharField(source="user.username", read_only=True)
    class Meta:
        model = PatientResponse
        fields = ["id", "user", "question", "question_text", "response_text", "user_info", "created_at", "created_by", "updated_at", "updated_by"]
        
        
        
class LabReportSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    class Meta:
        model = LabReport
        fields = ['id', 'patient', 'role', 'report_name', 'report_file', 'date_of_report']        
    
    def get_role(self, obj):
        # Assuming `obj.patient` is related to a user, and user has a 'role' attribute
        user = obj.patient  # or however the relation is set up
        return user.role
    
    def validate_report_file(self, value):
        if not value.name.endswith(('.pdf', '.doc', '.docx', '.txt')):
            raise serializers.ValidationError("Only PDF, DOC, DOCX, or TXT files are allowed.")
        return value