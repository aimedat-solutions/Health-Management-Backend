from django.db import models
from django.contrib.auth.models import User
from django.conf import settings    
import datetime
import logging
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.utils.crypto import get_random_string
from users.utils import send_otp
from django.core.exceptions import ValidationError


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


class CustomUser(User, AuditModel):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = PhoneNumberField(max_length=15, blank=True, null=True)
    security_code = models.CharField(max_length=120, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    sent = models.DateTimeField(null=True)
    is_first_login = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.role} . {self.phone_number}"
    
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
    

class Patient(AuditModel):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='patient_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10,choices=GENDER_CHOICES)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.user.role}"


class Doctor(AuditModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    specialty = models.CharField(max_length=100)

    def __str__(self):
        return f'Doctor {self.user} - Specialty: {self.specialty}'


class DietPlan(AuditModel):
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="assigned_diets")
    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="created_diets")
    date = models.DateField()
    diet_name = models.CharField(max_length=100)
    time_of_day = models.CharField(max_length=50)  
    meal_plan = models.JSONField()

    def __str__(self):
        return f"{self.diet_name} for {self.patient.first_name} on {self.date}"


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
    QUESTION_TYPES = [
        ('radio', 'Radio'),
        ('checkbox', 'Checkbox'),
        ('description', 'Description'),
    ]
    question_text = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    placeholder = models.CharField(max_length=255, null=True, blank=True)
    max_length = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.question_text


class Option(AuditModel):
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return self.value


class PatientResponse(AuditModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    response_text = models.TextField()

    def __str__(self):
        return f"Answers by {self.user.username}"


class HealthStatus(AuditModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='health_statuses')
    status = models.TextField()

    def __str__(self):
        return f'HealthStatus for {self.user.role} on {self.date}'
