"""Seeder for ``DoctorReview`` records.

Creates doctor reviews for a subset of conversations that have been
escalated or resolved, with realistic statuses and clinical notes.
"""

import random
from collections.abc import Sequence

from django.contrib.auth import get_user_model
from django.utils import timezone

from ai_assistant.enums import ConversationStatus, ReviewStatus
from ai_assistant.models import Conversation, DoctorReview
from ai_assistant.seeders.healthcare_data import DOCTOR_REVIEW_NOTES

User = get_user_model()

_REVIEW_STATUS_WEIGHTS: dict[str, float] = {
    ReviewStatus.REQUESTED: 0.15,
    ReviewStatus.IN_REVIEW: 0.20,
    ReviewStatus.APPROVED: 0.40,
    ReviewStatus.REJECTED: 0.10,
    ReviewStatus.NEEDS_REVISION: 0.15,
}


def seed_reviews(
    conversations: Sequence[Conversation],
    doctors: Sequence[User],
    probability: float = 0.3,
) -> list[DoctorReview]:
    """Create doctor reviews for a random subset of conversations.

    Only conversations in ``ESCALATED`` or ``RESOLVED`` states are
    eligible.  *probability* controls the fraction (default 30 %).

    Reviews are assigned the first available doctor; when all doctors
    have a review for a conversation the review is skipped.

    Returns the list of created ``DoctorReview`` instances.
    """
    reviews: list[DoctorReview] = []

    eligible = [
        c for c in conversations
        if c.status in (ConversationStatus.ESCALATED, ConversationStatus.RESOLVED)
    ]

    if not eligible:
        return reviews

    candidates = random.sample(
        eligible,
        k=max(1, int(len(eligible) * probability)),
    )

    statuses = list(_REVIEW_STATUS_WEIGHTS.keys())
    weights = list(_REVIEW_STATUS_WEIGHTS.values())

    for conv in candidates:
        doctor = random.choice(list(doctors))
        status = random.choices(statuses, weights=weights, k=1)[0]

        terminal_statuses = {ReviewStatus.APPROVED, ReviewStatus.REJECTED}
        reviewed_at = (
            timezone.now() - timezone.timedelta(hours=random.randint(1, 48))
            if status in terminal_statuses
            else None
        )

        notes_category = {
            ReviewStatus.APPROVED: "approved",
            ReviewStatus.REJECTED: "rejected",
            ReviewStatus.NEEDS_REVISION: "needs_revision",
        }.get(status, "approved")

        notes = random.choice(DOCTOR_REVIEW_NOTES.get(notes_category, DOCTOR_REVIEW_NOTES["approved"]))

        try:
            review = DoctorReview.objects.create(
                conversation=conv,
                doctor=doctor,
                status=status,
                notes=notes,
                reviewed_at=reviewed_at,
            )
            reviews.append(review)
        except Exception:
            continue

    return reviews
