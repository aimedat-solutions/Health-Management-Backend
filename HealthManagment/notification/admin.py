from django.contrib import admin

# Register your models here.
from notification.models import Notification, DeviceToken


admin.site.register(Notification)
admin.site.register(DeviceToken)