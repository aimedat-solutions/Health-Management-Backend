from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings    
import datetime
import logging
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.utils.crypto import get_random_string
from users.utils import send_otp
from django.core.exceptions import ValidationError
from .middleware import get_current_user
from datetime import timedelta
from django.utils.timezone import now

class AuditModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)s_set",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)s_set",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from .middleware import get_current_user

        user = get_current_user()
        if not self.pk and not self.created_by:
            self.created_by = user
        self.updated_by = user
        super().save(*args, **kwargs)


class CustomUser(AbstractUser, AuditModel):
    ROLE_CHOICES = [
        ('superadmin', 'SuperAdmin'),
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    ]

    phone_number = PhoneNumberField(unique=True, blank=False, null=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="patient")
    security_code = models.CharField(max_length=6, blank=True, null=True)  # Store OTP
    is_verified = models.BooleanField(default=False)
    sent = models.DateTimeField(null=True)  # OTP sent time
    is_first_login = models.BooleanField(default=True)
    initial_question_completed = models.BooleanField(default=False)  
    last_diet_question_answered = models.DateTimeField(null=True, blank=True)
    
    REQUIRED_FIELDS = ['role']
    
    def __str__(self):
        return f"{self.role} . {self.username}"
    
    def needs_diet_questions(self):
        if self.last_diet_question_answered:
            return now() > self.last_diet_question_answered + timedelta(days=15)
        return True 
    
    def clean(self):
        """ Ensure phone number is provided """
        super().clean()
        if not self.phone_number:
            raise ValidationError("Phone number is required for all users.")
        
    def save(self, *args, **kwargs):
        """ Ensure phone number is always present """
        if not self.phone_number and not self.is_superuser:
            raise ValidationError("Phone number cannot be empty.")
        super().save(*args, **kwargs)
        
    def generate_security_code(self):
        """ Generate a random security code (OTP). """
        token_length = getattr(settings, "TOKEN_LENGTH", 6)
        return get_random_string(token_length, allowed_chars="0123456789")

    def is_security_code_expired(self):
        """ Check if the security code has expired. """
        expiration_date = self.sent + datetime.timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
        return expiration_date <= timezone.now()

    def send_confirmation(self):
        """ Generate and send OTP to the user's phone number. """
        msg91_api_key = settings.MSG91_API_KEY
        msg91_otp_template_id = settings.MSG91_OTP_TEMPLATE_ID

        if all([msg91_api_key, msg91_otp_template_id]):
            try:
                self.security_code = self.generate_security_code()
                self.sent = timezone.now()
                self.save()

                otp_response = send_otp(str(self.phone_number))  # Replace with your OTP sending logic

                if otp_response.get("type") == "success":
                    return True
                else:
                    logging.error(f"Failed to send OTP: {otp_response.get('message')}")
                    return False
            except Exception as e:
                logging.error(f"Error while sending OTP: {e}")
                return False
        else:
            logging.error("MSG91 credentials or OTP template ID are not set")
            return False

    def check_verification(self, security_code):
        """ Check the OTP entered by the user. """
        if security_code == self.security_code:
            if not self.is_security_code_expired():
                self.is_verified = True
                self.security_code = None  # Clear the security code after verification
                self.save()
                return True
            else:
                raise ValidationError({"verification_error": _("OTP has expired. Please request a new OTP.")})
        else:
            raise ValidationError({"verification_error": _("Invalid OTP. Try again.")})
        
        

######################################################################## Excercise Model ################################################################################################


