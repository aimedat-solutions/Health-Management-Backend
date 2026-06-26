"""Seeder for ``MessageFeedback`` records.

Creates feedback for a random subset of assistant messages.  Feedback
covers various ratings, categories, and optional comments.
"""

import random
from collections.abc import Sequence

from django.contrib.auth import get_user_model

from ai_assistant.enums import FeedbackCategory
from ai_assistant.models import Message, MessageFeedback
from ai_assistant.seeders.healthcare_data import FEEDBACK_COMMENTS

User = get_user_model()

_RATING_DISTRIBUTION = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5]

_CATEGORIES = [
    FeedbackCategory.HELPFUL,
    FeedbackCategory.HELPFUL,
    FeedbackCategory.HELPFUL,
    FeedbackCategory.INACCURATE,
    FeedbackCategory.CONFUSING,
    FeedbackCategory.INCOMPLETE,
    FeedbackCategory.OTHER,
]


def seed_feedback(
    messages: Sequence[Message],
    patients: Sequence[User],
    probability: float = 0.35,
) -> list[MessageFeedback]:
    """Create feedback for a random subset of assistant messages.

    *probability* controls the fraction of assistant messages that receive
    feedback (default 35 %).  Only one feedback per patient-message pair
    is created (enforced by unique_together).

    Returns the list of created ``MessageFeedback`` instances.
    """
    feedback_list: list[MessageFeedback] = []
    assistant_messages = [m for m in messages if m.role == "assistant"]

    if not assistant_messages:
        return feedback_list

    candidates = random.sample(
        assistant_messages,
        k=max(1, int(len(assistant_messages) * probability)),
    )

    for msg in candidates:
        patient = msg.conversation.patient
        if patient not in patients:
            patient = random.choice(list(patients)) if patients else patient

        rating = random.choice(_RATING_DISTRIBUTION)
        category = random.choice(_CATEGORIES)
        comment = random.choice(FEEDBACK_COMMENTS) if random.random() > 0.4 else ""

        fb, _ = MessageFeedback.objects.get_or_create(
            message=msg,
            patient=patient,
            defaults={
                "rating": rating,
                "category": category,
                "comment": comment,
            },
        )
        feedback_list.append(fb)

    return feedback_list
