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
from dateutil.relativedelta import relativedelta

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
        if not self.pk and not self.created_by and hasattr(self, '_request_user'):
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
    security_code = models.CharField(max_length=6, blank=True, null=True)  # Store OTP
    is_verified = models.BooleanField(default=False)
    sent = models.DateTimeField(null=True)  # OTP sent time
    is_first_login = models.BooleanField(default=True)
    initial_question_completed = models.BooleanField(default=False)  
    last_question_answered_at = models.DateField(null=True, blank=True)
    last_diet_question_answered = models.DateTimeField(null=True, blank=True)
    ask_diet_question = models.BooleanField(default=True) 
    verified = models.BooleanField(default=False)
    welcome_seen = models.BooleanField(default=False)
    app_tour_completed = models.BooleanField(default=False)


    
    REQUIRED_FIELDS = ['role', 'phone_number']
    
    def __str__(self):
        return f"{self.role} . {self.phone_number}"
    
    def is_doctor(self):
        return self.role == RoleChoices.DOCTOR

    def is_patient(self):
        return self.role == RoleChoices.PATIENT
    
    def needs_diet_questions(self):
        """
        Determines if the patient needs to answer diet questions (every 15 days).
        """
        if self.last_diet_question_answered:
            return now() > self.last_diet_question_answered + timedelta(days=settings.DIET_QUESTION_ADD_DAYS)
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
    title = models.CharField(max_length=255)
    description = models.TextField()
    image_content = models.ImageField(upload_to='exercise_images/', null=True, blank=True)
    video_content = models.FileField(upload_to='exercise_videos/', null=True, blank=True)
    
    trimester_min = models.PositiveSmallIntegerField(default=1)
    trimester_max = models.PositiveSmallIntegerField(default=3)
    diabetes_safe = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.title}"

class ExerciseDate(AuditModel):
    """
    Tracks assigned dates for exercises.
    """
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="exercise_dates")
    doctor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='assigned_exercises')
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='patient_exercises')
    date = models.DateField()

    class Meta:
        unique_together = ("doctor", "patient", "exercise", "date")  

    def __str__(self):
        return f"{self.exercise.title} -> {self.patient.username} on {self.date}"
    
    def save(self, *args, **kwargs):
        if self.doctor.role != 'doctor':
            raise ValidationError("Selected doctor must have role 'doctor'")
        if self.patient.role != 'patient':
            raise ValidationError("Selected patient must have role 'patient'")
        super().save(*args, **kwargs)
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
    exercise = models.ForeignKey(ExerciseDate, on_delete=models.CASCADE, related_name="status_entries")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    updated_at = models.DateTimeField(auto_now=True)
    reason_audio = models.FileField(upload_to="exercise/audio/", null=True, blank=True)
    calories_burned = models.FloatField(default=0, null=True, blank=True)


    class Meta:
        unique_together = ("user", "exercise")

    def __str__(self):
        return f"{self.user.username} - {self.exercise.exercise.title}: {self.status}"
    
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
        ("pregnancy_diabetes", "Diabetes in Pregnancy"),
    ]
    QUESTION_TYPES = [
        ('radio', 'Radio'),
        ('checkbox', 'Checkbox'),
        ('description', 'Description'),
    ]
    question_image = models.ImageField(upload_to='questions_images/', null=True, blank=True)
    question_text = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=QUESTION_CATEGORIES)
    type = models.CharField(max_length=20, choices=QUESTION_TYPES, null=True, blank=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='sub_questions',
        on_delete=models.CASCADE
    )
    condition_value = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="If this is a sub-question, answer of parent that triggers it (e.g., 'yes')"
    )
    placeholder = models.CharField(max_length=255, null=True, blank=True)
    max_length = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.category.upper()} - {self.question_text[:50]}"
    
    def save(self, *args, **kwargs):
        """Ensure only 'initial' questions have a type."""
        if self.category == 'other':
            self.question_type = None  
        super().save(*args, **kwargs)

