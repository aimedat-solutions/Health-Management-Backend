from rest_framework import serializers
from users.models import CustomUser, DietPlan

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'phone_number', 'role']

class DietPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietPlan
        fields = '__all__'
























# from rest_framework import serializers
# from django.contrib.auth import authenticate
# from django.contrib.auth import get_user_model
# from phonenumber_field.serializerfields import PhoneNumberField
# from django.contrib.auth.models import Group, Permission
# from users.utils import send_otp, verify_otp
# from users.models import Question, Profile,DietPlan,Exercise, CustomUser, Option, PatientResponse,LabReport
# import re
# User = get_user_model()


# class CustomUserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = ['id', 'username', 'email', 'role', 'phone_number','password']
#         extra_kwargs = {'password': {'write_only': True}}

# class PatientSerializer(serializers.ModelSerializer):
#     user = CustomUserSerializer()

#     class Meta:
#         model = Profile
#         fields = ['id', 'user', 'first_name', 'last_name', 'date_of_birth', 'gender', 'address', "created_at", "created_by", "updated_at", "updated_by"]
        
#     def create(self, validated_data):
#         user_data = validated_data.pop('user')
#         user = User.objects.create(**user_data)
#         patient = Profile.objects.create(user=user, **validated_data)
#         return patient

#     def update(self, instance, validated_data):
#         user_data = validated_data.pop('user')
#         user = instance.user

#         instance.first_name = validated_data.get('first_name', instance.first_name)
#         instance.last_name = validated_data.get('last_name', instance.last_name)
#         instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
#         instance.gender = validated_data.get('gender', instance.gender)
#         instance.address = validated_data.get('address', instance.address)
#         instance.phone_number = validated_data.get('phone_number', instance.phone_number)
#         instance.health_status = validated_data.get('health_status', instance.health_status)
#         instance.save()

#         user.role = user_data.get('role', user.role)
#         user.is_active = user_data.get('is_active', user.is_active)
#         user.is_staff = user_data.get('is_staff', user.is_staff)
#         user.save()

#         return instance
    
# class DoctorRegistrationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = ['id', 'phone_number', 'role']  # Add other fields if required
#         read_only_fields = ['id', 'role'] 

#     def create(self, validated_data):
#         # Set default role as 'doctor'
#         validated_data['role'] = 'doctor'
#         validated_data['username'] = validated_data['phone_number']
#         validated_data['password']=CustomUser.objects.make_random_password()
#         group = Group.objects.get(name=validated_data['role'])
#         user = CustomUser.objects.create(**validated_data)
#         user.groups.add(group)
#         user.save()
#         send_otp(validated_data['phone_number'])
#         return user

# class DietPlanSerializer(serializers.ModelSerializer):
#     meal_plan = serializers.ListField(child=serializers.CharField())
#     class Meta:
#         model = DietPlan
#         fields = ['id', 'patient', 'date', 'diet_name', 'time_of_day', 'meal_plan',"created_at", "created_by", "updated_at", "updated_by"]

#     def create(self, validated_data):
#         request = self.context.get('request')
#         patient = validated_data['patient']
#         doctor = request.user.doctor
#         if patient.doctor != doctor:
#             raise serializers.ValidationError("You can only create diet plans for your own patients.")
#         diet_plan = DietPlan.objects.create(**validated_data)
#         return diet_plan

#     def validate_meal_plan(self, value):
#         if not isinstance(value, list):
#             raise serializers.ValidationError("Meal plan must be a list of items.")
#         return value

# class ExerciseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Exercise
#         fields = [
#             'id', 'user', 'exercise_name', 'exercise_type', 'duration', 
#             'intensity', 'calories_burned', 'date', "created_at", "created_by", "updated_at", "updated_by"
#         ]
#         read_only_fields = ['user', 'created_at', 'updated_at']



# class OptionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Option
#         fields = ['id', 'value',"created_at", "created_by", "updated_at", "updated_by"]

# class QuestionSerializer(serializers.ModelSerializer):
#     options = OptionSerializer(many=True, read_only=True)

