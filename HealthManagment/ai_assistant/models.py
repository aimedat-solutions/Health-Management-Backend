from django.conf import settings
from django.db import models

from ai_assistant.enums import (
    AIModelProvider,
    AgentType,
    ConversationStatus,
    ExecutionStatus,
    FeedbackCategory,
    MessageContentType,
    MessageRole,
    ReviewStatus,
)


class AIModel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    provider = models.CharField(max_length=20, choices=AIModelProvider.choices)
    model_id = models.CharField(max_length=200, help_text="Provider-specific model identifier")
    max_tokens = models.IntegerField(default=4096)
    temperature = models.FloatField(default=0.7)
    is_active = models.BooleanField(default=True)
    cost_per_input_token = models.DecimalField(max_digits=10, decimal_places=8, default=0)
    cost_per_output_token = models.DecimalField(max_digits=10, decimal_places=8, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_models"
        indexes = [
            models.Index(fields=["provider"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider})"


class AIAgent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    agent_type = models.CharField(max_length=30, choices=AgentType.choices)
    description = models.TextField(blank=True)
    system_prompt = models.TextField()
    model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    timeout_seconds = models.IntegerField(default=60)
    max_retries = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_agents"
        indexes = [
            models.Index(fields=["agent_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class Conversation(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_conversations",
    )
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=ConversationStatus.choices, default=ConversationStatus.ACTIVE)
    model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, blank=True)
    summary = models.TextField(blank=True, help_text="Auto-generated conversation summary")
    metadata = models.JSONField(default=dict, blank=True)
    total_tokens = models.IntegerField(default=0)
    message_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return self.title or f"Conversation {self.id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content_type = models.CharField(max_length=20, choices=MessageContentType.choices, default=MessageContentType.TEXT)
    content = models.TextField()
    content_data = models.JSONField(default=dict, blank=True, help_text="Extra data for non-text content types")
    hidden_from_patient = models.BooleanField(default=False)
    tokens = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"


class AgentExecution(models.Model):
    agent = models.ForeignKey(AIAgent, on_delete=models.SET_NULL, null=True, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="agent_executions")
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_executions")
    execution_id = models.CharField(max_length=100, unique=True, help_text="External execution ID from provider")
    status = models.CharField(max_length=20, choices=ExecutionStatus.choices, default=ExecutionStatus.PENDING)
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    tokens_used = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_executions"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["conversation", "status"]),
            models.Index(fields=["agent"]),
        ]

    def __str__(self):
        return f"{self.agent} | {self.get_status_display()}"


class MessageFeedback(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="feedback")
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_feedback")
    rating = models.IntegerField(help_text="Rating 1-5")
    category = models.CharField(max_length=20, choices=FeedbackCategory.choices, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_feedback"
        unique_together = [["message", "patient"]]
        indexes = [
            models.Index(fields=["message"]),
            models.Index(fields=["patient"]),
        ]

    def __str__(self):
        return f"Feedback {self.rating}/5 for msg {self.message_id}"


class DoctorReview(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="reviews")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversation_reviews")
    status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.REQUESTED)
    notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "doctor_reviews"
        unique_together = [["conversation", "doctor"]]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["conversation"]),
            models.Index(fields=["doctor"]),
        ]

    def __str__(self):
        return f"Review {self.get_status_display()} by {self.doctor_id}"
