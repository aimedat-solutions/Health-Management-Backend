"""
AI Assistant — Serializer layer.

Every endpoint has exactly two serializers:
  - Input serializer  (plain ``Serializer`` — validates raw request data)
  - Output serializer (``ModelSerializer`` — shapes model data for responses)

Input serializers never import or query models directly. They validate shape,
type, and format only. Business rules (state machines, ownership, quotas)
live in the service layer.

Output serializers are read-only. They control field exposure — no sensitive
model fields leak to the response.
"""

from typing import Any, Optional

from rest_framework import serializers

from ai_assistant.constants import MAX_CONVERSATION_TITLE_LENGTH, MAX_MESSAGE_CONTENT_LENGTH
from ai_assistant.enums import (
    ConversationStatus,
    FeedbackCategory,
    MessageContentType,
    ReviewStatus,
)
from ai_assistant.models import AIAgent, AIModel, Conversation, DoctorReview, Message, MessageFeedback

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_VALID_CONVERSATION_STATUSES = ", ".join(ConversationStatus.values)
_VALID_CONTENT_TYPES = ", ".join(MessageContentType.values)
_VALID_FEEDBACK_CATEGORIES = ", ".join(FeedbackCategory.values)
_VALID_REVIEW_STATUSES = ", ".join(ReviewStatus.values)


def _reject_deeply_nested_metadata(value: Any, max_depth: int = 5, _current: int = 1) -> None:
    """Recursive depth check that prevents billion-laughter attacks.

    Clients should not be able to send ``{"a": {"b": {"c": …}}}`` 10 000
    levels deep and overwhelm the JSON parser or downstream workers.
    """
    if _current > max_depth:
        raise serializers.ValidationError(
            f"Metadata nesting exceeds maximum depth of {max_depth} levels."
        )
    if isinstance(value, dict):
        for v in value.values():
            _reject_deeply_nested_metadata(v, max_depth, _current + 1)


# ---------------------------------------------------------------------------
# Shared / nested output helpers
# ---------------------------------------------------------------------------


class UserSummarySerializer(serializers.Serializer):
    """Public patient identity nested inside conversation responses.

    Excludes email, security_code, and audit fields.  ``phone_number`` is
    included because it is the primary login identifier in this system.
    """

    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True)


class DoctorSummarySerializer(serializers.Serializer):
    """Minimal doctor identity nested inside review / conversation responses."""

    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)


# ---------------------------------------------------------------------------
# AI Model / Agent  (output only — admin visibility)
# ---------------------------------------------------------------------------


class AIModelSerializer(serializers.ModelSerializer):
    """Read-only view of an AI model configuration.

    ``updated_at`` is excluded — it is irrelevant to the frontend.
    Cost fields are exposed for admin cost-tracking dashboards.
    """

    class Meta:
        model = AIModel
        fields = (
            "id",
            "name",
            "provider",
            "model_id",
            "is_active",
            "max_tokens",
            "temperature",
            "cost_per_input_token",
            "cost_per_output_token",
        )
        read_only_fields = fields


class AIAgentSerializer(serializers.ModelSerializer):
    """Read-only view of an AI agent.

    ``system_prompt`` is intentionally excluded — it is an internal
    configuration secret that must never leak to clients.
    """

    model = AIModelSerializer(read_only=True)

    class Meta:
        model = AIAgent
        fields = (
            "id",
            "name",
            "agent_type",
            "description",
            "model",
            "is_active",
            "timeout_seconds",
        )
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Conversation — input
# ---------------------------------------------------------------------------


class ConversationCreateInputSerializer(serializers.Serializer):
    """Validate ``POST /api/v1/conversations``.

    * ``title`` — required, non-blank, ≤ 255 characters.
    * ``metadata`` — optional dict, nesting depth ≤ 5.
    """

    title = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=MAX_CONVERSATION_TITLE_LENGTH,
        error_messages={
            "required": "Conversation title is required.",
            "blank": "Conversation title must not be blank.",
            "max_length": f"Conversation title must be {MAX_CONVERSATION_TITLE_LENGTH} characters or fewer.",
        },
    )
    metadata = serializers.JSONField(
        required=False,
        default=dict,
        allow_null=True,
    )

    def validate_metadata(self, value: Any) -> dict:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a JSON object.")
        _reject_deeply_nested_metadata(value)
        return value


class ConversationUpdateInputSerializer(serializers.Serializer):
    """Validate ``PATCH /api/v1/conversations/{id}``.

    All fields are optional (PATCH semantics).  The service layer enforces
    role-based restrictions (e.g. patient may only set ``paused`` /
    ``resolved``).  The serializer only checks that values are well-formed.

    * ``title`` — optional, non-blank, ≤ 255 characters.
    * ``status`` — optional, must be a valid ``ConversationStatus``.
    * ``metadata`` — optional dict, nesting depth ≤ 5.
    """

    title = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=MAX_CONVERSATION_TITLE_LENGTH,
        error_messages={
            "blank": "Conversation title must not be blank.",
            "max_length": f"Conversation title must be {MAX_CONVERSATION_TITLE_LENGTH} characters or fewer.",
        },
    )
    status = serializers.ChoiceField(
        required=False,
        choices=ConversationStatus.choices,
        error_messages={
            "invalid_choice": "'{input}' is not a valid conversation status. "
            f"Choices: {_VALID_CONVERSATION_STATUSES}.",
        },
    )
    metadata = serializers.JSONField(
        required=False,
        allow_null=True,
    )

    def validate_metadata(self, value: Any) -> Optional[dict]:
        if value is None:
            return value
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a JSON object.")
        _reject_deeply_nested_metadata(value)
        return value


