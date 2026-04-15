from django.urls import path
from .views import *

urlpatterns = [
    path("", NotificationListAPI.as_view()),
    path("read/<int:pk>/", MarkNotificationReadAPI.as_view()),
    path("save-token/", SaveDeviceTokenAPI.as_view()),
    
    
    path("test/", TestNotification.as_view()),
]

