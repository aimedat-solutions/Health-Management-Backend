from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification, DeviceToken
from .serializers import NotificationSerializer, DeviceTokenSerializer
from .services import send_notification

class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = Notification.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = NotificationSerializer(data, many=True)
        return Response(serializer.data)


class MarkNotificationReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notif = Notification.objects.get(id=pk, user=request.user)
        notif.is_read = True
        notif.save()
        return Response({"message": "Marked as read"})


class SaveDeviceTokenAPI(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class  = DeviceTokenSerializer

    def post(self, request):
        token = request.data.get("token")

        DeviceToken.objects.update_or_create(
            user=request.user,
            token=token,
            defaults={"is_active": True}
        )

        return Response({"message": "Token saved"})
    
    


class TestNotification(APIView):
    def get(self, request):
        send_notification(
            user=request.user,
            title="Test Notification 🎉",
            message="Your Firebase is working!",
            n_type="general"
        )
        return Response({"msg": "sent"})