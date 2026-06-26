from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError as DjangoDatabaseError
from django.db.models import Q

from ai_assistant.domain.entities.conversation import MessageEntity
from ai_assistant.domain.interfaces.repositories import MessageRepository
from ai_assistant.domain.value_objects.cursor_page import (
    CursorPage,
    decode_cursor,
    encode_cursor,
)
from ai_assistant.exceptions import DatabaseError, MessageNotFoundError
from ai_assistant.models import Message


class DjangoMessageRepository(MessageRepository):
    """Django ORM implementation of ``MessageRepository``.

    Message lists use **cursor-based pagination** to avoid duplicates/gaps
    when new messages arrive between page requests — a fundamental issue
    with offset/limit in chat contexts.
    """

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _to_entity(instance: Message) -> MessageEntity:
        return MessageEntity(
            id=instance.id,
            conversation_id=instance.conversation_id,
            role=instance.role,
            content_type=instance.content_type,
            content=instance.content,
            content_data=instance.content_data or {},
            hidden_from_patient=instance.hidden_from_patient,
            tokens=instance.tokens,
            created_at=instance.created_at,
        )

    @staticmethod
    def _apply_from_entity(
        entity: MessageEntity,
        instance: Optional[Message] = None,
    ) -> Message:
        if instance is None:
            instance = Message()
        instance.conversation_id = entity.conversation_id
        instance.role = entity.role
        instance.content_type = entity.content_type
        instance.content = entity.content
        instance.content_data = entity.content_data
        instance.hidden_from_patient = entity.hidden_from_patient
        instance.tokens = entity.tokens
        return instance

    # -- Read --------------------------------------------------------------

    def get_by_id(self, message_id: int) -> Optional[MessageEntity]:
        try:
            instance = Message.objects.get(id=message_id)
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(f"Database error fetching message {message_id}") from exc
        return self._to_entity(instance)

    def get_by_id_for_conversation(
        self, message_id: int, conversation_id: int
    ) -> Optional[MessageEntity]:
        try:
            instance = Message.objects.get(id=message_id, conversation_id=conversation_id)
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error fetching message {message_id} in conversation {conversation_id}"
            ) from exc
        return self._to_entity(instance)

    def list_by_conversation(
        self, conversation_id: int
    ) -> list[MessageEntity]:
        try:
            qs = Message.objects.filter(conversation_id=conversation_id).order_by("created_at")
            return [self._to_entity(m) for m in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error listing messages for conversation {conversation_id}"
            ) from exc

    def get_cursor_page(
        self,
        conversation_id: int,
        cursor: Optional[str] = None,
        limit: int = 50,
        direction: str = "backward",
    ) -> CursorPage[MessageEntity]:
        """Fetch a page of messages using keyset pagination.

        * ``backward`` — newest-first (default, opens chat at the latest message).
        * ``forward``   — oldest-first (used for infinite-scroll up).
        """
        try:
            qs = Message.objects.filter(conversation_id=conversation_id)

            if cursor:
                try:
                    cursor_data = decode_cursor(cursor)
                except ValueError:
                    cursor_data = None

                if cursor_data:
                    dt = cursor_data["created_at"]
                    pk = cursor_data["id"]
                    if direction == "backward":
                        qs = qs.filter(Q(created_at__lt=dt) | Q(created_at=dt, id__lt=pk))
                    else:
                        qs = qs.filter(Q(created_at__gt=dt) | Q(created_at=dt, id__gt=pk))

            if direction == "backward":
                qs = qs.order_by("-created_at", "-id")
            else:
                qs = qs.order_by("created_at", "id")

            # Fetch limit+1 to detect whether a subsequent page exists.
            results = list(qs[: limit + 1])
            has_more = len(results) > limit
            items = results[:limit]

            if has_more:
                last = results[limit - 1]
                next_cursor = encode_cursor(last.id, last.created_at)
            else:
                next_cursor = None

            return CursorPage(
                items=[self._to_entity(m) for m in items],
                next_cursor=next_cursor,
                has_more=has_more,
            )
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error fetching cursor page for conversation {conversation_id}"
            ) from exc

    def get_last_n(
        self, conversation_id: int, n: int = 20
    ) -> list[MessageEntity]:
        try:
            qs = (
                Message.objects.filter(conversation_id=conversation_id)
                .order_by("-created_at")[:n]
            )
            # Return in chronological order (oldest first) for the AI context builder.
            return [self._to_entity(m) for m in reversed(qs)]
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error fetching last {n} messages for conversation {conversation_id}"
            ) from exc

    # -- Write -------------------------------------------------------------

    def save(self, entity: MessageEntity) -> MessageEntity:
        try:
            if entity.id is not None:
                instance = Message.objects.get(id=entity.id)
            else:
                instance = None
            instance = self._apply_from_entity(entity, instance)
            instance.save()
            return self._to_entity(instance)
        except ObjectDoesNotExist as exc:
            raise MessageNotFoundError(
                f"Cannot update message {entity.id}: not found."
            ) from exc
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error saving message") from exc

    def count_by_conversation(self, conversation_id: int) -> int:
        try:
            return Message.objects.filter(conversation_id=conversation_id).count()
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error counting messages in conversation {conversation_id}"
            ) from exc
