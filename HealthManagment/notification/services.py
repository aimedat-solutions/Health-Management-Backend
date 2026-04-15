import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from .models import Notification, DeviceToken


# ✅ Initialize Firebase (safe)
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("notification/serviceAccountKey.json")
        firebase_admin.initialize_app(cred)


# ✅ Push Notification Sender
def send_push_notification(tokens, title, body, data=None):
    initialize_firebase()

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        tokens=tokens,
        data={str(k): str(v) for k, v in (data or {}).items()}  # Firebase needs string
    )

    response = messaging.send_each_for_multicast(message)

    print("FCM Response:", response.success_count, response.failure_count)
    print("Success:", sum([r.success for r in response.responses]))
    print("Failure:", sum([not r.success for r in response.responses]))

    return response


# ✅ MAIN FUNCTION (USE THIS EVERYWHERE)
def send_notification(user, title, message, n_type="general", data=None):
    """
    Sends notification + saves in DB

    Args:
        user: CustomUser instance
        title: Notification title
        message: Notification message
        n_type: diet / exercise / report / followup / general
        data: dict (extra data for mobile navigation)
    """

    # 1️⃣ Save in DB
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=n_type,
        extra_data=data
    )

    # 2️⃣ Get device tokens
    tokens = DeviceToken.objects.filter(
        user=user,
        is_active=True
    ).values_list("token", flat=True)

    tokens = list(tokens)

    if not tokens:
        print("No device tokens found for user")
        return {"status": "no_tokens"}

    # 3️⃣ Send push
    response = send_push_notification(tokens, title, message, data)

    return {
        "status": "sent",
        "success": response.success_count,
        "failed": response.failure_count
    }