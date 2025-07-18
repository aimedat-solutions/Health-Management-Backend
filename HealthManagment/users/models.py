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
from datetime import timedelta, date
from django.utils.timezone import now

######################################################################## Custom User Model ################################################################################################
class AuditModel(models.Model):
    """
    Abstract model to track creation & update details of an object.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
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
        """ Automatically set created_by & updated_by fields. """
        user = get_current_user()
        if not self.pk and not self.created_by:
            self.created_by = user
        self.updated_by = user
        super().save(*args, **kwargs)
        
        
class RoleChoices(models.TextChoices):
    SUPERADMIN = "superadmin", "SuperAdmin"
    ADMIN = "admin", "Admin"
    DOCTOR = "doctor", "Doctor"
    PATIENT = "patient", "Patient"

class CustomUser(AbstractUser, AuditModel):
    """
    Custom User Model with phone authentication & role-based access.
    """
    phone_number = PhoneNumberField(unique=True, blank=False, null=False)
    role = models.CharField(max_length=10, choices=RoleChoices.choices, default=RoleChoices.PATIENT)
    assigned_doctor = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_patients", limit_choices_to={"role": RoleChoices.DOCTOR},)
    security_code = models.CharField(max_length=6, blank=True, null=True)  # Store OTP
    is_verified = models.BooleanField(default=False)
    sent = models.DateTimeField(null=True)  # OTP sent time
    is_first_login = models.BooleanField(default=True)
    initial_question_completed = models.BooleanField(default=False)  
    last_diet_question_answered = models.DateTimeField(null=True, blank=True)
    ask_diet_question = models.BooleanField(default=True) 

    
    REQUIRED_FIELDS = ['role', 'phone_number']
    
    def __str__(self):
        return f"{self.role} . {self.username}"
    
    def is_doctor(self):
        return self.role == RoleChoices.DOCTOR

    def is_patient(self):
        return self.role == RoleChoices.PATIENT
    
    def needs_diet_questions(self):
        """
        Determines if the patient needs to answer diet questions (every 15 days).
        """
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
        """
        Generates & sends OTP via MSG91 API.
        Returns True if OTP is sent successfully, else False.
        """
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
    """
    Stores information about different exercises performed by a patient user.
    """
    class ExerciseType(models.TextChoices):
        STRENGTH = 'strength', 'Strength Training'
        CARDIO = 'cardio', 'Cardio'
        FLEXIBILITY = 'flexibility', 'Flexibility'
        BALANCE = 'balance', 'Balance'

    class IntensityLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='exercises')
    exercise_name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=ExerciseType.choices)
    duration = models.DurationField()  # e.g., how long they did the exercise
    intensity = models.CharField(max_length=50, choices=IntensityLevel.choices)
    calories_burned = models.PositiveIntegerField()
    date = models.DateField()
    video_content = models.FileField(upload_to='exercise_videos/', null=True, blank=True)
    image_content = models.ImageField(upload_to='exercise_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.exercise_name} by {self.user.username}"

class ExerciseStatus(AuditModel):
    """
    Tracks the status of exercises completed, skipped, or pending.
    """
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("skipped", "Skipped"),
        ("pending", "Pending"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="exercise_statuses")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="status_entries")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    updated_at = models.DateTimeField(auto_now=True)
    reason_audio = models.BinaryField(blank=True, null=True)  # Store audio in binary format

    class Meta:
        unique_together = ("user", "exercise")

    def __str__(self):
        return f"{self.user.username} - {self.exercise.exercise_name}: {self.status}"
    
class DoctorExerciseResponse(AuditModel):
    """
    Doctor's response to a patient's exercise performance.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='exercise_responses')
    review = models.TextField()

    def __str__(self):
        return f"Exercise Review by Dr. {self.doctor.username} for {self.user.username}"
    

