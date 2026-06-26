"""Domain and service-layer exceptions.

Every custom exception in the ai_assistant module inherits from
``AIAssistantError`` so callers can catch a single base type at the
view's exception handler and map it to the appropriate HTTP response.
"""


class AIAssistantError(Exception):
    """Base exception for all ai_assistant errors."""


# ── Not-found errors ────────────────────────────────────────────────────────


class ConversationNotFoundError(AIAssistantError):
    ...


class MessageNotFoundError(AIAssistantError):
    ...


class FeedbackNotFoundError(AIAssistantError):
    ...


class ReviewNotFoundError(AIAssistantError):
    ...


class ModelNotFoundError(AIAssistantError):
    ...


class AgentNotFoundError(AIAssistantError):
    ...


# ── Business-rule violations ─────────────────────────────────────────────────


class UnauthorizedConversationAccessError(AIAssistantError):
    """The requesting user does not own the conversation and is not assigned."""


class ConversationNotActiveError(AIAssistantError):
    """The conversation status does not allow sending messages.

    Only conversations with ``active`` or ``paused`` status accept new
    messages.
    """


class ReviewStateTransitionError(AIAssistantError):
    """The requested review status transition is not valid given the
    current state of the review.
    """


class DuplicateReviewError(AIAssistantError):
    """A review already exists for this doctor–conversation pair."""


class PatientQuotaExceededError(AIAssistantError):
    """Patient has exceeded their allowed conversation or token quota."""


class TokenLimitExceededError(AIAssistantError):
    """Conversation or request exceeds the maximum token limit."""


class ConversationDeletedError(AIAssistantError):
    """Operation attempted on a soft-deleted or archived conversation."""


# ── Infrastructure errors ────────────────────────────────────────────────────


class DatabaseError(AIAssistantError):
    """Wrapper for low-level database failures (connection, deadlock, etc.)."""


class LLMServiceError(AIAssistantError):
    """Raised when an LLM call fails after retries."""


class RAGServiceError(AIAssistantError):
    """Raised when retrieval fails."""


class AgentExecutionError(AIAssistantError):
    """Raised when an AI agent fails to complete."""
