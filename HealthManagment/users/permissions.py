from rest_framework.permissions import BasePermission
from rest_framework import permissions
from django.contrib.auth.models import Permission


def is_superuser_or_admin(user):
    return user.is_superuser or user.is_staff


class PermissionsManager(permissions.BasePermission):

    def has_permission(self, request, view):
        prefixer = ''
        if request.method == 'GET':
            return True
        elif request.method == 'POST':
            prefixer = 'add'
        elif request.method == 'PUT':
            prefixer = 'change'
        elif request.method == 'DELETE':
            prefixer = 'delete'
        elif request.method == 'PATCH':
            prefixer = 'update'
        request_codename = prefixer + '_' + view.codename
        groups = request.user.groups.all()
        for group in groups:
            permissions = Permission.objects.filter(group__name=group.name)
            if permissions.filter(codename=request_codename).exists():
                return True
        return False
    
    
class IsUserProfileOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff


class IsUserAddressOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated is True

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff