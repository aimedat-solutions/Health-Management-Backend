from typing import Optional

from django.db import DatabaseError as DjangoDatabaseError

from ai_assistant.domain.entities.conversation import AgentExecutionEntity
from ai_assistant.domain.interfaces.repositories import AgentExecutionRepository
from ai_assistant.exceptions import DatabaseError
from ai_assistant.models import AgentExecution


class DjangoAgentExecutionRepository(AgentExecutionRepository):
    """Django ORM implementation of ``AgentExecutionRepository``.

    Agent executions are append-only logs — there is no update or delete
    in v1.
    """

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _to_entity(instance: AgentExecution) -> AgentExecutionEntity:
        return AgentExecutionEntity(
            id=instance.id,
            agent_id=instance.agent_id,
            conversation_id=instance.conversation_id,
            message_id=instance.message_id,
            execution_id=instance.execution_id,
            status=instance.status,
            input_data=instance.input_data or {},
            output_data=instance.output_data or {},
            error_message=instance.error_message or "",
            tokens_used=instance.tokens_used,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            created_at=instance.created_at,
        )

    @staticmethod
    def _apply_from_entity(
        entity: AgentExecutionEntity,
        instance: Optional[AgentExecution] = None,
    ) -> AgentExecution:
        if instance is None:
            instance = AgentExecution()
        instance.agent_id = entity.agent_id
        instance.conversation_id = entity.conversation_id
        instance.message_id = entity.message_id
        instance.execution_id = entity.execution_id
        instance.status = entity.status
        instance.input_data = entity.input_data
        instance.output_data = entity.output_data
        instance.error_message = entity.error_message
        instance.tokens_used = entity.tokens_used
        instance.started_at = entity.started_at
        instance.completed_at = entity.completed_at
        return instance

    # -- Write -------------------------------------------------------------

    def save(self, entity: AgentExecutionEntity) -> AgentExecutionEntity:
        try:
            instance = self._apply_from_entity(entity)
            instance.save()
            return self._to_entity(instance)
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error saving agent execution log") from exc
