from celery import shared_task
from django.utils.timezone import now
from users.models import DietPlanMeal, DietPlanDate, ExerciseDate
from .services import send_notification


@shared_task
def send_meal_notifications():
    current_time = now().time()

    meals = DietPlanMeal.objects.filter(
        start_time__lte=current_time,
        end_time__gte=current_time
    )

    for meal in meals:
        patient = meal.diet_plan.patient

        send_notification(
            user=patient,
            title="Meal Reminder 🍽️",
            message=f"It's time for {meal.meal_type}",
            n_type="diet"
        )


@shared_task
def daily_diet_reminder():
    today = now().date()

    diet_dates = DietPlanDate.objects.filter(date=today)

    for d in diet_dates:
        patient = d.diet_plan.patient

        send_notification(
            user=patient,
            title="Today's Diet Plan",
            message="Check your diet plan for today",
            n_type="diet"
        )


@shared_task
def exercise_reminder():
    today = now().date()

    exercises = ExerciseDate.objects.filter(date=today)

    for ex in exercises:
        send_notification(
            user=ex.patient,
            title="Exercise Reminder 🏃",
            message=f"Do your exercise: {ex.exercise.title}",
            n_type="exercise"
        )