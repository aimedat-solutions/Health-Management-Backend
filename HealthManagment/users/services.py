from django.utils import timezone
from users.models import PatientResponse, ExerciseStatus

def get_trimester(profile):
    if not profile.pregnancy_month:
        return None
    if profile.pregnancy_month <= 3:
        return 1
    elif profile.pregnancy_month <= 6:
        return 2
    return 3


def has_diabetes(patient):
    return PatientResponse.objects.filter(
        user=patient,
        question__question_text__icontains="diabetes",
        response_text__icontains="yes"
    ).exists()


def calculate_step_goal(trimester, diabetes):
    if trimester == 1:
        base = 5000
    elif trimester == 2:
        base = 6000
    else:
        base = 4500

    if diabetes:
        return int(base * 0.85)
    return base


def classify_steps(steps, goal):
    if steps < goal * 0.5:
        return "low"
    elif steps <= goal * 1.1:
        return "safe"
    return "high"


def exercise_completed_today(patient):
    return ExerciseStatus.objects.filter(
        user=patient,
        status="completed",
        exercise__date=timezone.now().date()
    ).exists()


def daily_activity_message(step_status, exercise_done):
    if step_status == "high" and exercise_done:
        return "You have been very active today. Please rest and hydrate."
    if step_status == "low" and not exercise_done:
        return "Short walks after meals may help blood sugar control."
    return "Good balance of activity today."
