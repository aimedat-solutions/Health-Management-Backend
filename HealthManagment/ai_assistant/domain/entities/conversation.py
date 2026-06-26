from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ConversationEntity:
    """Pure-domain representation of a patient–AI conversation.

    No Django dependencies.  Every field maps to a ``Conversation`` model
    column, but the entity itself knows nothing about the ORM.
    """

    id: Optional[int] = None
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    title: str = ""
    status: str = "active"
    model_id: Optional[int] = None
    summary: str = ""
    metadata: dict = field(default_factory=dict)
    total_tokens: int = 0
    message_count: int = 0
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


@dataclass
class MessageEntity:
    """Pure-domain representation of a single chat message."""

    id: Optional[int] = None
    conversation_id: Optional[int] = None
    role: str = ""
    content_type: str = "text"
    content: str = ""
    content_data: dict = field(default_factory=dict)
    hidden_from_patient: bool = False
    tokens: int = 0
    created_at: Optional[datetime] = None


@dataclass
class MessageFeedbackEntity:
    """Patient rating / feedback on a specific AI message."""

    id: Optional[int] = None
    message_id: Optional[int] = None
    patient_id: Optional[int] = None
    rating: int = 0
    category: str = ""
    comment: str = ""
    created_at: Optional[datetime] = None


@dataclass
class DoctorReviewEntity:
    """Doctor review of an entire conversation."""

    id: Optional[int] = None
    conversation_id: Optional[int] = None
    doctor_id: Optional[int] = None
    status: str = "requested"
    notes: str = ""
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class AgentExecutionEntity:
    """Log entry tracking a single AI agent execution."""

    id: Optional[int] = None
    agent_id: Optional[int] = None
    conversation_id: Optional[int] = None
    message_id: Optional[int] = None
    execution_id: str = ""
    status: str = "pending"
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    error_message: str = ""
    tokens_used: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@dataclass
class AIModelEntity:
    """AI model configuration."""

    id: Optional[int] = None
    name: str = ""
    provider: str = ""
    model_id: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    is_active: bool = True
    cost_per_input_token: Decimal = Decimal("0")
    cost_per_output_token: Decimal = Decimal("0")


@dataclass
class AIAgentEntity:
    """AI agent configuration with its system prompt."""

    id: Optional[int] = None
    name: str = ""
    agent_type: str = ""
    description: str = ""
    system_prompt: str = ""
    model_id: Optional[int] = None
    is_active: bool = True
    timeout_seconds: int = 60
    max_retries: int = 3
