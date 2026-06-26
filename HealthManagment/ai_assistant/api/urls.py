from django.urls import path

from ai_assistant.api.views import (
    AIAgentListView,
    AIModelListView,
    ConversationDetailView,
    ConversationListView,
    MessageFeedbackView,
    MessageListView,
    ReviewDetailView,
    ReviewListGlobalView,
    ReviewListView,
)

app_name = "ai_assistant"

urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("conversations/<int:pk>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path(
        "conversations/<int:conversation_id>/messages/",
        MessageListView.as_view(),
        name="conversation-messages",
    ),
    path("messages/<int:message_id>/feedback/", MessageFeedbackView.as_view(), name="message-feedback"),
    path(
        "conversations/<int:conversation_id>/reviews/",
        ReviewListView.as_view(),
        name="conversation-reviews",
    ),
    path("reviews/", ReviewListGlobalView.as_view(), name="review-list-global"),
    path("reviews/<int:pk>/", ReviewDetailView.as_view(), name="review-detail"),
    path("models/", AIModelListView.as_view(), name="ai-model-list"),
    path("agents/", AIAgentListView.as_view(), name="ai-agent-list"),
]