class Option(AuditModel):
    """
    Stores options for multiple-choice questions.
    """
    id = models.AutoField(primary_key=True) 
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    value = models.CharField(max_length=100)
    type = models.CharField( 
        max_length=20,
        choices=[
            ('default', 'Default'),
            ('text', 'Text Input'),
            ('number', 'Number Input'),
        ],
        default='default'
    )
   
    def __str__(self):
        return f"{self.value} - {self.question.question_text[:30]}"

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
    first_name = models.CharField(null=True, blank=True, max_length=100)
    last_name = models.CharField(null=True, blank=True, max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True, choices=GenderChoices.choices,default=GenderChoices.FEMALE)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    address = models.TextField(null=True, blank=True, help_text="Only for patients")  
    specialization = models.CharField(max_length=255, null=True, blank=True, help_text="Only for doctors")  
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    height = models.FloatField(help_text="Height in cm", null=True, blank=True)
    weight = models.FloatField(help_text="Weight in kg", null=True, blank=True)
    blood_pressure = models.JSONField(null=True, blank=True, default=dict, help_text='{"systolic": 120, "diastolic": 80, "unit": "mmHg"}')
    lmp_date = models.DateField(null=True, blank=True, help_text="Last Menstrual Period")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def age(self):
        """Calculate age from date_of_birth."""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @property
    def bmi(self):
        """
        BMI = Weight (kg) / (Height (m))²
        """
        if self.height and self.weight:
            height_m = self.height / 100 
            bmi_value = self.weight / (height_m ** 2)
            return round(bmi_value, 2)
        return None
    
    @property
    def bmi_category(self):
        """
        Returns BMI category based on WHO classification.
        """
        bmi = self.bmi
        if bmi is None:
            return None
        if bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 24.9:
            return "Normal weight"
        elif 25 <= bmi < 29.9:
            return "Overweight"
        else:
            return "Obese"
    
    @property
    def pregnancy_month(self):
        """
        Pregnancy month based on LMP (1–9)
        """
        if self.lmp_date:
            delta_days = (date.today() - self.lmp_date).days
            month = (delta_days // 28) + 1
            return min(month, 9)  # max 9 months
        return None

    @property
    def gestational_age(self):
        """
        Gestational Age (weeks & days) = From LMP to today
        Returns string like '8 weeks 6 days'
        """
        if self.lmp_date:
            delta = date.today() - self.lmp_date
            weeks = delta.days // 7
            days = delta.days % 7
            return f"{weeks} weeks {days} days"
        return None
    
    @property
    def edd(self):
        """Expected Date of Delivery (EDD) = LMP + 9 months + 7 days (standard)."""
        if self.lmp_date:
            return self.lmp_date + relativedelta(months=9, days=7)
        return None
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    

######################################################################## Diet and Meal Model ################################################################################################
class MealPortion(AuditModel):
    """
    Defines meal portion categories for diet plans.
    """
    name = models.CharField(max_length=255)
    calories = models.FloatField(null=True, blank=True)
    protein = models.FloatField(null=True, blank=True)
    carbohydrates = models.FloatField(null=True, blank=True)
    fat = models.FloatField(null=True, blank=True)
    fiber = models.FloatField(null=True, blank=True)
    sugar = models.FloatField(null=True, blank=True)
    saturated_fat = models.FloatField(null=True, blank=True)
    trans_fat = models.FloatField(null=True, blank=True)
    cholesterol = models.FloatField(null=True, blank=True)
    sodium = models.FloatField(null=True, blank=True)
    serving_unit = models.CharField(max_length=100, null=True, blank=True)
    serving_qty = models.FloatField(null=True, blank=True)
    ai_generated = models.BooleanField(default=False)
    
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
    diet_plan = models.ForeignKey(DietPlan, on_delete=models.CASCADE, related_name="meals")
    meal_type = models.CharField(max_length=20, choices=MealType.choices)  
    meal_portions = models.ManyToManyField(MealPortion)
    start_time = models.TimeField(null=True, blank=True, help_text="Start of meal window")
    end_time = models.TimeField(null=True, blank=True, help_text="End of meal window")
    
    def __str__(self):
        return f"{self.meal_type} ({self.start_time}-{self.end_time}) for {self.diet_plan.patient.username}"
    
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
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reason_audio = models.FileField(upload_to="skkiped/audio/",null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("patient", "diet_plan", "date")

    def __str__(self):
        return f"{self.patient.username} - {self.diet_plan.meal_type} on {self.date}: {self.status}"
    
class DietPlanCompletedPortion(AuditModel):
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="completed_portions")
    diet_plan_meal = models.ForeignKey(DietPlanMeal, on_delete=models.CASCADE, related_name="completed_portions")
    portion = models.ForeignKey(MealPortion, on_delete=models.CASCADE, related_name="completed_by_patients")
    date = models.DateField()

    class Meta:
        unique_together = ("patient", "diet_plan_meal", "portion", "date")

    def __str__(self):
        return f"{self.patient.username} ate {self.portion.name} ({self.diet_plan_meal.meal_type}) on {self.date}"


class ExtraMeal(AuditModel):
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="extra_meals")
    diet_plan_meal = models.ForeignKey(DietPlanMeal, on_delete=models.CASCADE, null=True, blank=True, related_name="extra_items")
    date = models.DateField()
    item_name = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(upload_to="extrameal/images/", null=True, blank=True)
    quantity = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    audio_entry = models.FileField(upload_to="extrameal/audio/", null=True, blank=True)  # optional audio

    def __str__(self):
        return f"{self.patient.username} extra meal on {self.date}"
   
