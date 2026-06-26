"""Seeder for test patient and doctor users.

Idempotent — uses ``get_or_create`` by unique ``username`` so that
repeated invocations update existing users instead of creating
duplicates.
"""

from collections.abc import Sequence

from django.contrib.auth import get_user_model

from ai_assistant.seeders.healthcare_data import (
    DOCTOR_FIRST_NAMES,
    DOCTOR_LAST_NAMES,
    PATIENT_FIRST_NAMES,
    PATIENT_LAST_NAMES,
)

User = get_user_model()

_PATIENT_PASSWORD = "testpass123"
_DOCTOR_PASSWORD = "testpass123"


def _make_patient(i: int) -> User:
    """Create or update a single patient user by index."""
    first = PATIENT_FIRST_NAMES[i % len(PATIENT_FIRST_NAMES)]
    last = PATIENT_LAST_NAMES[(i // 10) % len(PATIENT_LAST_NAMES)]
    data = dict(
        role="patient",
        phone_number=f"+9180000{i:04d}",
        first_name=first,
        last_name=last,
        email=f"{first.lower()}.{last.lower()}@example.com",
        is_verified=True,
        is_first_login=False,
    )
    try:
        user = User.objects.get(username=f"patient_{i}")
        for field, value in data.items():
            setattr(user, field, value)
        user.save(update_fields=list(data))
    except User.DoesNotExist:
        user = User(username=f"patient_{i}", **data)
        user.set_password(_PATIENT_PASSWORD)
        user.save()
    return user


def _make_doctor(i: int) -> User:
    """Create or update a single doctor user by index."""
    first = DOCTOR_FIRST_NAMES[i % len(DOCTOR_FIRST_NAMES)]
    last = DOCTOR_LAST_NAMES[(i // 10) % len(DOCTOR_LAST_NAMES)]
    data = dict(
        role="doctor",
        phone_number=f"+9181111{i:04d}",
        first_name=first.replace("Dr. ", ""),
        last_name=last,
        email=f"dr.{last.lower()}@hospital.example.com",
        is_verified=True,
    )
    try:
        user = User.objects.get(username=f"doctor_{i}")
        for field, value in data.items():
            setattr(user, field, value)
        user.save(update_fields=list(data))
    except User.DoesNotExist:
        user = User(username=f"doctor_{i}", **data)
        user.set_password(_DOCTOR_PASSWORD)
        user.save()
    return user


def seed_users(
    patient_count: int = 10,
    doctor_count: int = 5,
) -> tuple[Sequence[User], Sequence[User]]:
    """Create or update *patient_count* patients and *doctor_count* doctors.

    Users are identified by their ``username`` (``patient_0`` …,
    ``doctor_0`` …).  Existing users are updated with fresh name/phone
    data.  Password is only set on creation.

    Returns ``(patients, doctors)`` — two lists of ``User`` instances.
    """
    patients = [_make_patient(i) for i in range(patient_count)]
    doctors = [_make_doctor(i) for i in range(doctor_count)]
    return patients, doctors
