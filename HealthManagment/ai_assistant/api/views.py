import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ai_assistant.api.response import ApiResponse
from ai_assistant.api.serializers import (
    AIModelSerializer,
    AIAgentSerializer,
    ConversationCreateInputSerializer,
    ConversationDetailOutputSerializer,
    ConversationListOutputSerializer,
    ConversationUpdateInputSerializer,
    FeedbackCreateInputSerializer,
    FeedbackOutputSerializer,
    MessageCreateInputSerializer,
    MessageOutputSerializer,
    ReviewCreateInputSerializer,
    ReviewOutputSerializer,
    ReviewUpdateInputSerializer,
    SendMessageResultSerializer,
)
from ai_assistant.permissions import IsDoctorUser
from users.permissions import IsAdminOrSuperAdmin
from ai_assistant.domain.value_objects.cursor_page import CursorPage
from ai_assistant.exceptions import (
    AIAssistantError,
    ConversationDeletedError,
    ConversationNotActiveError,
    ConversationNotFoundError,
    DatabaseError,
    DuplicateReviewError,
    LLMServiceError,
    MessageNotFoundError,
    PatientQuotaExceededError,
    ReviewStateTransitionError,
    TokenLimitExceededError,
    UnauthorizedConversationAccessError,
)
from ai_assistant.services.consultation import ConsultationService
from ai_assistant.repositories.conversation_repo import DjangoConversationRepository
from ai_assistant.repositories.message_repo import DjangoMessageRepository
from ai_assistant.repositories.feedback_repo import DjangoFeedbackRepository
from ai_assistant.repositories.review_repo import DjangoReviewRepository
from ai_assistant.repositories.agent_execution_repo import DjangoAgentExecutionRepository
from ai_assistant.repositories.model_repo import DjangoAIModelRepository, DjangoAIAgentRepository
from ai_assistant.models import AIModel, AIAgent

logger = logging.getLogger(__name__)


