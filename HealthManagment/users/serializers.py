from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from .utils import send_otp, verify_otp
from .models import Doctor, Question, Patient, CustomUser, SectionOneQuestions, SectionTwoQuestions, SectionThreeQuestions, SectionFourQuestions, SectionFiveQuestions
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

class CustomUserDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('pk', 'username', 'email', 'role', 'phone_number')
        read_only_fields = ('email',)

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'phone_number','password']
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

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
        
        
        
        
class SectionOneQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionOneQuestions
        fields = '__all__'

class SectionTwoQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionTwoQuestions
        fields = '__all__'

class SectionThreeQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionThreeQuestions
        fields = '__all__'

class SectionFourQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionFourQuestions
        fields = '__all__'

class SectionFiveQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionFiveQuestions
        fields = '__all__'

class CombinedSectionSerializer(serializers.Serializer):
    section_type = serializers.ChoiceField(choices=[
        ('I', 'Physical Activity at Work'),
        ('II', 'Physical Activity – General'),
        ('III', 'Physical Activity - Commutation (Transport)'),
        ('IV', 'Physical Activity - Recreation'),
        ('V', 'Physical Activity - Weekend Recreation'),
    ])
    section_data = serializers.JSONField()

    def create(self, validated_data):
        section_type = validated_data.get('section_type')
        section_data = validated_data.get('section_data')

        if section_type == 'I':
            serializer = SectionOneQuestionsSerializer(data=section_data)
        elif section_type == 'II':
            serializer = SectionTwoQuestionsSerializer(data=section_data)
        elif section_type == 'III':
            serializer = SectionThreeQuestionsSerializer(data=section_data)
        elif section_type == 'IV':
            serializer = SectionFourQuestionsSerializer(data=section_data)
        elif section_type == 'V':
            serializer = SectionFiveQuestionsSerializer(data=section_data)
        else:
            raise serializers.ValidationError("Invalid section type")

        if serializer.is_valid():
            serializer.save()
            return serializer.data
        else:
            raise serializers.ValidationError(serializer.errors)
        
        
    def to_representation(self, instance):
        section_type = self.context.get('section_type')
        
        if section_type == 'I':
            serializer = SectionOneQuestionsSerializer(instance)
        elif section_type == 'II':
            serializer = SectionTwoQuestionsSerializer(instance)
        elif section_type == 'III':
            serializer = SectionThreeQuestionsSerializer(instance)
        elif section_type == 'IV':
            serializer = SectionFourQuestionsSerializer(instance)
        elif section_type == 'V':
            serializer = SectionFiveQuestionsSerializer(instance)
        else:
            raise serializers.ValidationError("Invalid section type")

        return serializer.data