class PatientDietQuestion(AuditModel):
    """
    Tracks dietary habits of a patient with optional audio responses.
    """
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'patient'})
    date = models.DateField(default=timezone.now)

    breakfast = models.TextField(null=True, blank=True)
    lunch = models.TextField(null=True, blank=True)
    eveningSnack = models.TextField(null=True, blank=True)
    dinner = models.TextField(null=True, blank=True)

    breakfast_audio = models.FileField(upload_to="diet_questions/audio/", null=True, blank=True)
    lunch_audio = models.FileField(upload_to="diet_questions/audio/", null=True, blank=True)
    eveningSnack_audio = models.FileField(upload_to="diet_questions/audio/", null=True, blank=True)
    dinner_audio = models.FileField(upload_to="diet_questions/audio/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Diet question for {self.patient.username} on {self.date}"


class TimeSlotChoices(models.TextChoices):
    EARLY_MORNING = "EARLY_MORNING", "Early Morning"
    MORNING = "MORNING", "Morning"
    AFTERNOON = "AFTERNOON", "Afternoon"
    EVENING = "EVENING", "Evening"
    NIGHT = "NIGHT", "Night"


class ActivityTypeChoices(models.TextChoices):
    WALKING = "WALKING", "Walking"
    STRETCHING = "STRETCHING", "Stretching"
    SLOW_WALK = "SLOW_WALK", "Slow Walk"
    YOGA = "YOGA", "Yoga"
    BREATHING = "BREATHING", "Breathing"
    LIGHT_EXERCISE = "LIGHT_EXERCISE", "Light Exercise"


class EffortLevelChoices(models.TextChoices):
    EASY = "EASY", "Easy"
    COMFORTABLE = "COMFORTABLE", "Comfortable"
    MODERATE = "MODERATE", "Moderate"
    VIGOROUS = "VIGOROUS", "Vigorous"


class SymptomChoices(models.TextChoices):
    NONE = "NONE", "None"
    BACK_PAIN = "BACK_PAIN", "Back Pain"
    FATIGUE = "FATIGUE", "Fatigue"
    SHORTNESS_OF_BREATH = "SHORTNESS_OF_BREATH", "Shortness of Breath"
    DIZZINESS = "DIZZINESS", "Dizziness"
    SWELLING = "SWELLING", "Swelling"
    CONTRACTIONS = "CONTRACTIONS", "Contractions"
    HEADACHE = "HEADACHE", "Headache"
    NAUSEA = "NAUSEA", "Nausea"


class PatientExerciseLog(AuditModel):
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'patient'})
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Exercise log for {self.patient.username} on {self.date}"


