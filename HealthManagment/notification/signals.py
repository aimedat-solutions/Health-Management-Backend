from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import LabReport, HealthStatus, CustomUser, DietPlan, PatientDietQuestion, PatientExerciseLog
from .services import send_notification


def get_patient_doctors(patient):
    doctor_ids = DietPlan.objects.filter(
        patient=patient
    ).values_list("doctor", flat=True).distinct()
    return CustomUser.objects.filter(id__in=doctor_ids)


@receiver(post_save, sender=LabReport)
def notify_report(sender, instance, created, **kwargs):
    if created:
        doctors = get_patient_doctors(instance.patient)
        patient_name = instance.patient.profile.first_name or instance.patient.username
        for doctor in doctors:
            send_notification(
                user=doctor,
                title="New Lab Report from Patient",
                message=f"Patient {patient_name} uploaded {instance.report_name}",
                n_type="report"
            )


@receiver(post_save, sender=HealthStatus)
def notify_health_update(sender, instance, created, **kwargs):
    patient_name = instance.patient.profile.first_name or instance.patient.username

    send_notification(
        user=instance.patient,
        title="Health Updated",
        message="Your health status updated",
        n_type="general"
    )

    critical_statuses = ["Critical", "Poor"]
    if instance.health_status in critical_statuses:
        doctors = get_patient_doctors(instance.patient)
        for doctor in doctors:
            send_notification(
                user=doctor,
                title=f"Patient Health: {instance.health_status}",
                message=f"Patient {patient_name} health status is now {instance.health_status}",
                n_type="general",
                data={"patient_id": instance.patient.id, "health_status": instance.health_status}
            )


@receiver(post_save, sender=PatientDietQuestion)
def notify_diet_log(sender, instance, created, **kwargs):
    if created:
        doctors = get_patient_doctors(instance.patient)
        patient_name = instance.patient.profile.first_name or instance.patient.username
        for doctor in doctors:
            send_notification(
                user=doctor,
                title="Diet Log Submitted",
                message=f"Patient {patient_name} submitted diet log for {instance.date}",
                n_type="general",
                data={"patient_id": instance.patient.id, "date": str(instance.date)}
            )


@receiver(post_save, sender=PatientExerciseLog)
def notify_exercise_log(sender, instance, created, **kwargs):
    if created:
        doctors = get_patient_doctors(instance.patient)
        patient_name = instance.patient.profile.first_name or instance.patient.username
        for doctor in doctors:
            send_notification(
                user=doctor,
                title="Exercise Log Submitted",
                message=f"Patient {patient_name} submitted exercise log for {instance.date}",
                n_type="general",
                data={"patient_id": instance.patient.id, "date": str(instance.date)}
            )
