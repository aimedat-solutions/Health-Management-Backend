from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError as DjangoDatabaseError

from ai_assistant.domain.entities.conversation import AIAgentEntity, AIModelEntity
from ai_assistant.domain.interfaces.repositories import AIAgentRepository, AIModelRepository
from ai_assistant.exceptions import AgentNotFoundError, DatabaseError, ModelNotFoundError
from ai_assistant.models import AIAgent, AIModel


class DjangoAIModelRepository(AIModelRepository):
    """Read-only repository for ``AIModel`` records.

    Models are configured via the Django admin and rarely change at
    runtime, so the service layer may safely cache the results of these
    queries.
    """

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _to_entity(instance: AIModel) -> AIModelEntity:
        return AIModelEntity(
            id=instance.id,
            name=instance.name,
            provider=instance.provider,
            model_id=instance.model_id,
            max_tokens=instance.max_tokens,
            temperature=instance.temperature,
            is_active=instance.is_active,
            cost_per_input_token=instance.cost_per_input_token,
            cost_per_output_token=instance.cost_per_output_token,
        )

    # -- Read --------------------------------------------------------------

    def get_by_id(self, model_id: int) -> Optional[AIModelEntity]:
        try:
            instance = AIModel.objects.get(id=model_id)
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(f"Database error fetching AI model {model_id}") from exc
        return self._to_entity(instance)

    def get_active(self) -> list[AIModelEntity]:
        try:
            qs = AIModel.objects.filter(is_active=True).order_by("name")
            return [self._to_entity(m) for m in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error fetching active AI models") from exc

    def get_default(self) -> Optional[AIModelEntity]:
        """Return the first active model as the system default.

        If a specific model should be the default, the admin can set its
        ``name`` to something like ``default`` and this method can be
        updated to prefer it.
        """
        try:
            instance = AIModel.objects.filter(is_active=True).first()
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error fetching default AI model") from exc
        if instance is None:
            return None
        return self._to_entity(instance)


class DjangoAIAgentRepository(AIAgentRepository):
    """Read-only repository for ``AIAgent`` records."""

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _to_entity(instance: AIAgent) -> AIAgentEntity:
        return AIAgentEntity(
            id=instance.id,
            name=instance.name,
            agent_type=instance.agent_type,
            description=instance.description or "",
            system_prompt=instance.system_prompt,
            model_id=instance.model_id,
            is_active=instance.is_active,
            timeout_seconds=instance.timeout_seconds,
            max_retries=instance.max_retries,
        )

    # -- Read --------------------------------------------------------------

    def get_by_id(self, agent_id: int) -> Optional[AIAgentEntity]:
        try:
            instance = AIAgent.objects.get(id=agent_id)
        except ObjectDoesNotExist:
            return None
        except DjangoDatabaseError as exc:
            raise DatabaseError(f"Database error fetching AI agent {agent_id}") from exc
        return self._to_entity(instance)

    def get_active(self) -> list[AIAgentEntity]:
        try:
            qs = AIAgent.objects.filter(is_active=True).order_by("name")
            return [self._to_entity(a) for a in qs]
        except DjangoDatabaseError as exc:
            raise DatabaseError("Database error fetching active AI agents") from exc

    def get_by_type(self, agent_type: str) -> Optional[AIAgentEntity]:
        try:
            instance = AIAgent.objects.filter(
                agent_type=agent_type, is_active=True
            ).first()
        except DjangoDatabaseError as exc:
            raise DatabaseError(
                f"Database error fetching AI agent by type '{agent_type}'"
            ) from exc
        if instance is None:
            return None
        return self._to_entity(instance)
