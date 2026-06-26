from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError as DjangoDatabaseError, IntegrityError

from ai_assistant.domain.entities.conversation import MessageFeedbackEntity
from ai_assistant.domain.interfaces.repositories import FeedbackRepository
from ai_assistant.exceptions import DatabaseError
from ai_assistant.models import MessageFeedback


class DjangoFeedbackRepository(FeedbackRepository):
    """Django ORM implementation of ``FeedbackRepository``.

    Uses upsert semantics via ``update_or_create`` — a patient may only
    have one feedback entry per message.  If an entry already exists, the
    existing record is updated instead of raising a duplicate-key error.
    """

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _to_entity(instance: MessageFeedback) -> MessageFeedbackEntity:
        return MessageFeedbackEntity(
            id=instance.id,
            message_id=instance.message_id,
            patient_id=instance.patient_id,
            rating=instance.rating,
            category=instance.category or "",
            comment=instance.comment or "",
            created_at=instance.created_at,
        )

    @staticmethod
    def _apply_from_entity(
        entity: MessageFeedbackEntity,
        instance: Optional[MessageFeedback] = None,
    ) -> MessageFeedback:
        if instance is None:
            instance = MessageFeedback()
        instance.message_id = entity.message_id
        instance.patient_id = entity.patient_id
        instance.rating = entity.rating
        instance.category = entity.category
        instance.comment = entity.comment
        return instance

    # -- Read --------------------------------------------------------------

    def get_by_message_and_patient(
        self, message_id: int, patient_id: int
    ) -> Optional[MessageFeedbackEntity]:
        try:
            instance = MessageFeedback.objects.get(
                message_id=message_id, patient_id=patient_id
            )
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error fetching feedback for message {message_id}, patient {patient_id}"
            ) from exc
        return self._to_entity(instance)

    def get_by_message(self, message_id: int) -> Optional[MessageFeedbackEntity]:
        """Return the feedback entry for a message (if one exists).

        Note: if multiple patients could rate the same message this would
        be ambiguous.  In the current model, feedback is per (message, patient),
        so this convenience method returns the first entry found.
        """
        try:
            instance = MessageFeedback.objects.filter(message_id=message_id).first()
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error fetching feedback for message {message_id}"
            ) from exc
        if instance is None:
            return None
        return self._to_entity(instance)

    # -- Write -------------------------------------------------------------

    def upsert(self, entity: MessageFeedbackEntity) -> MessageFeedbackEntity:
        """Create or update feedback for ``(message, patient)``.

        Uses ``update_or_create`` under the hood — no need for a separate
        existence check in the service layer.
        """
        try:
            instance, _created = MessageFeedback.objects.update_or_create(
                message_id=entity.message_id,
                patient_id=entity.patient_id,
                defaults={
                    "rating": entity.rating,
                    "category": entity.category,
                    "comment": entity.comment,
                },
            )
            return self._to_entity(instance)
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error upserting feedback") from exc

    def save(self, entity: MessageFeedbackEntity) -> MessageFeedbackEntity:
        """Explicit save — use ``upsert`` instead for normal usage."""
        try:
            if entity.id is not None:
                instance = MessageFeedback.objects.get(id=entity.id)
            else:
                instance = None
            instance = self._apply_from_entity(entity, instance)
            instance.save()
            return self._to_entity(instance)
        except ObjectDoesNotExist as exc:
            raise DatabaseError(
                f"Cannot update feedback {entity.id}: not found."
            ) from exc
        except IntegrityError as exc:
            raise DatabaseError(
                "Duplicate feedback entry. Use upsert to update existing feedback."
            ) from exc
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error saving feedback") from exc