# ---------------------------------------------------------------------------
# Conversation — output
# ---------------------------------------------------------------------------


class ConversationListOutputSerializer(serializers.ModelSerializer):
    """Conversation summary for list views (dashboard, search results).

    ``last_message_preview`` is populated by the service layer via a
    correlated subquery or ``Prefetch`` — never by N+1 iteration.
    """

    patient = UserSummarySerializer(read_only=True)
    doctor = DoctorSummarySerializer(read_only=True)
    model = AIModelSerializer(read_only=True)
    last_message_preview = serializers.CharField(
        read_only=True,
        help_text="First 120 characters of the most recent message.",
    )

    class Meta:
        model = Conversation
        fields = (
            "id",
            "title",
            "status",
            "message_count",
            "total_tokens",
            "summary",
            "patient",
            "doctor",
            "model",
            "last_message_preview",
            "started_at",
            "updated_at",
        )
        read_only_fields = fields


class ConversationDetailOutputSerializer(serializers.ModelSerializer):
    """Full conversation detail for the chat view or doctor review screen."""

    patient = UserSummarySerializer(read_only=True)
    doctor = DoctorSummarySerializer(read_only=True)
    model = AIModelSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "id",
            "title",
            "status",
            "message_count",
            "total_tokens",
            "summary",
            "metadata",
            "patient",
            "doctor",
            "model",
            "started_at",
            "updated_at",
            "resolved_at",
        )
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Message — input
# ---------------------------------------------------------------------------


class MessageCreateInputSerializer(serializers.Serializer):
    """Validate ``POST /api/v1/conversations/{id}/messages``.

    * ``content`` — required, non-blank, ≤ 100 000 characters.
    * ``content_type`` — optional, defaults to ``text``.
    * ``content_data`` — optional dict with type-specific required keys.

    Object-level validation (``validate``):
    * ``image_url`` → ``content_data`` must contain a ``url`` field that
      starts with ``http://`` or ``https://``.
    * ``file`` → ``content_data`` must contain ``file_name`` and ``mime_type``.
    * ``structured_data`` → ``content_data`` must contain ``schema`` and ``data``.
    """

    content = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=MAX_MESSAGE_CONTENT_LENGTH,
        error_messages={
            "required": "Message content is required.",
            "blank": "Message content must not be blank.",
            "max_length": f"Message content must be {MAX_MESSAGE_CONTENT_LENGTH} characters or fewer.",
        },
    )
    content_type = serializers.ChoiceField(
        required=False,
        default=MessageContentType.TEXT,
        choices=MessageContentType.choices,
        error_messages={
            "invalid_choice": "'{input}' is not a valid content type. "
            f"Choices: {_VALID_CONTENT_TYPES}.",
        },
    )
    content_data = serializers.JSONField(
        required=False,
        default=dict,
        allow_null=True,
    )

    def validate_content(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Message content must not consist solely of whitespace.")
        return stripped

    def validate_content_data(self, value: Any) -> dict:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content data must be a JSON object.")
        return value

    def validate(self, attrs: dict) -> dict:
        content_type = attrs.get("content_type", MessageContentType.TEXT)
        content_data = attrs.get("content_data", {})

        if content_type == MessageContentType.IMAGE_URL:
            url = content_data.get("url")
            if not url:
                raise serializers.ValidationError(
                    {"content_data": "When content_type is 'image_url', content_data must include a 'url' field."}
                )
            if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
                raise serializers.ValidationError(
                    {"content_data": "The 'url' field must be a valid HTTP or HTTPS URL."}
                )

        if content_type == MessageContentType.FILE:
            if not content_data.get("file_name"):
                raise serializers.ValidationError(
                    {"content_data": "When content_type is 'file', content_data must include a 'file_name' field."}
                )
            if not content_data.get("mime_type"):
                raise serializers.ValidationError(
                    {"content_data": "When content_type is 'file', content_data must include a 'mime_type' field."}
                )

        if content_type == MessageContentType.STRUCTURED:
            if not content_data.get("schema"):
                raise serializers.ValidationError(
                    {"content_data": "When content_type is 'structured_data', content_data must include a 'schema' field."}
                )
            if "data" not in content_data:
                raise serializers.ValidationError(
                    {"content_data": "When content_type is 'structured_data', content_data must include a 'data' field."}
                )

        return attrs


# ---------------------------------------------------------------------------
# Message — output
# ---------------------------------------------------------------------------


class FeedbackSummarySerializer(serializers.Serializer):
    """Inline feedback preview nested inside each AI message.

    ``None`` values let the frontend render an empty rating widget without
    an extra existence-check request.  The service layer populates this
    via ``Prefetch`` to avoid N+1 queries on the chat view.
    """

    rating = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    category = serializers.CharField(
        read_only=True,
        allow_null=True,
    )


class MessageOutputSerializer(serializers.ModelSerializer):
    """Single message in the chat transcript.

    ``hidden_from_patient`` is excluded — it is a system-internal flag.
    """

    feedback = FeedbackSummarySerializer(
        read_only=True,
        default=None,
    )

    class Meta:
        model = Message
        fields = (
            "id",
            "role",
            "content_type",
            "content",
            "content_data",
            "tokens",
            "feedback",
            "created_at",
        )
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Send-message composite response
# ---------------------------------------------------------------------------


class SendMessageResultSerializer(serializers.Serializer):
    """Composite response for the send-message endpoint.

    Returns the user message, AI response, triage assessment, and updated
    conversation status in a single round-trip.
    """

    user_message = MessageOutputSerializer(read_only=True)
    ai_message = MessageOutputSerializer(
        read_only=True,
        allow_null=True,
        help_text="Null when the AI call failed. The user message is still persisted.",
    )
    triage = serializers.DictField(
        read_only=True,
        help_text="Urgency assessment extracted from the AI response.",
    )
    conversation_status = serializers.CharField(
        read_only=True,
        help_text="May differ from the input status if auto-escalation triggered.",
    )


# ---------------------------------------------------------------------------
# Feedback — input
# ---------------------------------------------------------------------------


class FeedbackCreateInputSerializer(serializers.Serializer):
    """Validate ``POST /api/v1/messages/{id}/feedback``.

    * ``rating`` — required, integer 1–5.
    * ``category`` — optional free-text category.
    * ``comment`` — optional, ≤ 2 000 characters.
    """

    rating = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=5,
        error_messages={
            "required": "Rating is required.",
            "min_value": "Rating must be between 1 and 5.",
            "max_value": "Rating must be between 1 and 5.",
            "invalid": "Rating must be an integer.",
        },
    )
    category = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=FeedbackCategory.choices,
        error_messages={
            "invalid_choice": "'{input}' is not a valid feedback category. "
            f"Choices: {_VALID_FEEDBACK_CATEGORIES}.",
        },
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        error_messages={
            "max_length": "Feedback comment must be 2 000 characters or fewer.",
        },
    )


