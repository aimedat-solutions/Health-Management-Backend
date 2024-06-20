from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from decouple import config
from django.contrib.contenttypes.models import ContentType
User = get_user_model()

Group.objects.get_or_create(name='admin')
Group.objects.get_or_create(name='doctor')
Group.objects.get_or_create(name='patient')
permission = Permission.objects.get_or_create(codename='add_admin',
                                              name='add admin',
                                              content_type=ContentType.objects.get_for_model(User))
permission = Permission.objects.get_or_create(codename='change_admin',
                                              name='change admin',
                                              content_type=ContentType.objects.get_for_model(User))
permission = Permission.objects.get_or_create(codename='delete_admin',
                                              name='delete admin',
                                              content_type=ContentType.objects.get_for_model(User))
group = Group.objects.get(name="admin")
superadmin_group = Group.objects.get(name='admin')
superadmin_permissions = Permission.objects.all()
superadmin_group.permissions.set(superadmin_permissions)

admin_group = Group.objects.get(name='doctor')
admin_permissions_codenames = [
    'add_doctor', 'view_doctor',
]
admin_permissions = Permission.objects.filter(
    codename__in=admin_permissions_codenames)
admin_group.permissions.set(admin_permissions)

users_group = Group.objects.get(name='patient')
user_permissions_codenames = [
    'add_patient', 'view_patient',
]
users_permissions = Permission.objects.filter(
    codename__in=user_permissions_codenames)
users_group.permissions.set(users_permissions)


class Command(BaseCommand):
    help = 'Create superadmin user and assign permissions'

    def handle(self, *args, **options):
        username = config('SUPERADMIN_USERNAME', default=None)
        password = config('SUPERADMIN_PASSWORD', default=None)

        if username and password:
            superadmin_group, created = Group.objects.get_or_create(
                name='admin')
            permissions = Permission.objects.all()
            superadmin_group.permissions.set(permissions)
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username=username, is_superuser=True, is_staff=True)
            user.set_password(password)
            user.save()
            user.groups.add(superadmin_group)
            self.stdout.write(self.style.SUCCESS(
                'Superadmin user created successfully.'))