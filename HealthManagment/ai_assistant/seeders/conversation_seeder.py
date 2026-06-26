"""Seeder for ``Conversation`` records.

Creates realistic conversations with varied statuses and timestamps
for each patient.
"""

import random
from collections.abc import Sequence
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from ai_assistant.enums import ConversationStatus
from ai_assistant.models import AIModel, Conversation
from ai_assistant.seeders.healthcare_data import CONVERSATION_TEMPLATES

User = get_user_model()


def _random_timestamp(days_ago: int) -> datetime:
    """Return a random ``datetime`` within the last *days_ago* days."""
    now = timezone.now()
    offset = timedelta(
        days=random.randint(0, days_ago),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return now - offset


_STATUS_WEIGHTS = {
    ConversationStatus.ACTIVE: 0.40,
    ConversationStatus.PAUSED: 0.15,
    ConversationStatus.RESOLVED: 0.25,
    ConversationStatus.ESCALATED: 0.10,
    ConversationStatus.ARCHIVED: 0.10,
}

_STATUS_CHOICES = list(_STATUS_WEIGHTS.keys())
_STATUS_PROBS = list(_STATUS_WEIGHTS.values())


def seed_conversations(
    patients: Sequence[User],
    models: Sequence[AIModel],
    conversations_per_patient: int = 3,
) -> list[Conversation]:
    """Create *conversations_per_patient* conversations for each patient.

    Each conversation picks a random template from
    ``CONVERSATION_TEMPLATES`` for its title, gets a random status
    (weighted toward ``active``), and a random started/updated timestamp.

    Returns the list of created ``Conversation`` instances.
    """
    conversations: list[Conversation] = []

    for patient in patients:
        for _ in range(conversations_per_patient):
            template = random.choice(CONVERSATION_TEMPLATES)
            title = template["title"].format(patient_name=patient.first_name)
            started = _random_timestamp(days_ago=14)
            updated = started + timedelta(
                minutes=random.randint(5, 120),
            )
            status = random.choices(_STATUS_CHOICES, weights=_STATUS_PROBS, k=1)[0]
            resolved_at = updated if status in (
                ConversationStatus.RESOLVED,
                ConversationStatus.ARCHIVED,
            ) else None

            conv = Conversation.objects.create(
                patient=patient,
                title=title,
                status=status,
                model=random.choice(models) if models else None,
                started_at=started,
                updated_at=updated,
                resolved_at=resolved_at,
                metadata={"source": random.choice(["mobile", "web", "api"])},
            )
            conversations.append(conv)

    return conversations
