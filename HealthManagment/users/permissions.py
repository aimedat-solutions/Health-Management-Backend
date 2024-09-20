from rest_framework.permissions import BasePermission
from rest_framework import permissions
from django.contrib.auth.models import Permission
from rest_framework import permissions
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

def is_superuser_or_admin(user):
    return user.is_superuser or user.is_staff

class PermissionsManager(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated(detail="You are not authenticated. Please log in to access this resource.")

        method_permission_map = {
            'GET': None,   # Allow read access by default
            'POST': 'add',
            'PUT': 'change',
            'DELETE': 'delete',
            'PATCH': 'update',
        }
        prefixer = method_permission_map.get(request.method)
        if prefixer is None:
            return True
        request_codename = f"{prefixer}_{view.codename}"
        user_groups = request.user.groups.all()

        for group in user_groups:
            group_permissions = Permission.objects.filter(group__name=group.name)
            if group_permissions.filter(codename=request_codename).exists():
                return True
        raise PermissionDenied(detail=f"You do not have permission to {prefixer} {view.codename}.")
    
class IsUserProfileOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff


class IsUserAddressOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated is True

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff