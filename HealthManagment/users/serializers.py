from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from phonenumber_field.serializerfields import PhoneNumberField
from django.contrib.auth.models import Group, Permission
from .utils import send_otp, verify_otp
from .models import ( DailyStepCount,Question, Profile,DietPlan,Exercise, CustomUser, Option, PatientResponse,
                    LabReport,DietPlanStatus,ExerciseDate,AppContent,UserLegalConsent,HealthEducation,HelpContent
                    )
import re,os
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError
from django.utils.crypto import get_random_string
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    
    phone_number = PhoneNumberField(required=False)

    class Meta:
        model = CustomUser
        fields = ('role', 'phone_number')

    def validate_phone_number(self, value):
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
            send_otp(str(phone_number))
            print(send_otp)
        
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    phone_number = PhoneNumberField(required=False)
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
                response = verify_otp(str(phone_number), otp)
                if response['type'] != 'success':
                    raise serializers.ValidationError("OTP verification failed.")
            else:
                # In non-production environments, verify with random OTP `1234`
                if otp != '123456':
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
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    specialization = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = (
            'pk',
            'username',
            'email',
            'role',
            'first_name',
            'last_name',
            'specialization',
            "verified",
            "is_verified",
            "initial_question_completed",
            "ask_diet_question",
            'phone_number',
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        )

    def get_first_name(self, obj):
        return getattr(obj.profile, "first_name", None)

    def get_last_name(self, obj):
        return getattr(obj.profile, "last_name", None)
    
    def get_specialization(self, obj):
        # ✅ only for doctors
        if obj.role != "doctor":
            return None

        profile = getattr(obj, "profile", None)
        return getattr(profile, "specialization", None) if profile else None
    
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'phone_number','password']
        extra_kwargs = {'password': {'write_only': True}}


class ProfileSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='user.role', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    verified = serializers.BooleanField(source='user.verified', read_only=True)
    lmp_date = serializers.DateField(required=False, allow_null=True) 
    blood_pressure = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    pregnancy_details = serializers.SerializerMethodField()
    class Meta:
        model = Profile
        fields = [
            'id', 'role', 'phone_number', 'email', 'first_name', 'last_name', 'profile_image', 'date_of_birth', 'age', 'gender', 'occupation',
            'address', 'specialization', 'height', 'weight', 'blood_pressure', 'verified',
            'lmp_date', 'pregnancy_details',
        ]
    
    def get_pregnancy_details(self, obj):
        return {
            "bmi": obj.bmi or "Not available",
            "bmi_category": obj.bmi_category or "Not available",
            "gestational_age": obj.gestational_age,
            "edd": obj.edd,
            "month": obj.pregnancy_month
        }
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request', None)

        if instance.profile_image and request is not None:
            data['profile_image'] = request.build_absolute_uri(instance.profile_image.url)
        else:
            data['profile_image'] = None

        # Hide specialization if not doctor
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.role != 'doctor':
                data.pop('specialization', None)
        else:
            data.pop('specialization', None)
        return data
class DoctorRegistrationSerializer(serializers.ModelSerializer):
    phone_number = PhoneNumberField()

    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number']  # Include only relevant fields
        read_only_fields = ['id', 'role']

    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        phone_number = validated_data.get('phone_number')
        environment = os.getenv('DJANGO_ENV', 'development')

        try:
            user = CustomUser.objects.get(phone_number=phone_number)
            print(user)
            if environment in ['production', 'staging']:
                send_otp(str(phone_number))
                self.context['otp_sent'] = True
            else:
                self.context['otp_sent'] = False

            return user

        except CustomUser.DoesNotExist:
            # Registration flow
            validated_data['role'] = 'doctor'
            base_username = slugify(str(phone_number))
            username = base_username
            suffix = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}_{suffix}"
                suffix += 1

            validated_data['username'] = username
            user = CustomUser.objects.create(**validated_data)
            random_password = get_random_string(length=8)
            user.set_password(random_password)
            user.save()

            # Assign to doctor group
            doctor_group = Group.objects.get(name='doctor')
            user.groups.add(doctor_group)

            # Create profile if not exists
            Profile.objects.get_or_create(user=user)

            # Send OTP in allowed envs
            if environment in ['production', 'staging']:
                send_otp(str(phone_number))
                self.context['otp_sent'] = True
            else:
                self.context['otp_sent'] = False

            return user
        
class DietPlanStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlanStatus
        fields = "__all__"
        
class DietPlanSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    meal_plan = serializers.JSONField()
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
       diabetes_safe = serializers.BooleanField(read_only=True)
       class Meta:
        model = Exercise
        fields = [
            'id', 'title', 'image_content', 'description', 'video_content',
            "created_at", "created_by", "diabetes_safe", "updated_at", "updated_by"
        ]
        read_only_fields = ['created_at', 'updated_at']

class ExerciseDateSerializer(serializers.ModelSerializer):
    exercise_details = ExerciseSerializer(source="exercise", read_only=True)
    class Meta:
        model = ExerciseDate
        fields = [
            "id",
            "date",
            
            "exercise_details"
        ]
        
        
class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'value', 'type'] 

