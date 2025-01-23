from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from decouple import config
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class Command(BaseCommand):
    help = "Create user groups, assign permissions, and create a superadmin user"

    def handle(self, *args, **options):
        # Define Groups
        admin_group, _ = Group.objects.get_or_create(name="admin")
        doctor_group, _ = Group.objects.get_or_create(name="doctor")
        patient_group, _ = Group.objects.get_or_create(name="patient")

        # Map Permissions for Each Group
        admin_permissions_codenames = [
            "add_exercise", "view_exercise", "change_exercise", "delete_exercise",
            "add_dietplan", "view_dietplan", "change_dietplan", "delete_dietplan",
            "add_question", "view_question", "change_question", "delete_question",
            "add_patient", "view_patient", "change_patient", "delete_patient",
            "add_doctor", "view_doctor", "change_doctor", "delete_doctor",
            "add_profile", "view_profile", "change_profile", "delete_profile",
        ]

        doctor_permissions_codenames = [
            "add_dietplan", "view_dietplan", "change_dietplan",
            "view_exercise", "add_exercise", "view_question",
        ]

        patient_permissions_codenames = [
            "view_exercise", "view_dietplan", "add_patientresponse", "view_patientresponse",
        ]

        # Assign Permissions to Groups
        self.assign_permissions_to_group(admin_group, admin_permissions_codenames)
        self.assign_permissions_to_group(doctor_group, doctor_permissions_codenames)
        self.assign_permissions_to_group(patient_group, patient_permissions_codenames)

        # Create Superadmin User
        self.create_superadmin()

    def assign_permissions_to_group(self, group, permission_codenames):
        """Helper method to assign permissions to a group."""
        permissions = Permission.objects.filter(codename__in=permission_codenames)
        group.permissions.set(permissions)
        self.stdout.write(self.style.SUCCESS(f"Permissions assigned to {group.name} group."))

    def create_superadmin(self):
        """Create a superadmin user and assign all permissions."""
        username = config("SUPERADMIN_USERNAME", default="superadmin")
        password = config("SUPERADMIN_PASSWORD", default="admin123")

        if username and password:
            superadmin_group, _ = Group.objects.get_or_create(name="admin")
            all_permissions = Permission.objects.all()
            superadmin_group.permissions.set(all_permissions)

            user, created = User.objects.get_or_create(
                username=username,
                is_superuser=True,
                is_staff=True
            )
            if created:
                user.set_password(password)
                user.save()
                user.groups.add(superadmin_group)
                self.stdout.write(self.style.SUCCESS("Superadmin user created successfully."))
            else:
                self.stdout.write(self.style.WARNING("Superadmin user already exists."))
