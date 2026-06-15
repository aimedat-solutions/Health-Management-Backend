from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Notification, DeviceToken
from .serializers import NotificationSerializer, DeviceTokenSerializer
from .services import send_notification
from users.filters import NotificationFilter

class NotificationListAPI(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = NotificationFilter

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by("-created_at")


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