class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)
    sub_questions = serializers.SerializerMethodField()
    question_image = serializers.SerializerMethodField()
    class Meta:
        model = Question
        fields = ['id', 'question_image', 'question_text', 'category', 'type', 'parent', 'condition_value', 'placeholder', 'max_length', 'options', 'sub_questions']
        
    def get_question_image(self, obj):
        request = self.context.get('request')
        if obj.question_image and request:
            return request.build_absolute_uri(obj.question_image.url)
        return None
        
    def get_sub_questions(self, obj):
        return QuestionSerializer(obj.sub_questions.all(), many=True, context=self.context).data
        
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
    sub_questions = serializers.ListSerializer(
        child=serializers.DictField(), required=False
    )

    class Meta:
        model = Question
        fields = ['id', 'question_image', 'question_text', 'category', 'type', 'parent', 'condition_value', 'placeholder', 'max_length', 'options', 'sub_questions']
        extra_kwargs = {
            'placeholder': {'required': False},  
            'max_length': {'required': False},   
            'parent': {'required': False},
            'condition_value': {'required': False}
        }
    
    def validate(self, data):
        if data['type'] != 'description' and ('placeholder' in data or 'max_length' in data):
            raise serializers.ValidationError("Only description type questions can have a placeholder or max_length.")
        
        return data

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        sub_questions_data = validated_data.pop('sub_questions', [])

        question = Question.objects.create(**validated_data)

        for option_data in options_data:
            Option.objects.create(question=question, **option_data)

        self._create_sub_questions(question, sub_questions_data)

        return question

    def _create_sub_questions(self, parent_question, sub_questions_data):
        for sub_data in sub_questions_data:
            options_data = sub_data.pop('options', [])
            nested_sub_questions = sub_data.pop('sub_questions', [])

            sub_question = Question.objects.create(
                parent=parent_question,
                **sub_data
            )

            for option_data in options_data:
                Option.objects.create(question=sub_question, **option_data)

            if nested_sub_questions:
                self._create_sub_questions(sub_question, nested_sub_questions)

    
    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', [])
        sub_questions_data = validated_data.pop('sub_questions', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        instance.options.all().delete()
        for option_data in options_data:
            Option.objects.create(question=instance, **option_data)

        instance.sub_questions.all().delete()
        self._create_sub_questions(instance, sub_questions_data)

        return instance
        
class QuestionAnswerSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    user_info = ProfileSerializer(source="user.profile", read_only=True)
    selected_option = OptionSerializer(read_only=True)
    class Meta:
        model = PatientResponse
        fields = ["id", "user", "questions", "selected_option", "response_text", "user_info", "created_at", "created_by", "updated_at", "updated_by"]
        
    def get_questions(self, obj):
        return QuestionSerializer(obj.question, context=self.context).data

class DoctorQuestionResponseSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(source="question.id")
    question_text = serializers.CharField(source="question.question_text")
    question_image = serializers.SerializerMethodField()
    category = serializers.CharField(source="question.category")
    type = serializers.CharField(source="question.type")
    options = OptionSerializer(many=True, source="question.options", read_only=True)
    selected_option = OptionSerializer(read_only=True)
    response_text = serializers.CharField()
    answered_at = serializers.DateTimeField(source="created_at")
    sub_questions = serializers.SerializerMethodField()

    def get_question_image(self, obj):
        request = self.context.get('request')
        if obj.question.question_image and request:
            return request.build_absolute_uri(obj.question.question_image.url)
        return None

    def get_sub_questions(self, obj):
        sub_responses = self.context.get('sub_responses', {}).get(obj.question.id, [])
        return [
            {
                "question_id": sr.question.id,
                "question_text": sr.question.question_text,
                "question_image": self.get_question_image(sr),
                "category": sr.question.category,
                "type": sr.question.type,
                "options": OptionSerializer(sr.question.options.all(), many=True).data,
                "selected_option": OptionSerializer(sr.selected_option).data if sr.selected_option else None,
                "response_text": sr.response_text,
                "answered_at": sr.created_at,
            }
            for sr in sub_responses
        ]

class DoctorPatientResponseSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    patient_name = serializers.CharField()
    phone_number = serializers.CharField()
    responses = DoctorQuestionResponseSerializer(many=True)
        
        
        
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
    

class AppContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppContent
        fields = ["id", "content_type", "title", "body", "is_active"]
        
class LegalConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLegalConsent
        fields = ["content_type", "version"]

    def validate(self, data):
        user = self.context["request"].user

        # Prevent duplicate acceptance of same version
        if UserLegalConsent.objects.filter(
            user=user,
            content_type=data["content_type"],
            version=data["version"]
        ).exists():
            raise serializers.ValidationError(
                "Consent already accepted for this version."
            )

        return data

class HealthEducationSerializer(serializers.ModelSerializer):
    pdf_file = serializers.SerializerMethodField()

    class Meta:
        model = HealthEducation
        fields = "__all__"

    def get_pdf_file(self, obj):
        request = self.context.get("request")
        if obj.pdf_file:
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None

class HelpContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpContent
        fields = "__all__"


class StepSyncSerializer(serializers.Serializer):
    date = serializers.DateField()
    steps = serializers.IntegerField(min_value=0)
    source = serializers.ChoiceField(
        choices=["google_fit", "apple_health", "manual"]
    )


class DailyStepSerializer(serializers.ModelSerializer):
    message = serializers.CharField(read_only=True)

    class Meta:
        model = DailyStepCount
        fields = [
            "date",
            "steps",
            "goal_steps",
            "status",
            "message",
        ]
