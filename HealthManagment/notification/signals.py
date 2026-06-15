from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import LabReport, HealthStatus, CustomUser, DietPlan
from .services import send_notification


@receiver(post_save, sender=LabReport)
def notify_report(sender, instance, created, **kwargs):
    if created:
        # Notify the patient's doctor(s) when a lab report is uploaded
        doctor_ids = DietPlan.objects.filter(
            patient=instance.patient
        ).values_list("doctor", flat=True).distinct()

        for doc_id in doctor_ids:
            doctor = CustomUser.objects.filter(id=doc_id).first()
            if doctor:
                send_notification(
                    user=doctor,
                    title="New Lab Report from Patient",
                    message=f"Patient {instance.patient.profile.first_name or instance.patient.username} uploaded {instance.report_name}",
                    n_type="report"
                )


@receiver(post_save, sender=HealthStatus)
def notify_health_update(sender, instance, created, **kwargs):
    if created:
        send_notification(
            user=instance.patient,
            title="Health Updated",
            message="Your health status updated",
            n_type="general"
        )