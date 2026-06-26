from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError as DjangoDatabaseError

from ai_assistant.domain.entities.conversation import DoctorReviewEntity
from ai_assistant.domain.interfaces.repositories import ReviewRepository
from ai_assistant.exceptions import DatabaseError, ReviewNotFoundError
from ai_assistant.models import DoctorReview


class DjangoReviewRepository(ReviewRepository):
    """Django ORM implementation of ``ReviewRepository``.

    Translates between ``DoctorReview`` model instances and
    ``DoctorReviewEntity`` domain objects.
    """

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _to_entity(instance: DoctorReview) -> DoctorReviewEntity:
        return DoctorReviewEntity(
            id=instance.id,
            conversation_id=instance.conversation_id,
            doctor_id=instance.doctor_id,
            status=instance.status,
            notes=instance.notes or "",
            reviewed_at=instance.reviewed_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )

    @staticmethod
    def _apply_from_entity(
        entity: DoctorReviewEntity,
        instance: Optional[DoctorReview] = None,
    ) -> DoctorReview:
        if instance is None:
            instance = DoctorReview()
        instance.conversation_id = entity.conversation_id
        instance.doctor_id = entity.doctor_id
        instance.status = entity.status
        instance.notes = entity.notes
        instance.reviewed_at = entity.reviewed_at
        return instance

    @staticmethod
    def _base_qs():
        return DoctorReview.objects.select_related("doctor", "conversation")

    # -- Read --------------------------------------------------------------

    def get_by_id(self, review_id: int) -> Optional[DoctorReviewEntity]:
        try:
            instance = self._base_qs().get(id=review_id)
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(f"Database error fetching review {review_id}") from exc
        return self._to_entity(instance)

    def get_by_conversation_and_doctor(
        self, conversation_id: int, doctor_id: int
    ) -> Optional[DoctorReviewEntity]:
        try:
            instance = self._base_qs().get(
                conversation_id=conversation_id, doctor_id=doctor_id
            )
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error fetching review for conversation {conversation_id}, "
                f"doctor {doctor_id}"
            ) from exc
        return self._to_entity(instance)

    def list_by_conversation(
        self, conversation_id: int
    ) -> list[DoctorReviewEntity]:
        try:
            qs = self._base_qs().filter(conversation_id=conversation_id).order_by("-created_at")
            return [self._to_entity(r) for r in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error listing reviews for conversation {conversation_id}"
            ) from exc

    def list_by_doctor(
        self,
        doctor_id: int,
        status: Optional[str] = None,
    ) -> list[DoctorReviewEntity]:
        try:
            qs = self._base_qs().filter(doctor_id=doctor_id)
            if status:
                qs = qs.filter(status=status)
            qs = qs.order_by("-created_at")
            return [self._to_entity(r) for r in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error listing reviews for doctor {doctor_id}"
            ) from exc

    def list_all(
        self,
        status: Optional[str] = None,
    ) -> list[DoctorReviewEntity]:
        try:
            qs = self._base_qs()
            if status:
                qs = qs.filter(status=status)
            qs = qs.order_by("-created_at")
            return [self._to_entity(r) for r in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error listing all reviews") from exc

    # -- Write -------------------------------------------------------------

    def save(self, entity: DoctorReviewEntity) -> DoctorReviewEntity:
        try:
            if entity.id is not None:
                instance = DoctorReview.objects.get(id=entity.id)
            else:
                instance = None
            instance = self._apply_from_entity(entity, instance)
            instance.save()
            return self._to_entity(instance)
        except ObjectDoesNotExist as exc:
            raise ReviewNotFoundError(
                f"Cannot update review {entity.id}: not found."
            ) from exc
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error saving review") from exc
