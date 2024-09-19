
from django.db import models
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField

class CustomUser(User):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = PhoneNumberField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return f"{self.role} . {self.username}"
    
class Patient(models.Model):
    HEALTH_STATUS = [
        ('bp', 'BP'),
        ('weight', 'Weight'),
        ('bmi', 'BMI'),
        ('diastolic', 'Diastolic'),
    ]
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
    health_status = models.CharField(max_length=15, choices=HEALTH_STATUS)

    def __str__(self):
        return f'Patient {self.pk} : {self.first_name} {self.last_name}'
    
class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialty = models.CharField(max_length=100)

    def __str__(self):
        return f'Doctor {self.user} - Specialty: {self.specialty}'
    
class DietPlan(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='diet_plans')
    date = models.DateField()
    diet_name = models.CharField(max_length=100)
    time_of_day = models.CharField(max_length=50)  # e.g., "7am - 10am"
    meal_plan = models.JSONField()
    
    def __str__(self):
        return f"{self.diet_name} for {self.patient.first_name} on {self.date}"
    
class Exercise(models.Model):
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.exercise_name} by {self.user.username}"
class SectionOneQuestions(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    work_involves_seasonal_activity = models.BooleanField(choices=[(True, 'Yes'), (False, 'No')])
    primary_activity = models.CharField(max_length=255, blank=True, null=True)
    off_seasonal_activity = models.CharField(max_length=255, blank=True, null=True)
    duration_occupation_year_full_time = models.PositiveIntegerField(blank=True, null=True)
    duration_occupation_year_part_time = models.PositiveIntegerField(blank=True, null=True)
    duration_occupation_week_full_time = models.PositiveIntegerField(blank=True, null=True)
    duration_occupation_week_part_time = models.PositiveIntegerField(blank=True, null=True)
    hours_per_day_full_time = models.DurationField(blank=True, null=True)
    hours_per_day_part_time = models.DurationField(blank=True, null=True)
    sitting_full_time = models.DurationField(blank=True, null=True)
    sitting_part_time = models.DurationField(blank=True, null=True)
    standing_full_time = models.DurationField(blank=True, null=True)
    standing_part_time = models.DurationField(blank=True, null=True)
    walking_paces_full_time = models.DurationField(blank=True, null=True)
    walking_paces_part_time = models.DurationField(blank=True, null=True)
    climbing_stairs_full_time = models.DurationField(blank=True, null=True)
    climbing_stairs_part_time = models.DurationField(blank=True, null=True)
    skilled_activities_full_time = models.DurationField(blank=True, null=True)
    skilled_activities_part_time = models.DurationField(blank=True, null=True)
    strenuous_activities_full_time = models.DurationField(blank=True, null=True)
    strenuous_activities_part_time = models.DurationField(blank=True, null=True)
    
class SectionTwoQuestions(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    duration_sleep_and_nap = models.DurationField(null=True)
    personal_care_duration = models.DurationField(null=True)
    cooking_duration = models.DurationField(null=True)
    collecting_water_wood_duration = models.DurationField(null=True)
    non_mechanized_domestic_chores_duration = models.DurationField(null=True)
    climbing_steps_duration = models.DurationField(null=True)

class SectionThreeQuestions(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    self_driving_duration = models.DurationField(null=True)
    commuting_duration = models.DurationField(null=True)
    cycling_duration = models.DurationField(null=True)
    walking_duration = models.DurationField(null=True)

class SectionFourQuestions(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    watching_tv_duration = models.DurationField(null=True)
    chatting_reading_duration = models.DurationField(null=True)
    slow_walking_duration = models.DurationField(null=True)
    shopping_duration = models.DurationField(null=True)
    worship_duration = models.DurationField(null=True)
    playing_musical_instrument_duration = models.DurationField(null=True)
    singing_duration = models.DurationField(null=True)
    others_duration = models.DurationField(null=True)

class SectionFiveQuestions(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    weekend_includes = models.IntegerField(choices=[(1, 'Sunday'), (2, 'Saturday and Sunday')])
    weekend_extra_sleep_duration = models.DurationField(null=True)
    watching_tv_duration = models.DurationField(null=True)
    others_duration = models.DurationField(null=True)
    comments = models.TextField(blank=True)
    
class Question(models.Model):
    SECTION_CHOICES = [
        ('I', 'Physical Activity at Work'),
        ('II', 'Physical Activity – General'),
        ('III', 'Physical Activity - Commutation (Transport)'),
        ('IV', 'Physical Activity - Recreation'),
        ('V', 'Physical Activity - Weekend Recreation'),
    ]

    SECTION_QUESTION_MAPPING = {
        'I': ['1', '2', '3', '4a', '4b', '4c', '5a', '5b', '5c', '6a', '6b', '6c', '7', '7a', '7g', '7b', '7h', '7c', '7i', '7d', '7j', '7e', '7k', '7f', '7l'],
        'II': ['8', '9', '10', '11', '12', '13'],
        'III': ['14', '15', '16', '17'],
        'IV': ['18a', '18b', '18c', '18d', '18e', '18f', '18g', '18h'],
        'V': ['19', '20', '21', '22'],
    }

    QUESTION_CHOICES = [
        ('1', 'Does your work involve Seasonal Activity?'),
        ('2', 'Specify Seasonal / Primary or Full Time Activity / Occupation'),
        ('3', 'Specify Off-Seasonal / Part-time Activity / Occupation'),
        ('4a', 'Indicate your duration of occupation per year'),
        ('4b', 'Seasonal Occupation / Full Time Months / Year'),
        ('4c', 'Off-Seasonal Occupation / Part-Time Months / Year'),
        ('5a', 'Indicate your duration of occupation per Week'),
        ('5b', 'Seasonal Occupation / Full Time Days / Week'),
        ('5c', 'Off-Seasonal Occupation / Part-Time Days / Week'),
        ('6a', 'On an average, how many hours per day do you spend at work place?'),
        ('6b', 'Seasonal Occupation / Full Time Hours : Minutes / Day'),
        ('6c', 'Off-Seasonal Occupation / Part-Time Hours : Minutes / Day'),
        ('7', 'At the work place, how many hours per day do you spend on the following:'),
        ('7a', 'Sitting (Office Work)'),
        ('7g', 'Sitting (Office Work)'),
        ('7b', 'Standing'),
        ('7h', 'Standing'),
        ('7c', 'Walking at varying paces without a load'),
        ('7i', 'Walking at varying paces without a load'),
        ('7d', 'Climbing stairs / Walking uphill'),
        ('7j', 'Climbing stairs / Walking uphill'),
        ('7e', 'Skilled occupational activities - [professional Babysitting –Crèche; driving, tailoring, Laundering, housekeeping etc.,]'),
        ('7k', 'Skilled occupational activities - [professional Babysitting –Crèche; driving, tailoring, Laundering, housekeeping, etc.,]'),
        ('7f', 'An activity more strenuous than walking'),
        ('7l', 'An activity more strenuous than walking'),
        ('8', 'Sleeping (Regular hours of sleep usually at night) plus Nap (short sleep - day time)'),
        ('9', 'Personal care - brushing, Toilet, Showering, Dressing, Hair dressing and Eating (Include all meals, snacks & coffee/tea drinks)'),
        ('10', 'Cooking – (including Pre-preparation of meals, snacks and beverages)'),
        ('11', 'Collecting water/ wood'),
        ('12', 'Non-mechanized domestic chores (sweeping, washing clothes and dishes by hand, baby care, elderly care)'),
        ('13', 'Climbing steps / walking uphill'),
        ('14', 'Self driving – work and other places (car/bike/scooter)'),
        ('15', 'Commuting by bus / auto / pillion rider (to work & other places)'),
        ('16', 'Travel by cycling (excludes cycling as an exercise)'),
        ('17', 'Walking to and fro places (excludes walking as an exercise)'),
        ('18a', 'Watching TV'),
        ('18b', 'Chatting, reading, sitting, listening to music, etc.'),
        ('18c', 'Slow walking'),
        ('18d', 'Shopping'),
        ('18e', 'Going to a worship place'),
        ('18f', 'Playing a musical Instrument'),
        ('18g', 'Singing (as a hobby)'),
        ('18h', 'Others'),
        ('19', 'Week end includes? Sunday 1, Saturday and Sunday 2'),
        ('20', 'Weekend extra night sleep / Nap'),
        ('21', 'List all the extra activities that you do in a typical weekend and are not mentioned in the earlier sections'),
        ('22', 'Others'),
        ('23', 'Comments, (if any)'),
    ]

    section = models.CharField(max_length=20, choices=SECTION_CHOICES)
    question_code = models.CharField(max_length=20, choices=QUESTION_CHOICES, unique=True)
    question_text = models.TextField()
    is_seasonal = models.BooleanField(default=False)
    is_full_time = models.BooleanField(default=False)
    duration_years = models.PositiveIntegerField(blank=True, null=True)
    duration_months = models.PositiveIntegerField(blank=True, null=True)
    duration_weeks = models.PositiveIntegerField(blank=True, null=True)
    hours_per_day = models.DurationField(blank=True, null=True)
    activity_type = models.CharField(max_length=1, choices=[('c', 'Walking'), ('d', 'Climbing'), ('e', 'Skilled'), ('f', 'Strenuous')], blank=True, null=True)
    activity_duration = models.DurationField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class PatientResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class HealthStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='health_statuses')
    status = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'HealthStatus for {self.user.role} on {self.date}'