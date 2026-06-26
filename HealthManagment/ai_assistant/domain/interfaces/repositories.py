from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from ai_assistant.domain.entities.conversation import (
    AIAgentEntity,
    AIModelEntity,
    AgentExecutionEntity,
    ConversationEntity,
    DoctorReviewEntity,
    MessageEntity,
    MessageFeedbackEntity,
)
from ai_assistant.domain.value_objects.cursor_page import CursorPage


# ── Conversation ────────────────────────────────────────────────────────────


class ConversationRepository(ABC):
    """Data-access contract for ``Conversation`` aggregate.

    Every method returns or accepts domain entities — never Django model
    instances.  This keeps business logic completely decoupled from the ORM.
    """

    @abstractmethod
    def get_by_id(self, conversation_id: int) -> Optional[ConversationEntity]:
        ...

    @abstractmethod
    def get_by_id_for_user(
        self, conversation_id: int, user_id: int
    ) -> Optional[ConversationEntity]:
        ...

    @abstractmethod
    def list_by_patient(
        self,
        patient_id: int,
        status: Optional[str] = None,
        ordering: str = "-updated_at",
    ) -> list[ConversationEntity]:
        ...

    @abstractmethod
    def list_by_doctor(
        self,
        doctor_id: int,
        status: Optional[str] = None,
        ordering: str = "-updated_at",
    ) -> list[ConversationEntity]:
        ...

    @abstractmethod
    def list_all(
        self,
        status: Optional[str] = None,
        ordering: str = "-updated_at",
    ) -> list[ConversationEntity]:
        ...

    @abstractmethod
    def save(self, entity: ConversationEntity) -> ConversationEntity:
        ...

    @abstractmethod
    def update_status(self, conversation_id: int, status: str) -> None:
        ...

    @abstractmethod
    def increment_message_count(self, conversation_id: int) -> None:
        ...

    @abstractmethod
    def add_tokens(self, conversation_id: int, count: int) -> None:
        ...

    @abstractmethod
    def count_by_patient(self, patient_id: int) -> int:
        ...

    @abstractmethod
    def exists(self, conversation_id: int) -> bool:
        ...


# ── Message ─────────────────────────────────────────────────────────────────


class MessageRepository(ABC):
    """Data-access contract for ``Message``.

    Message retrieval uses **cursor-based pagination** (not offset/limit)
    because new messages arrive between page requests in a chat context,
    and offset pagination produces duplicates or gaps in that scenario.
    """

    @abstractmethod
    def get_by_id(self, message_id: int) -> Optional[MessageEntity]:
        ...

    @abstractmethod
    def get_by_id_for_conversation(
        self, message_id: int, conversation_id: int
    ) -> Optional[MessageEntity]:
        ...

    @abstractmethod
    def list_by_conversation(
        self, conversation_id: int
    ) -> list[MessageEntity]:
        ...

    @abstractmethod
    def get_cursor_page(
        self,
        conversation_id: int,
        cursor: Optional[str] = None,
        limit: int = 50,
        direction: str = "backward",
    ) -> CursorPage[MessageEntity]:
        ...

    @abstractmethod
    def get_last_n(
        self, conversation_id: int, n: int = 20
    ) -> list[MessageEntity]:
        ...

    @abstractmethod
    def save(self, entity: MessageEntity) -> MessageEntity:
        ...

    @abstractmethod
    def count_by_conversation(self, conversation_id: int) -> int:
        ...


# ── Feedback ────────────────────────────────────────────────────────────────


class FeedbackRepository(ABC):
    """Data-access contract for ``MessageFeedback``.

    Uses upsert semantics — a patient may only submit one feedback entry
    per message.  If an entry already exists for ``(message, patient)``
    the repository updates it rather than raising a duplicate-key error.
    """

    @abstractmethod
    def get_by_message_and_patient(
        self, message_id: int, patient_id: int
    ) -> Optional[MessageFeedbackEntity]:
        ...

    @abstractmethod
    def get_by_message(self, message_id: int) -> Optional[MessageFeedbackEntity]:
        ...

    @abstractmethod
    def upsert(self, entity: MessageFeedbackEntity) -> MessageFeedbackEntity:
        ...

    @abstractmethod
    def save(self, entity: MessageFeedbackEntity) -> MessageFeedbackEntity:
        ...


# ── Doctor Review ───────────────────────────────────────────────────────────


class ReviewRepository(ABC):
    """Data-access contract for ``DoctorReview``."""

    @abstractmethod
    def get_by_id(self, review_id: int) -> Optional[DoctorReviewEntity]:
        ...

    @abstractmethod
    def get_by_conversation_and_doctor(
        self, conversation_id: int, doctor_id: int
    ) -> Optional[DoctorReviewEntity]:
        ...

    @abstractmethod
    def list_by_conversation(
        self, conversation_id: int
    ) -> list[DoctorReviewEntity]:
        ...

    @abstractmethod
    def list_by_doctor(
        self,
        doctor_id: int,
        status: Optional[str] = None,
    ) -> list[DoctorReviewEntity]:
        ...

    @abstractmethod
    def list_all(
        self,
        status: Optional[str] = None,
    ) -> list[DoctorReviewEntity]:
        ...

    @abstractmethod
    def save(self, entity: DoctorReviewEntity) -> DoctorReviewEntity:
        ...


# ── Agent Execution ─────────────────────────────────────────────────────────


class AgentExecutionRepository(ABC):
    """Data-access contract for ``AgentExecution`` logs."""

    @abstractmethod
    def save(self, entity: AgentExecutionEntity) -> AgentExecutionEntity:
        ...


# ── AI Model ────────────────────────────────────────────────────────────────


class AIModelRepository(ABC):
    """Read-only contract for ``AIModel`` configuration."""

    @abstractmethod
    def get_by_id(self, model_id: int) -> Optional[AIModelEntity]:
        ...

    @abstractmethod
    def get_active(self) -> list[AIModelEntity]:
        ...

    @abstractmethod
    def get_default(self) -> Optional[AIModelEntity]:
        ...


# ── AI Agent ────────────────────────────────────────────────────────────────


class AIAgentRepository(ABC):
    """Read-only contract for ``AIAgent`` configuration."""

    @abstractmethod
    def get_by_id(self, agent_id: int) -> Optional[AIAgentEntity]:
        ...

    @abstractmethod
    def get_active(self) -> list[AIAgentEntity]:
        ...

    @abstractmethod
    def get_by_type(self, agent_type: str) -> Optional[AIAgentEntity]:
        ...