class ExerciseLogEntry(models.Model):
    exercise_log = models.ForeignKey(PatientExerciseLog, on_delete=models.CASCADE, related_name='entries')
    time_slot = models.CharField(max_length=20, choices=TimeSlotChoices.choices)
    activity_type = models.CharField(max_length=30, choices=ActivityTypeChoices.choices)
    duration_minutes = models.PositiveSmallIntegerField()
    effort_level = models.CharField(max_length=20, choices=EffortLevelChoices.choices)
    symptoms = models.JSONField(default=list)
    custom_symptom = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.get_time_slot_display()} - {self.get_activity_type_display()} ({self.duration_minutes}min)"


    ####################################################### LabReport Model ################################################################################################
class LabReport(AuditModel):
    """
    Stores medical reports uploaded by patients.
    """
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="lab_reports")
    report_name = models.CharField(max_length=200)
    report_file = models.FileField(upload_to='lab_reports/')
    date_of_report = models.DateField()

    def __str__(self):
        return f"{self.report_name} for {self.patient.username} on {self.date_of_report}"
    
    
    
######################################################################## Health Status Model ################################################################################################

class HealthStatus(AuditModel):
    """
    Tracks user health parameters over time.
    """
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='health_records')
    blood_pressure = models.CharField(max_length=10, default="120/80")
    calories = models.IntegerField(default=2000)
    points = models.PositiveIntegerField(null=True, blank=True, help_text="Health points")
    bmi = models.FloatField(null=True, blank=True, help_text="Body Mass Index")
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
    
    
class DailyStepCount(AuditModel):
    SOURCE_CHOICES = (
        ("google_fit", "Google Fit"),
        ("apple_health", "Apple Health"),
        ("manual", "Manual"),
    )

    STATUS_CHOICES = (
        ("low", "Low"),
        ("safe", "Safe"),
        ("high", "High"),
    )

    patient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="daily_steps",
        limit_choices_to={"role": "patient"}
    )
    date = models.DateField()
    steps = models.PositiveIntegerField()
    goal_steps = models.PositiveIntegerField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ("patient", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.patient.phone_number} - {self.date} - {self.steps}"
    
    def get_trimester(profile):
        if not profile.pregnancy_month:
            return None
        if profile.pregnancy_month <= 3:
            return 1
        elif profile.pregnancy_month <= 6:
            return 2
        return 3



class AppContent(AuditModel):
    CONTENT_TYPES = [
        ("welcome", "Welcome"),
        ("quote", "Motivational Quote"),
        ("disclaimer", "Disclaimer"),
        ("privacy", "Privacy Policy"),
        ("terms", "Terms & Legal"),
    ]

    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    title = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.content_type
    
class HealthEducation(AuditModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    pdf_file = models.FileField(upload_to="health_education/pdf/")
    order = models.PositiveIntegerField(default=0)
    category = models.CharField(
        max_length=100,
        help_text="nutrition, exercise, insulin, general"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class HelpContent(AuditModel):
    CONTENT_TYPES = [
        ("app_tour", "App Tour"),
        ("user_manual", "User Manual"),
    ]

    screen_name = models.CharField(
        max_length=100,
        help_text="home, diet, exercise, profile, general"
    )
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPES
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    step_order = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["screen_name", "step_order"]

    def __str__(self):
        return f"{self.content_type} | {self.screen_name} | {self.step_order}"

class UserLegalConsent(AuditModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content_type = models.CharField(max_length=20)  # disclaimer/privacy/terms
    version = models.CharField(max_length=20)
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "content_type", "version")
