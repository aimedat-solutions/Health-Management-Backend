from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import LabReport, HealthStatus
from .services import send_notification


@receiver(post_save, sender=LabReport)
def notify_report(sender, instance, created, **kwargs):
    if created:
        send_notification(
            user=instance.patient,
            title="New Lab Report",
            message=f"{instance.report_name} uploaded",
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