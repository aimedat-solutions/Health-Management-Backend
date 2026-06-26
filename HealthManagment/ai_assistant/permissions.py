from rest_framework.permissions import BasePermission


class IsPatientUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "patient")


class IsDoctorUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "doctor")


class IsConversationOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        patient = getattr(obj, "patient", None)
        if patient is None:
            conversation = getattr(obj, "conversation", None)
            if conversation is not None:
                patient = conversation.patient
        return patient == request.user