# ---------------------------------------------------------------------------
# Feedback — output
# ---------------------------------------------------------------------------


class FeedbackOutputSerializer(serializers.ModelSerializer):
    """Feedback detail returned on create / retrieve."""

    class Meta:
        model = MessageFeedback
        fields = (
            "id",
            "message_id",
            "rating",
            "category",
            "comment",
            "created_at",
        )
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Doctor review — input
# ---------------------------------------------------------------------------


class ReviewCreateInputSerializer(serializers.Serializer):
    """Validate ``POST /api/v1/conversations/{id}/reviews``.

    * ``status`` — optional, defaults to ``requested``.
      Limited to {``requested``, ``in_review``} — a review may not be
      created in a terminal state.
    * ``notes`` — optional, ≤ 10 000 characters.
    """

    status = serializers.ChoiceField(
        required=False,
        default=ReviewStatus.REQUESTED,
        choices=[ReviewStatus.REQUESTED, ReviewStatus.IN_REVIEW],
        error_messages={
            "invalid_choice": "Initial review status must be 'requested' or 'in_review'.",
        },
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=10000,
        error_messages={
            "max_length": "Review notes must be 10 000 characters or fewer.",
        },
    )


class ReviewUpdateInputSerializer(serializers.Serializer):
    """Validate ``PATCH /api/v1/reviews/{id}``.

    * ``status`` — required, must be a valid ``ReviewStatus``.
      State-transition rules (e.g. ``requested → approved`` is illegal) are
      enforced by the service layer.
    * ``notes`` — optional, ≤ 10 000 characters.
    """

    status = serializers.ChoiceField(
        required=True,
        choices=ReviewStatus.choices,
        error_messages={
            "required": "Review status is required.",
            "invalid_choice": "'{input}' is not a valid review status. "
            f"Choices: {_VALID_REVIEW_STATUSES}.",
        },
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=10000,
        error_messages={
            "max_length": "Review notes must be 10 000 characters or fewer.",
        },
    )


# ---------------------------------------------------------------------------
# Doctor review — output
# ---------------------------------------------------------------------------


class ReviewOutputSerializer(serializers.ModelSerializer):
    """Review detail returned on create / update / list."""

    doctor = DoctorSummarySerializer(read_only=True)

    class Meta:
        model = DoctorReview
        fields = (
            "id",
            "conversation_id",
            "doctor",
            "status",
            "notes",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Error response shape  (OpenAPI schema reference only)
# ---------------------------------------------------------------------------


class ErrorDetailSerializer(serializers.Serializer):
    """Per-error detail block returned in the ``errors`` array."""

    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    request_id = serializers.CharField()
