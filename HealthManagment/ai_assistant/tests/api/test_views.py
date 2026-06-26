from datetime import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ai_assistant.domain.entities.conversation import (
    ConversationEntity,
    DoctorReviewEntity,
    MessageEntity,
    MessageFeedbackEntity,
)
from ai_assistant.domain.value_objects.cursor_page import CursorPage
from ai_assistant.enums import ConversationStatus
from ai_assistant.exceptions import (
    ConversationNotActiveError,
    ConversationNotFoundError,
    DuplicateReviewError,
    LLMServiceError,
    PatientQuotaExceededError,
    ReviewStateTransitionError,
    UnauthorizedConversationAccessError,
)
from ai_assistant.models import AIModel, AIAgent
from ai_assistant.services.consultation import SendMessageResult

User = get_user_model()


def _build_conversation(**overrides) -> ConversationEntity:
    defaults = dict(
        id=1,
        patient_id=1,
        doctor_id=None,
        title="Test",
        status=ConversationStatus.ACTIVE,
        metadata={},
        model_id=None,
        message_count=0,
        total_tokens=0,
        summary="",
        started_at=datetime.now(),
        updated_at=datetime.now(),
        resolved_at=None,
    )
    defaults.update(overrides)
    return ConversationEntity(**defaults)


def _build_message(**overrides) -> MessageEntity:
    defaults = dict(
        id=1,
        conversation_id=1,
        role="user",
        content_type="text",
        content="Hello",
        content_data={},
        tokens=10,
        hidden_from_patient=False,
        created_at=datetime.now(),
    )
    defaults.update(overrides)
    return MessageEntity(**defaults)


def _build_feedback(**overrides) -> dict:
    defaults = dict(id=1, message_id=1, patient_id=1, rating=4, category="helpful", comment="Great", created_at=datetime.now())
    defaults.update(overrides)
    return defaults


def _build_review(**overrides) -> dict:
    defaults = dict(
        id=1,
        conversation_id=1,
        doctor_id=1,
        status="requested",
        notes="",
        reviewed_at=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(overrides)
    return defaults


class ViewTestBase(APITestCase):
    """Shared helpers for all view tests."""

    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient1", password="pass123", role="patient", phone_number="+1111111111",
        )
        self.doctor = User.objects.create_user(
            username="doctor1", password="pass123", role="doctor", phone_number="+2222222222",
        )
        self.admin = User.objects.create_user(
            username="admin1", password="pass123", role="admin", phone_number="+3333333333",
        )

    def _mock_service(self, **return_values):
        patcher = mock.patch("ai_assistant.api.views._get_consultation_service")
        mock_get = patcher.start()
        self.addCleanup(patcher.stop)
        svc = mock.MagicMock()
        for name, value in return_values.items():
            getattr(svc, name).return_value = value
        mock_get.return_value = svc
        return svc

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def _login_patient(self):
        self._login(self.patient)

    def _login_doctor(self):
        self._login(self.doctor)

    def _login_admin(self):
        self._login(self.admin)


# ─── ConversationListView ────────────────────────────────────────────────────


