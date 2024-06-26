# Generated by Django 4.0.4 on 2024-05-20 06:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_alter_patient_health_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='patient',
            old_name='health_status',
            new_name='patient_health_status',
        ),
        migrations.AlterField(
            model_name='patient',
            name='gender',
            field=models.CharField(choices=[('male', 'Male'), ('female', 'Female')], max_length=10),
        ),
    ]