_EXCEPTION_STATUS_MAP: dict[type, int] = {
    ConversationNotFoundError: status.HTTP_404_NOT_FOUND,
    MessageNotFoundError: status.HTTP_404_NOT_FOUND,
    UnauthorizedConversationAccessError: status.HTTP_404_NOT_FOUND,
    ConversationNotActiveError: status.HTTP_409_CONFLICT,
    ReviewStateTransitionError: status.HTTP_409_CONFLICT,
    DuplicateReviewError: status.HTTP_409_CONFLICT,
    PatientQuotaExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    TokenLimitExceededError: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    ConversationDeletedError: status.HTTP_410_GONE,
    LLMServiceError: status.HTTP_502_BAD_GATEWAY,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _get_consultation_service() -> ConsultationService:
    return ConsultationService(
        conversation_repo=DjangoConversationRepository(),
        message_repo=DjangoMessageRepository(),
        feedback_repo=DjangoFeedbackRepository(),
        review_repo=DjangoReviewRepository(),
        execution_repo=DjangoAgentExecutionRepository(),
        model_repo=DjangoAIModelRepository(),
        agent_repo=DjangoAIAgentRepository(),
    )


def _error_response(exc: AIAssistantError) -> ApiResponse:
    http_status = _EXCEPTION_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return ApiResponse(
        data={"detail": str(exc)},
        status=http_status,
    )


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        svc = _get_consultation_service()
        try:
            entities = svc.list_conversations(
                user_id=request.user.pk,
                user_role=getattr(request.user, "role", "patient"),
                status=request.query_params.get("status"),
                ordering=request.query_params.get("ordering", "-updated_at"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)
        serializer = ConversationListOutputSerializer(entities, many=True)
        return ApiResponse(data=serializer.data)

    def post(self, request):
        input_serializer = ConversationCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        svc = _get_consultation_service()
        try:
            entity = svc.create_conversation(
                patient_id=request.user.pk,
                title=input_serializer.validated_data["title"],
                metadata=input_serializer.validated_data.get("metadata"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)

        output = ConversationDetailOutputSerializer(entity)
        return ApiResponse(data=output.data, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        svc = _get_consultation_service()
        try:
            entity = svc.get_conversation(
                conversation_id=pk,
                user_id=request.user.pk,
                user_role=getattr(request.user, "role", "patient"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)
        serializer = ConversationDetailOutputSerializer(entity)
        return ApiResponse(data=serializer.data)

    def patch(self, request, pk):
        input_serializer = ConversationUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        svc = _get_consultation_service()
        try:
            entity = svc.update_conversation(
                conversation_id=pk,
                user_id=request.user.pk,
                user_role=getattr(request.user, "role", "patient"),
                updates=input_serializer.validated_data,
            )
        except AIAssistantError as exc:
            return _error_response(exc)

        output = ConversationDetailOutputSerializer(entity)
        return ApiResponse(data=output.data)

    def delete(self, request, pk):
        if getattr(request.user, "role", "") != "admin":
            return ApiResponse(
                data={"detail": "Only administrators can delete conversations."},
                status=status.HTTP_403_FORBIDDEN,
            )
        svc = _get_consultation_service()
        try:
            svc.delete_conversation(conversation_id=pk)
        except AIAssistantError as exc:
            return _error_response(exc)
        return ApiResponse(status=status.HTTP_204_NO_CONTENT)


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        svc = _get_consultation_service()
        try:
            page: CursorPage = svc.get_messages(
                conversation_id=conversation_id,
                user_id=request.user.pk,
                user_role=getattr(request.user, "role", "patient"),
                cursor=request.query_params.get("cursor"),
                limit=int(request.query_params.get("limit", 50)),
                direction=request.query_params.get("direction", "backward"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)

        serializer = MessageOutputSerializer(page.items, many=True)
        meta = {
            "next_cursor": page.next_cursor,
            "has_next": page.has_more,
        }
        return ApiResponse(data=serializer.data, meta=meta)

    def post(self, request, conversation_id):
        input_serializer = MessageCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        svc = _get_consultation_service()
        try:
            result = svc.send_message(
                conversation_id=conversation_id,
                patient_id=request.user.pk,
                content=input_serializer.validated_data["content"],
                content_type=input_serializer.validated_data.get("content_type", "text"),
                content_data=input_serializer.validated_data.get("content_data"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)

        output = SendMessageResultSerializer(result)
        return ApiResponse(data=output.data, status=status.HTTP_201_CREATED)


class MessageFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        input_serializer = FeedbackCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        svc = _get_consultation_service()
        try:
            entity = svc.submit_feedback(
                message_id=message_id,
                patient_id=request.user.pk,
                rating=input_serializer.validated_data["rating"],
                category=input_serializer.validated_data.get("category"),
                comment=input_serializer.validated_data.get("comment"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)

        serializer = FeedbackOutputSerializer(entity)
        return ApiResponse(data=serializer.data, status=status.HTTP_201_CREATED)


class ReviewListView(APIView):

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsDoctorUser()]
        return [IsAuthenticated()]

    def get(self, request, conversation_id):
        svc = _get_consultation_service()
        try:
            entities = svc.list_reviews(
                conversation_id=conversation_id,
                user_id=request.user.pk,
                user_role=getattr(request.user, "role", "patient"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)
        serializer = ReviewOutputSerializer(entities, many=True)
        return ApiResponse(data=serializer.data)

    def post(self, request, conversation_id):
        input_serializer = ReviewCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        svc = _get_consultation_service()
        try:
            entity = svc.request_review(
                conversation_id=conversation_id,
                doctor_id=request.user.pk,
                notes=input_serializer.validated_data.get("notes"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)

        output = ReviewOutputSerializer(entity)
        return ApiResponse(data=output.data, status=status.HTTP_201_CREATED)


class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDoctorUser]

    def patch(self, request, pk):
        input_serializer = ReviewUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        svc = _get_consultation_service()
        try:
            entity = svc.update_review(
                review_id=pk,
                doctor_id=request.user.pk,
                status=input_serializer.validated_data["status"],
                notes=input_serializer.validated_data.get("notes"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)

        output = ReviewOutputSerializer(entity)
        return ApiResponse(data=output.data)


class ReviewListGlobalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        svc = _get_consultation_service()
        try:
            entities = svc.list_all_reviews(
                user_id=request.user.pk,
                user_role=getattr(request.user, "role", "patient"),
                status=request.query_params.get("status"),
            )
        except AIAssistantError as exc:
            return _error_response(exc)
        serializer = ReviewOutputSerializer(entities, many=True)
        return ApiResponse(data=serializer.data)


class AIModelListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def get(self, request):
        models = AIModel.objects.filter(is_active=True)
        serializer = AIModelSerializer(models, many=True)
        return ApiResponse(data=serializer.data)


class AIAgentListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def get(self, request):
        agents = AIAgent.objects.filter(is_active=True).select_related("model")
        serializer = AIAgentSerializer(agents, many=True)
        return ApiResponse(data=serializer.data)
