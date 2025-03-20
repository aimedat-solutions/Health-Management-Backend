import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from decouple import config
from users.models import CustomUser

User = get_user_model()

class Command(BaseCommand):
    help = "Create user groups, assign permissions, and create a superadmin user"

    def handle(self, *args, **options):
        """Load roles & permissions dynamically from .env"""
        roles_permissions_json = config("ROLES_PERMISSIONS", default="{}")
        roles_permissions = json.loads(roles_permissions_json)

        if not roles_permissions:
            self.stdout.write(self.style.ERROR("⚠️ No roles defined in .env!"))
            return

        for role, permission_codenames in roles_permissions.items():
            group, _ = Group.objects.get_or_create(name=role)
            self.assign_permissions_to_group(group, permission_codenames)

        # Create Superadmin User
        self.create_superadmin()

    def assign_permissions_to_group(self, group, permission_codenames):
        """Assign permissions to the group dynamically"""
        if permission_codenames == "all":
            permissions = Permission.objects.all()
        else:
            permissions = Permission.objects.filter(codename__in=permission_codenames.split(","))

        if permissions.exists():
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f"✅ Permissions assigned to {group.name} group."))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ No valid permissions found for {group.name}."))

    def create_superadmin(self):
        """Create a superadmin user."""
        username = config("SUPERADMIN_USERNAME", default="superadmin")
        password = config("SUPERADMIN_PASSWORD", default="superadmin")

        superadmin_group, _ = Group.objects.get_or_create(name="superadmin")
        all_permissions = Permission.objects.all()
        superadmin_group.permissions.set(all_permissions)

        user, created = CustomUser.objects.get_or_create(
                username=username,
                email=username,
                role = 'superadmin',
                is_superuser=True,
                is_staff=True
            )
        
        if created:
            user.set_password(password)
            user.save()
            user.groups.add(superadmin_group)
            self.stdout.write(self.style.SUCCESS("✅ Superadmin user created successfully."))
        else:
            self.stdout.write(self.style.WARNING("⚠️ Superadmin user already exists."))
