"""HealthManagment URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from users.views import ( 
 SendOrResendSMSAPIView,
 ProfileAPIView,  
 CustomLoginView,UserRegistrationAPIView,LogoutAPIView,
)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path("home/", TemplateView.as_view(template_name="index.html")),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('request-otp/', SendOrResendSMSAPIView.as_view(), name='send-sms'),
    path('verify-otp/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('admin-panel/', include('users.urls')),
    path('profile/', ProfileAPIView.as_view(), name='profile-api'),
    path('doctor/', include('doctor.urls')),
    path('patient/', include('patient.urls')), 
]