class ConversationListViewTests(ViewTestBase):
    url = "/api/v1/conversations/"

    def test_get_success_empty(self):
        self._login_patient()
        self._mock_service(list_conversations=[])
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"], [])

    def test_get_success_with_data(self):
        self._login_patient()
        conv = _build_conversation()
        self._mock_service(list_conversations=[conv])
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(resp.data["data"][0]["title"], "Test")

    def test_get_passes_query_params(self):
        self._login_patient()
        svc = self._mock_service(list_conversations=[])
        self.client.get(self.url + "?status=active&ordering=title")
        svc.list_conversations.assert_called_once_with(
            user_id=self.patient.pk,
            user_role="patient",
            status="active",
            ordering="title",
        )

    def test_get_patient_uses_own_role(self):
        self._login_patient()
        svc = self._mock_service(list_conversations=[])
        self.client.get(self.url)
        svc.list_conversations.assert_called_once_with(
            user_id=self.patient.pk, user_role="patient", status=None, ordering="-updated_at",
        )

    def test_get_doctor_uses_doctor_role(self):
        self._login_doctor()
        svc = self._mock_service(list_conversations=[])
        self.client.get(self.url)
        svc.list_conversations.assert_called_once_with(
            user_id=self.doctor.pk, user_role="doctor", status=None, ordering="-updated_at",
        )

    def test_get_service_failure_404(self):
        self._login_patient()
        svc = self._mock_service()
        svc.list_conversations.side_effect = ConversationNotFoundError("not found")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_requires_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_success(self):
        self._login_patient()
        conv = _build_conversation(patient_id=self.patient.pk)
        self._mock_service(create_conversation=conv)
        resp = self.client.post(self.url, {"title": "New conversation"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["data"]["title"], "Test")

    def test_post_validation_error(self):
        self._login_patient()
        resp = self.client.post(self.url, {"title": ""}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_service_failure_quota(self):
        self._login_patient()
        svc = self._mock_service()
        svc.create_conversation.side_effect = PatientQuotaExceededError("quota exceeded")
        resp = self.client.post(self.url, {"title": "New"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_post_requires_auth(self):
        resp = self.client.post(self.url, {"title": "New"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── ConversationDetailView ──────────────────────────────────────────────────


class ConversationDetailViewTests(ViewTestBase):
    url = "/api/v1/conversations/1/"

    def test_get_success(self):
        self._login_patient()
        conv = _build_conversation(patient_id=self.patient.pk)
        self._mock_service(get_conversation=conv)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["title"], "Test")

    def test_get_not_found(self):
        self._login_patient()
        svc = self._mock_service()
        svc.get_conversation.side_effect = ConversationNotFoundError("not found")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_unauthorized(self):
        self._login_patient()
        svc = self._mock_service()
        svc.get_conversation.side_effect = UnauthorizedConversationAccessError("denied")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_requires_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_success(self):
        self._login_patient()
        conv = _build_conversation(patient_id=self.patient.pk)
        self._mock_service(update_conversation=conv)
        resp = self.client.patch(self.url, {"title": "Updated"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["title"], "Test")

    def test_patch_validation_error(self):
        self._login_patient()
        resp = self.client.patch(self.url, {"status": "bogus"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_conflict(self):
        self._login_patient()
        svc = self._mock_service()
        svc.update_conversation.side_effect = ConversationNotActiveError("not active")
        resp = self.client.patch(self.url, {"status": "archived"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_patch_requires_auth(self):
        resp = self.client.patch(self.url, {"title": "Updated"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_admin_success(self):
        self._login_admin()
        self._mock_service(delete_conversation=None)
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_patient_forbidden(self):
        self._login_patient()
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_not_found(self):
        self._login_admin()
        svc = self._mock_service()
        svc.delete_conversation.side_effect = ConversationNotFoundError("not found")
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_requires_auth(self):
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── MessageListView ─────────────────────────────────────────────────────────


class MessageListViewTests(ViewTestBase):
    url = "/api/v1/conversations/1/messages/"

    def test_get_success_empty(self):
        self._login_patient()
        page = CursorPage(items=[], next_cursor=None, has_more=False)
        self._mock_service(get_messages=page)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"], [])

    def test_get_success_with_data(self):
        self._login_patient()
        msg = _build_message()
        page = CursorPage(items=[msg], next_cursor="abc", has_more=True)
        self._mock_service(get_messages=page)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(resp.data["data"][0]["content"], "Hello")
        self.assertEqual(resp.data["meta"]["next_cursor"], "abc")
        self.assertEqual(resp.data["meta"]["has_next"], True)

    def test_get_passes_query_params(self):
        self._login_patient()
        page = CursorPage(items=[], next_cursor=None, has_more=False)
        svc = self._mock_service(get_messages=page)
        self.client.get(self.url + "?cursor=xyz&limit=10&direction=forward")
        svc.get_messages.assert_called_once_with(
            conversation_id=1,
            user_id=self.patient.pk,
            user_role="patient",
            cursor="xyz",
            limit=10,
            direction="forward",
        )

    def test_get_not_found(self):
        self._login_patient()
        svc = self._mock_service()
        svc.get_messages.side_effect = ConversationNotFoundError("not found")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_requires_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_success_with_ai_response(self):
        self._login_patient()
        result = SendMessageResult(
            user_message=_build_message(role="user"),
            ai_message=_build_message(id=2, role="assistant", content="AI response"),
            triage={"urgency": "non_urgent", "recommendation": "Rest"},
            conversation_status="active",
        )
        self._mock_service(send_message=result)
        resp = self.client.post(self.url, {"content": "I have a cold"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("user_message", resp.data["data"])
        self.assertIn("ai_message", resp.data["data"])
        self.assertIn("triage", resp.data["data"])

    def test_post_success_without_ai_response(self):
        self._login_patient()
        result = SendMessageResult(
            user_message=_build_message(role="user"),
            ai_message=None,
            triage={"urgency": "unknown", "recommendation": ""},
            conversation_status="paused",
        )
        self._mock_service(send_message=result)
        resp = self.client.post(self.url, {"content": "Hello"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(resp.data["data"]["ai_message"])

    def test_post_validation_error(self):
        self._login_patient()
        resp = self.client.post(self.url, {"content": ""}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_conflict_conversation_not_active(self):
        self._login_patient()
        svc = self._mock_service()
        svc.send_message.side_effect = ConversationNotActiveError("not active")
        resp = self.client.post(self.url, {"content": "Hello"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_post_unauthorized(self):
        self._login_patient()
        svc = self._mock_service()
        svc.send_message.side_effect = UnauthorizedConversationAccessError("denied")
        resp = self.client.post(self.url, {"content": "Hello"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_llm_service_error(self):
        self._login_patient()
        svc = self._mock_service()
        svc.send_message.side_effect = LLMServiceError("LLM down")
        resp = self.client.post(self.url, {"content": "Hello"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_post_requires_auth(self):
        resp = self.client.post(self.url, {"content": "Hello"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── MessageFeedbackView ────────────────────────────────────────────────────


class MessageFeedbackViewTests(ViewTestBase):
    url = "/api/v1/messages/1/feedback/"

    def test_post_success(self):
        self._login_patient()
        fb = _build_feedback()
        svc = self._mock_service(submit_feedback=MessageFeedbackEntity(**fb))
        resp = self.client.post(self.url, {"rating": 5}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["data"]["rating"], 4)
        svc.submit_feedback.assert_called_once()

    def test_post_validation_error_bad_rating(self):
        self._login_patient()
        resp = self.client.post(self.url, {"rating": 0}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_validation_error_missing_rating(self):
        self._login_patient()
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_requires_auth(self):
        resp = self.client.post(self.url, {"rating": 3}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_passes_correct_args(self):
        self._login_patient()
        fb = _build_feedback()
        svc = self._mock_service(submit_feedback=MessageFeedbackEntity(**fb))
        self.client.post(self.url, {"rating": 4, "category": "helpful", "comment": "Nice"}, format="json")
        svc.submit_feedback.assert_called_once_with(
            message_id=1,
            patient_id=self.patient.pk,
            rating=4,
            category="helpful",
            comment="Nice",
        )


# ─── ReviewListView ──────────────────────────────────────────────────────────


class ReviewListViewTests(ViewTestBase):
    url = "/api/v1/conversations/1/reviews/"

    def test_get_success_empty(self):
        self._login_patient()
        self._mock_service(list_reviews=[])
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"], [])

    def test_get_success_with_data(self):
        self._login_patient()
        review_entity = DoctorReviewEntity(**_build_review())
        self._mock_service(list_reviews=[review_entity])
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(resp.data["data"][0]["status"], "requested")

    def test_get_not_found(self):
        self._login_patient()
        svc = self._mock_service()
        svc.list_reviews.side_effect = ConversationNotFoundError("not found")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_requires_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_success(self):
        self._login_doctor()
        review_entity = DoctorReviewEntity(**_build_review(doctor_id=self.doctor.pk))
        self._mock_service(request_review=review_entity)
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_post_duplicate_error(self):
        self._login_doctor()
        svc = self._mock_service()
        svc.request_review.side_effect = DuplicateReviewError("duplicate")
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_post_requires_auth(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── ReviewDetailView ────────────────────────────────────────────────────────


class ReviewDetailViewTests(ViewTestBase):
    url = "/api/v1/reviews/1/"

    def test_patch_success(self):
        self._login_doctor()
        review_entity = DoctorReviewEntity(**_build_review(doctor_id=self.doctor.pk, status="in_review"))
        self._mock_service(update_review=review_entity)
        resp = self.client.patch(self.url, {"status": "in_review"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["status"], "in_review")

    def test_patch_validation_error(self):
        self._login_doctor()
        resp = self.client.patch(self.url, {"status": ""}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_state_transition_error(self):
        self._login_doctor()
        svc = self._mock_service()
        svc.update_review.side_effect = ReviewStateTransitionError("bad transition")
        resp = self.client.patch(self.url, {"status": "approved"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_patch_not_found(self):
        self._login_doctor()
        svc = self._mock_service()
        svc.update_review.side_effect = ConversationNotFoundError("not found")
        resp = self.client.patch(self.url, {"status": "in_review"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_unauthorized(self):
        self._login_doctor()
        svc = self._mock_service()
        svc.update_review.side_effect = UnauthorizedConversationAccessError("denied")
        resp = self.client.patch(self.url, {"status": "in_review"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_requires_auth(self):
        resp = self.client.patch(self.url, {"status": "in_review"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── AIModelListView ─────────────────────────────────────────────────────────


class AIModelListViewTests(ViewTestBase):
    url = "/api/v1/models/"

    def test_get_success_empty(self):
        self._login_patient()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"], [])

    def test_get_success_with_data(self):
        AIModel.objects.create(
            name="GPT-4o", provider="openai", model_id="gpt-4o", is_active=True,
            max_tokens=4096, temperature=0.7, cost_per_input_token=0.00001, cost_per_output_token=0.00003,
        )
        self._login_patient()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(resp.data["data"][0]["name"], "GPT-4o")

    def test_get_filters_inactive(self):
        AIModel.objects.create(
            name="Old Model", provider="openai", model_id="old", is_active=False,
            max_tokens=2048, temperature=0.5, cost_per_input_token=0, cost_per_output_token=0,
        )
        self._login_patient()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 0)

    def test_get_requires_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── AIAgentListView ─────────────────────────────────────────────────────────


class AIAgentListViewTests(ViewTestBase):
    url = "/api/v1/agents/"

    def test_get_success_empty(self):
        self._login_patient()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"], [])

    def test_get_success_with_data(self):
        model = AIModel.objects.create(
            name="GPT-4o", provider="openai", model_id="gpt-4o", is_active=True,
            max_tokens=4096, temperature=0.7, cost_per_input_token=0, cost_per_output_token=0,
        )
        AIAgent.objects.create(
            name="Triage Agent", agent_type="triage", description="Urgency analysis",
            model=model, is_active=True, timeout_seconds=30, system_prompt="Assess urgency.",
        )
        self._login_patient()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 1)
        self.assertEqual(resp.data["data"][0]["name"], "Triage Agent")
        self.assertIn("model", resp.data["data"][0])

    def test_get_filters_inactive(self):
        model = AIModel.objects.create(
            name="GPT-4o", provider="openai", model_id="gpt-4o", is_active=True,
            max_tokens=4096, temperature=0.7, cost_per_input_token=0, cost_per_output_token=0,
        )
        AIAgent.objects.create(
            name="Retired Agent", agent_type="triage", description="Old",
            model=model, is_active=False, timeout_seconds=30, system_prompt="",
        )
        self._login_patient()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["data"]), 0)

    def test_get_requires_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
