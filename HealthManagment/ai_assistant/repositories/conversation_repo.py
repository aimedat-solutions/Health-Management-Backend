from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError as DjangoDatabaseError
from django.db.models import Prefetch, Q

from ai_assistant.domain.entities.conversation import ConversationEntity
from ai_assistant.domain.interfaces.repositories import ConversationRepository
from ai_assistant.exceptions import ConversationNotFoundError, DatabaseError
from ai_assistant.models import Conversation, Message


class DjangoConversationRepository(ConversationRepository):
    """Django ORM implementation of ``ConversationRepository``.

    Translates between ``Conversation`` model instances and
    ``ConversationEntity`` domain objects.  All database exceptions are
    caught and re-raised as domain exceptions so the service layer never
    depends on ``django.db``.
    """

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _to_entity(instance: Conversation) -> ConversationEntity:
        return ConversationEntity(
            id=instance.id,
            patient_id=instance.patient_id,
            doctor_id=instance.doctor_id,
            title=instance.title,
            status=instance.status,
            model_id=instance.model_id,
            summary=instance.summary,
            metadata=instance.metadata or {},
            total_tokens=instance.total_tokens,
            message_count=instance.message_count,
            started_at=instance.started_at,
            updated_at=instance.updated_at,
            resolved_at=instance.resolved_at,
        )

    @staticmethod
    def _apply_from_entity(
        entity: ConversationEntity,
        instance: Optional[Conversation] = None,
    ) -> Conversation:
        if instance is None:
            instance = Conversation()
        instance.patient_id = entity.patient_id
        instance.doctor_id = entity.doctor_id
        instance.title = entity.title
        instance.status = entity.status
        instance.model_id = entity.model_id
        instance.summary = entity.summary
        instance.metadata = entity.metadata
        instance.total_tokens = entity.total_tokens
        instance.message_count = entity.message_count
        instance.resolved_at = entity.resolved_at
        return instance

    @staticmethod
    def _base_qs():
        return Conversation.objects.select_related("patient", "doctor", "model")

    # -- Read --------------------------------------------------------------

    def get_by_id(self, conversation_id: int) -> Optional[ConversationEntity]:
        try:
            instance = self._base_qs().get(id=conversation_id)
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(f"Database error fetching conversation {conversation_id}") from exc
        return self._to_entity(instance)

    def get_by_id_for_user(
        self, conversation_id: int, user_id: int
    ) -> Optional[ConversationEntity]:
        try:
            instance = self._base_qs().get(
                Q(id=conversation_id),
                Q(patient_id=user_id) | Q(doctor_id=user_id),
            )
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error fetching conversation {conversation_id} for user {user_id}"
            ) from exc
        return self._to_entity(instance)

    def list_by_patient(
        self,
        patient_id: int,
        status: Optional[str] = None,
        ordering: str = "-updated_at",
    ) -> list[ConversationEntity]:
        try:
            qs = self._base_qs().filter(patient_id=patient_id)
            if status:
                qs = qs.filter(status=status)
            qs = qs.order_by(ordering)
            return [self._to_entity(c) for c in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError(f"Database error listing conversations for patient {patient_id}") from exc

    def list_by_doctor(
        self,
        doctor_id: int,
        status: Optional[str] = None,
        ordering: str = "-updated_at",
    ) -> list[ConversationEntity]:
        try:
            qs = self._base_qs().filter(doctor_id=doctor_id)
            if status:
                qs = qs.filter(status=status)
            qs = qs.order_by(ordering)
            return [self._to_entity(c) for c in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError(f"Database error listing conversations for doctor {doctor_id}") from exc

    def list_all(
        self,
        status: Optional[str] = None,
        ordering: str = "-updated_at",
    ) -> list[ConversationEntity]:
        try:
            qs = self._base_qs()
            if status:
                qs = qs.filter(status=status)
            qs = qs.order_by(ordering)
            return [self._to_entity(c) for c in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error listing all conversations") from exc

    # -- Write -------------------------------------------------------------

    def save(self, entity: ConversationEntity) -> ConversationEntity:
        try:
            if entity.id is not None:
                instance = Conversation.objects.get(id=entity.id)
            else:
                instance = None
            instance = self._apply_from_entity(entity, instance)
            instance.save()
            return self._to_entity(instance)
        except ObjectDoesNotExist as exc:
            raise ConversationNotFoundError(
                f"Cannot update conversation {entity.id}: not found."
            ) from exc
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error saving conversation") from exc

    def update_status(self, conversation_id: int, status: str) -> None:
        try:
            updated = Conversation.objects.filter(id=conversation_id).update(status=status)
            if updated == 0:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error updating status for conversation {conversation_id}"
            ) from exc

    def increment_message_count(self, conversation_id: int) -> None:
        try:
            updated = Conversation.objects.filter(id=conversation_id).update(
                message_count=models.F("message_count") + 1
            )
            if updated == 0:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error incrementing message count for conversation {conversation_id}"
            ) from exc

    def add_tokens(self, conversation_id: int, count: int) -> None:
        try:
            updated = Conversation.objects.filter(id=conversation_id).update(
                total_tokens=models.F("total_tokens") + count
            )
            if updated == 0:
                raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error adding tokens for conversation {conversation_id}"
            ) from exc

    def count_by_patient(self, patient_id: int) -> int:
        try:
            return Conversation.objects.filter(patient_id=patient_id).count()
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error counting conversations for patient {patient_id}"
            ) from exc

    def exists(self, conversation_id: int) -> bool:
        try:
            return Conversation.objects.filter(id=conversation_id).exists()
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error checking existence of conversation {conversation_id}"
            ) from exc


# Circular-import workaround: models.F is needed in methods above.
from django.db import models  # noqa: E402
