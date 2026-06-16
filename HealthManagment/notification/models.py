from django.db import models
from django.conf import settings
from users.models import CustomUser, AuditModel


class Notification(AuditModel):
    NOTIFICATION_TYPES = [
        ("diet", "Diet"),
        ("exercise", "Exercise"),
        ("report", "Report"),
        ("followup", "Follow-up"),
        ("onboarding", "Onboarding"),
        ("general", "General"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)

    is_read = models.BooleanField(default=False)
    extra_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.phone_number} - {self.title}"


class DeviceToken(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="device_tokens"
    )
    token = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.phone_number}"