class Exercise(AuditModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='exercises')
    exercise_name = models.CharField(max_length=255)
    exercise_type = models.CharField(max_length=100, choices=[
        ('strength', 'Strength Training'),
        ('cardio', 'Cardio'),
        ('flexibility', 'Flexibility'),
        ('balance', 'Balance'),
    ])
    duration = models.DurationField()  # e.g., how long they did the exercise
    intensity = models.CharField(max_length=50, choices=[
        ('low', 'Low Intensity'),
        ('medium', 'Medium Intensity'),
        ('high', 'High Intensity'),
    ])
    calories_burned = models.PositiveIntegerField()
    date = models.DateField()
    video_content = models.FileField(upload_to='exercise_videos/', null=True, blank=True)
    image_content = models.ImageField(upload_to='exercise_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.exercise_name} by {self.user.username}"


class DoctorExerciseResponse(AuditModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='exercise_responses')
    review = models.TextField()

    def __str__(self):
        return f"Exercise Review by Dr. {self.doctor.username} for {self.user.username}"


class Question(AuditModel):
    QUESTION_CATEGORIES = [
        ("initial", "Initial Question"),
        ("diet", "Diet Question"),
    ]
    QUESTION_TYPES = [
        ('radio', 'Radio'),
        ('checkbox', 'Checkbox'),
        ('description', 'Description'),
    ]
    question_text = models.CharField(max_length=255)
    category = models.CharField(max_length=10, choices=QUESTION_CATEGORIES)
    type = models.CharField(max_length=20, choices=QUESTION_TYPES, null=True, blank=True)
    placeholder = models.CharField(max_length=255, null=True, blank=True)
    max_length = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.category.upper()} - {self.question_text[:50]}"
    
    def save(self, *args, **kwargs):
        """Ensure only 'initial' questions have a type."""
        if self.category == 'diet':
            self.question_type = None  
        super().save(*args, **kwargs)

class Option(AuditModel):
    id = models.AutoField(primary_key=True) 
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return self.value



######################################################################### PATIENT Model #########################################################################################################

class Profile(AuditModel):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10,choices=GENDER_CHOICES,default="female")
    address = models.TextField(null=True, blank=True, help_text="Only for patients")  
    specialization = models.CharField(max_length=255, null=True, blank=True, help_text="Only for doctors")  
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True, help_text="Auto-calculated based on date_of_birth")
    calories = models.PositiveIntegerField(help_text="Daily calorie intake", null=True, blank=True)
    height = models.FloatField(help_text="Height in cm", null=True, blank=True)
    weight = models.FloatField(help_text="Weight in kg", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate age based on date_of_birth
        if self.date_of_birth:
            today = datetime.date.today()
            self.age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class DietPlan(AuditModel):
    patient = models.ForeignKey(CustomUser , on_delete=models.CASCADE, related_name="assigned_diets")
    doctor = models.ForeignKey(CustomUser , on_delete=models.CASCADE, related_name="created_diets")
    date = models.DateField(default=datetime.date.today)
    title = models.CharField(max_length=100)
    blood_sugar_range = models.CharField(max_length=50, choices=[("low", "Low"), ("normal", "Normal"), ("high", "High")])
    meal_time = models.CharField(max_length=50, choices=[("morning", "Morning"), ("afternoon", "Afternoon"), ("evening", "Evening")])
    trimester = models.CharField(max_length=50)
    meal_plan = models.JSONField(help_text="Enter the meal plan in JSON format")
    doctor_comment = models.TextField(blank=True, null=True, verbose_name="Doctor's Comments")

    class Meta:
        unique_together = ("patient", "date")
        
    def __str__(self):
        return f"{self.title} for {self.patient.first_name} on {self.date}"
    
    

class PatientResponse(AuditModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    selected_option = models.ForeignKey(Option, null=True, blank=True, on_delete=models.SET_NULL)
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answers by {self.user.username}for question {self.question.question_text[:30]}"
    
class PatientDietSchedule(models.Model):
    patient = models.OneToOneField(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'patient'})
    last_diet_update = models.DateTimeField(default=timezone.now)

    def is_due_for_update(self):
        return timezone.now() >= self.last_diet_update + timedelta(days=15)
    
    def save(self, *args, **kwargs):
        # Ensure only "patient" users can be assigned
        if self.patient.role != 'patient':
            raise ValueError("Only users with the 'patient' role can have a diet schedule.")
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"Diet Schedule for {self.patient.username}"

class LabReport(AuditModel):
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="lab_reports")
    report_name = models.CharField(max_length=200)
    report_file = models.FileField(upload_to='lab_reports/')
    date_of_report = models.DateField()

    def __str__(self):
        return f"{self.report_name} for {self.patient.first_name} on {self.date_of_report}"

class HealthStatus(AuditModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='health_statuses')
    calories = models.PositiveIntegerField(help_text="Daily calorie intake", null=True, blank=True)
    height = models.FloatField(help_text="Height in cm", null=True, blank=True)
    weight = models.FloatField(help_text="Weight in kg", null=True, blank=True)
    months = models.PositiveIntegerField(help_text="Number of months (e.g., pregnancy tracking)", null=True, blank=True)
    status = models.TextField()

    def __str__(self):
        return f'HealthStatus for {self.user.role} on {self.date}'