######################################################################## Question Model ################################################################################################
class Question(AuditModel):
    """
    Stores various health-related questions.
    """
    QUESTION_CATEGORIES = [
        ("initial", "Initial Question"),
        ("other", "Others"),
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
    """
    Stores options for multiple-choice questions.
    """
    id = models.AutoField(primary_key=True) 
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return self.value

class PatientResponse(AuditModel):
    """
    Stores patients' responses to various health questions.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='answer_responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='question_responses')
    selected_option = models.ForeignKey(Option, null=True, blank=True, on_delete=models.SET_NULL)
    response_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answers by {self.user.username}for question {self.question.question_text[:30]}"

######################################################################### Profile Model #########################################################################################################

class Profile(AuditModel):
    class GenderChoices(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10,choices=GenderChoices.choices,default=GenderChoices.FEMALE)
    address = models.TextField(null=True, blank=True, help_text="Only for patients")  
    specialization = models.CharField(max_length=255, null=True, blank=True, help_text="Only for doctors")  
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True, help_text="Auto-calculated based on date_of_birth")
    calories = models.PositiveIntegerField(help_text="Daily calorie intake", null=True, blank=True)
    height = models.FloatField(help_text="Height in cm", null=True, blank=True)
    weight = models.FloatField(help_text="Weight in kg", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def age(self):
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    

######################################################################## Diet and Meal Model ################################################################################################
class MealPortion(AuditModel):
    """
    Defines meal portion categories for diet plans.
    """
    name = models.CharField(max_length=255) 
    
    def __str__(self):
        return self.name
    
class DietPlan(AuditModel):
    """
    Stores diet plan assigned to patients by doctors.
    """
    patient = models.ForeignKey(CustomUser , on_delete=models.CASCADE, related_name="assigned_diets")
    doctor = models.ForeignKey(CustomUser , on_delete=models.CASCADE, related_name="created_diets")
        
    def __str__(self):
        return f"Diet Plan for {self.patient}"

class DietPlanDate(AuditModel):
    """
    Tracks assigned dates for diet plans.
    """
    diet_plan = models.ForeignKey(DietPlan, on_delete=models.CASCADE, related_name="diet_dates")
    date = models.DateField()

    class Meta:
        unique_together = ("diet_plan", "date")  

    def __str__(self):
        return f"{self.diet_plan.patient} - {self.date}"

class DietPlanMeal(models.Model):
    """
    Stores meal details within a diet plan.
    """
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACKS = "snacks", "Snacks"
    diet_plan = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="meals")
    meal_type = models.CharField(max_length=20, choices=MealType.choices)  
    meal_portions = models.ManyToManyField(MealPortion)

    def __str__(self):
        return f"{self.meal_type} for {self.diet_plan.username}"
    
class DietPlanStatus(AuditModel):
    """
    Tracks the completion status of diet plans.
    """
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("skipped", "Skipped"),
        ("pending", "Pending"),
    ]

    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="diet_statuses")
    diet_plan = models.ForeignKey(DietPlanMeal, on_delete=models.CASCADE, related_name="status_entries")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reason_audio = models.BinaryField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("patient", "diet_plan")

    def __str__(self):
        return f"{self.patient.first_name} - {self.diet_plan.MealType}: {self.status}"
   
class PatientDietQuestion(AuditModel):
    """
    Tracks dietary habits of a patient.
    """
    patient = models.OneToOneField(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'patient'})
    breakfast = models.TextField(null=True, blank=True)
    lunch = models.TextField(null=True, blank=True)
    eveningSnack = models.TextField(null=True, blank=True)
    dinner = models.TextField(null=True, blank=True)
    mms = models.CharField(max_length=10, null=True, blank=True)
    preBreakfast = models.TextField(null=True, blank=True)
    last_diet_update = models.DateField(auto_now=True)

    def __str__(self):
        return f"Diet question for {self.patient.username} on {self.last_diet_update}"
    
    def is_due_for_update(self):
        return self.last_diet_update and timezone.now().date() >= self.last_diet_update + timedelta(days=int(settings.DIET_QUESTION_ADD_DAYS))
    

######################################################################## LabReport Model ################################################################################################
class LabReport(AuditModel):
    """
    Stores medical reports uploaded by patients.
    """
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="lab_reports")
    report_name = models.CharField(max_length=200)
    report_file = models.FileField(upload_to='lab_reports/')
    date_of_report = models.DateField()

    def __str__(self):
        return f"{self.report_name} for {self.patient.first_name} on {self.date_of_report}"
    
    
    
######################################################################## Health Status Model ################################################################################################

class HealthStatus(AuditModel):
    """
    Tracks user health parameters over time.
    """
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='health_records')
    blood_pressure = models.CharField(max_length=10, default="120/80")
    calories = models.IntegerField(default=2000)
    month = models.IntegerField(default=0)
    weight = models.CharField(max_length=10, default="60 KG")
    height = models.CharField(max_length=10, default="165 CM")
    points = models.PositiveIntegerField(null=True, blank=True, help_text="Health points")
    bmi = models.FloatField(default=22.0)
    blood_sugar = models.CharField(max_length=20, default="98 mg/dL")
    Colestrol = models.CharField(max_length=20, default="180 mg/dL")
    diet_followed = models.CharField(max_length=10, default="50%")
    exercise_followed = models.CharField(max_length=10, default="50%")
    point = models.PositiveIntegerField(null=True, blank=True, help_text="Health point")
    diet_streak = models.CharField(max_length=10, default="0 Days")
    exercise_streak = models.CharField(max_length=10, default="0 Days")
    health_status = models.CharField(max_length=20, default="Good")

    def __str__(self):
        return f'HealthStatus for {self.patient.role}'