#     class Meta:
#         model = Question
#         fields = ['id', 'type', 'question_text', 'options', 'placeholder', 'max_length',"created_at", "created_by", "updated_at", "updated_by"]
    
#     def to_representation(self, instance):
#         representation = super().to_representation(instance)

#         # Only include 'placeholder' and 'max_length' for 'description' type
#         if instance.type != 'description':
#             representation.pop('placeholder', None)
#             representation.pop('max_length', None)

#         return representation  
# class OptionCreateSerializer(serializers.ModelSerializer):
#     id = serializers.IntegerField(required=False) 
#     class Meta:
#         model = Option
#         fields = ['id', 'value']

# # Serializer for creating questions with options
# class QuestionCreateSerializer(serializers.ModelSerializer):
#     options = OptionCreateSerializer(many=True, required=False)

#     class Meta:
#         model = Question
#         fields = ['type', 'question_text', 'placeholder', 'max_length', 'options']
#         extra_kwargs = {
#             'placeholder': {'required': False},  # Make placeholder optional
#             'max_length': {'required': False},   # Make max_length optional
#         }
    
#     def validate(self, data):
#         # Ensure 'placeholder' and 'max_length' are optional but allowed for 'description' type
#         if data['type'] != 'description' and ('placeholder' in data or 'max_length' in data):
#             raise serializers.ValidationError("Only description type questions can have a placeholder or max_length.")
        
#         return data

#     def create(self, validated_data):
#         options_data = validated_data.pop('options', [])
#         question = Question.objects.create(**validated_data)
#         for option_data in options_data:
#             Option.objects.create(question=question, **option_data)
        
#         return question
    
#     def update(self, instance, validated_data):
#         # Update question fields
#         instance.type = validated_data.get('type', instance.type)
#         instance.question_text = validated_data.get('question_text', instance.question_text)
#         instance.placeholder = validated_data.get('placeholder', instance.placeholder)
#         instance.max_length = validated_data.get('max_length', instance.max_length)
#         instance.save()

#         # Update or create options
#         options_data = validated_data.get('options', [])
#         current_options = {opt.id: opt for opt in instance.options.all()}
#         processed_option_ids = set()

#         for option_data in options_data:
#             option_id = option_data.get('id')
#             option_value = option_data['value']

#             if option_id:
#                 # Update existing option
#                 option = current_options.get(option_id)
#                 if option:
#                     option.value = option_value
#                     option.save()
#                     processed_option_ids.add(option.id)
#             else:
#                 # Create new option
#                 new_option = Option.objects.create(question=instance, value=option_value)
#                 processed_option_ids.add(new_option.id)

#         # Response structure
#         updated_options = [
#             {"id": opt.id, "value": opt.value} for opt in instance.options.all()
#         ]
#         return {
#             "type": instance.type,
#             "question_text": instance.question_text,
#             "placeholder": instance.placeholder,
#             "max_length": instance.max_length,
#             "options": updated_options,
#         }
        
# class QuestionAnswerSerializer(serializers.ModelSerializer):
#     question_text = serializers.CharField(source="question.question_text", read_only=True)
#     user_info = serializers.CharField(source="user.username", read_only=True)
#     class Meta:
#         model = PatientResponse
#         fields = ["id", "user", "question", "question_text", "response_text", "user_info", "created_at", "created_by", "updated_at", "updated_by"]
        
        
        
# class LabReportSerializer(serializers.ModelSerializer):
#     role = serializers.SerializerMethodField()
#     class Meta:
#         model = LabReport
#         fields = ['id', 'patient', 'role', 'report_name', 'report_file', 'date_of_report']        
    
#     def get_role(self, obj):
#         # Assuming `obj.patient` is related to a user, and user has a 'role' attribute
#         user = obj.patient  # or however the relation is set up
#         return user.role
    
#     def validate_report_file(self, value):
#         if not value.name.endswith(('.pdf', '.doc', '.docx', '.txt')):
#             raise serializers.ValidationError("Only PDF, DOC, DOCX, or TXT files are allowed.")
#         return value