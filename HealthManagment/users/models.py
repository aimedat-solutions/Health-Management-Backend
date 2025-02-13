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
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="patient")
    phone_number = PhoneNumberField(max_length=15, blank=True, null=True)
    security_code = models.CharField(max_length=120, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    sent = models.DateTimeField(null=True)
    is_first_login = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.role} . {self.username}"
    
    def save(self, *args, **kwargs):       
        request = kwargs.pop('request', None)  # Extract the request user if passed
        if request:
            if request.user.role == "superadmin" and self.role not in ["admin", "superadmin"]:
                raise ValidationError("SuperAdmin can only create Admin users.")
            elif request.user.role == "admin" and self.role != "doctor":
                raise ValidationError("Admin can only create Doctor users.")

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
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answers by {self.user.username}for question {self.question.pk}"


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
