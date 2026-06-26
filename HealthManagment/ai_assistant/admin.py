from django.contrib import admin

from ai_assistant.models import (
    AIAgent,
    AIModel,
    AgentExecution,
    Conversation,
    DoctorReview,
    Message,
    MessageFeedback,
)


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "model_id", "is_active", "max_tokens")
    list_filter = ("provider", "is_active")
    search_fields = ("name", "model_id")


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_type", "is_active", "timeout_seconds", "model")
    list_filter = ("agent_type", "is_active")
    search_fields = ("name",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "status", "message_count", "total_tokens", "updated_at")
    list_filter = ("status", "started_at")
    search_fields = ("patient__email", "patient__phone", "title")
    date_hierarchy = "started_at"
    raw_id_fields = ("patient", "doctor")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "content_type", "tokens", "created_at")
    list_filter = ("role", "content_type", "created_at")
    raw_id_fields = ("conversation",)


@admin.register(AgentExecution)
class AgentExecutionAdmin(admin.ModelAdmin):
    list_display = ("id", "agent", "status", "tokens_used", "started_at", "completed_at")
    list_filter = ("status",)
    raw_id_fields = ("agent", "conversation", "message")


@admin.register(MessageFeedback)
class MessageFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "patient", "rating", "category", "created_at")
    list_filter = ("rating", "category")


@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "doctor", "status", "reviewed_at")
    list_filter = ("status",)
    raw_id_fields = ("conversation", "doctor")
