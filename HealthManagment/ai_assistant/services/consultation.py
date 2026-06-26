"""
Service layer for the patient–AI consultation flow.

``ConsultationService`` is the single entry-point for all conversation
and message operations.  It enforces business rules, orchestrates
repository calls, manages transaction boundaries, and logs every
operation.  Views never talk to repositories directly.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from django.db import transaction
from django.utils import timezone

from ai_assistant.domain.entities.conversation import (
    AIAgentEntity,
    AIModelEntity,
    AgentExecutionEntity,
    ConversationEntity,
    DoctorReviewEntity,
    MessageEntity,
    MessageFeedbackEntity,
)
from ai_assistant.domain.interfaces.repositories import (
    AIAgentRepository,
    AIModelRepository,
    AgentExecutionRepository,
    ConversationRepository,
    FeedbackRepository,
    MessageRepository,
    ReviewRepository,
)
from ai_assistant.domain.value_objects.cursor_page import CursorPage
from ai_assistant.enums import (
    AgentType,
    ConversationStatus,
    ExecutionStatus,
    MessageRole,
    ReviewStatus,
)
from ai_assistant.exceptions import (
    ConversationNotActiveError,
    ConversationNotFoundError,
    DuplicateReviewError,
    LLMServiceError,
    PatientQuotaExceededError,
    ReviewStateTransitionError,
    UnauthorizedConversationAccessError,
)
from ai_assistant.llm.base import BaseLLMClient, LLMResponse

logger = logging.getLogger(__name__)


# ── DTOs ─────────────────────────────────────────────────────────────────────


@dataclass
class SendMessageResult:
    """Composite result returned by ``send_message``.

    ``ai_message`` is ``None`` when:
    * the conversation was paused, or
    * the LLM call failed (the user message is still persisted).
    """

    user_message: MessageEntity
    ai_message: Optional[MessageEntity] = None
    triage: dict = field(default_factory=lambda: {"urgency": "unknown", "recommendation": ""})
    conversation_status: str = "active"


# ── Service ──────────────────────────────────────────────────────────────────


class ConsultationService:
    """Orchestrates conversation and message operations.

    Every public method enforces at least one business rule and delegates
    all data access to injected repositories.  No direct ORM usage.
    """

    PATIENT_WRITABLE_FIELDS = frozenset({"title", "status"})
    PATIENT_ALLOWED_STATUSES = frozenset({ConversationStatus.PAUSED, ConversationStatus.RESOLVED})
    DOCTOR_ALLOWED_STATUSES = frozenset({ConversationStatus.RESOLVED, ConversationStatus.ARCHIVED})
    MAX_CONVERSATIONS_PER_PATIENT = 1000

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        feedback_repo: FeedbackRepository,
        review_repo: ReviewRepository,
        execution_repo: AgentExecutionRepository,
        model_repo: AIModelRepository,
        agent_repo: AIAgentRepository,
        patient_info_provider: Optional[Callable[[int], dict]] = None,
        llm_client: Optional[BaseLLMClient] = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._feedback_repo = feedback_repo
        self._review_repo = review_repo
        self._execution_repo = execution_repo
        self._model_repo = model_repo
        self._agent_repo = agent_repo
        self._patient_info_provider = patient_info_provider
        self._llm_client = llm_client

    # ── Conversation CRUD ─────────────────────────────────────────────────

    def create_conversation(
        self,
        patient_id: int,
        title: str,
        metadata: Optional[dict] = None,
    ) -> ConversationEntity:
        """Start a new patient–AI conversation.

        Business rules:
        * A patient may not exceed ``MAX_CONVERSATIONS_PER_PATIENT``
          active conversations (soft quota — prevents abuse).
        """
        logger.info("Creating conversation for patient %d", patient_id)

        current_count = self._conversation_repo.count_by_patient(patient_id)
        if current_count > self.MAX_CONVERSATIONS_PER_PATIENT:
            raise PatientQuotaExceededError(
                f"Patient {patient_id} has {current_count} conversations, "
                f"exceeding the limit of {self.MAX_CONVERSATIONS_PER_PATIENT}."
            )

        default_model = self._model_repo.get_default()

        entity = ConversationEntity(
            patient_id=patient_id,
            title=title,
            metadata=metadata or {},
            model_id=default_model.id if default_model else None,
        )
        saved = self._conversation_repo.save(entity)
        logger.info("Created conversation %d for patient %d", saved.id, patient_id)
        return saved

    def get_conversation(
        self,
        conversation_id: int,
        user_id: int,
        user_role: str,
    ) -> ConversationEntity:
        """Fetch a single conversation with access control.

        Business rules:
        * Patients see only their own conversations.
        * Doctors see only conversations assigned to them.
        * Admins see everything.
        """
        logger.debug("Fetching conversation %d for user %d (role=%s)", conversation_id, user_id, user_role)

        conversation = self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found."
            )

        if user_role == "patient" and conversation.patient_id != user_id:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found or access denied."
            )
        if user_role == "doctor" and conversation.doctor_id != user_id:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found or access denied."
            )

        return conversation

    def list_conversations(
        self,
        user_id: int,
        user_role: str,
        status: Optional[str] = None,
        ordering: str = "-updated_at",
    ) -> list[ConversationEntity]:
        """Return conversations visible to the requesting user.

        Business rules:
        * Patients see their own conversations.
        * Doctors see conversations assigned to them.
        * Admins see all conversations.
        """
        logger.debug("Listing conversations for user %d (role=%s)", user_id, user_role)

        if user_role == "admin":
            return self._conversation_repo.list_all(status=status, ordering=ordering)
        if user_role == "doctor":
            return self._conversation_repo.list_by_doctor(
                doctor_id=user_id, status=status, ordering=ordering
            )
        return self._conversation_repo.list_by_patient(
            patient_id=user_id, status=status, ordering=ordering
        )

    def _get_conversation_unrestricted(self, conversation_id: int) -> ConversationEntity:
        """Fetch a conversation by ID without role-based access filtering.

        Raises ``ConversationNotFoundError`` if it does not exist.
        """
        conversation = self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
        return conversation

    def update_conversation(
        self,
        conversation_id: int,
        user_id: int,
        user_role: str,
        updates: dict,
    ) -> ConversationEntity:
        """Apply partial updates to a conversation.

        Business rules:
        * **Patient** — can only update ``title`` or ``status`` (to
          ``paused`` or ``resolved``).  Must own the conversation.
        * **Doctor** — can update ``title``, ``status`` (to ``resolved``
          or ``archived``), and ``metadata``.  Must be assigned.
        * **Admin** — unrestricted.

        Unknown keys in ``updates`` are silently ignored.
        """
        conversation = self._get_conversation_unrestricted(conversation_id)

        if user_role == "admin":
            pass  # full access

        elif user_role == "patient":
            if conversation.patient_id != user_id:
                raise UnauthorizedConversationAccessError(
                    f"Patient {user_id} does not own conversation {conversation_id}."
                )
            filtered = {k: v for k, v in updates.items() if k in self.PATIENT_WRITABLE_FIELDS}
            if "status" in filtered and filtered["status"] not in self.PATIENT_ALLOWED_STATUSES:
                raise ConversationNotActiveError(
                    f"Patient may only set status to one of: "
                    f"{', '.join(self.PATIENT_ALLOWED_STATUSES)}."
                )
            updates = filtered

        elif user_role == "doctor":
            if conversation.doctor_id != user_id:
                raise UnauthorizedConversationAccessError(
                    f"Doctor {user_id} is not assigned to conversation {conversation_id}."
                )
            doctor_allowed = frozenset({"title", "status", "metadata"})
            filtered = {k: v for k, v in updates.items() if k in doctor_allowed}
            if "status" in filtered and filtered["status"] not in self.DOCTOR_ALLOWED_STATUSES:
                raise ConversationNotActiveError(
                    f"Doctor may only set status to one of: "
                    f"{', '.join(self.DOCTOR_ALLOWED_STATUSES)}."
                )
            updates = filtered

        if not updates:
            return conversation

        if "title" in updates:
            conversation.title = updates["title"]
        if "status" in updates:
            conversation.status = updates["status"]
        if "metadata" in updates and isinstance(updates["metadata"], dict):
            conversation.metadata = {**conversation.metadata, **updates["metadata"]}

        saved = self._conversation_repo.save(conversation)
        logger.info("Updated conversation %d (fields=%s)", conversation_id, list(updates))
        return saved

    def delete_conversation(self, conversation_id: int) -> None:
        """Soft-delete a conversation by archiving it.

        Business rules:
        * Only callable by admin (enforced at the view layer).
        * The conversation is archived, not hard-deleted, so patient data
          is preserved for audit and regulatory compliance.
        """
        conversation = self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
        self._conversation_repo.update_status(conversation_id, ConversationStatus.ARCHIVED)
        logger.info("Archived conversation %d", conversation_id)

    # ── Messages ──────────────────────────────────────────────────────────

    def send_message(
        self,
        conversation_id: int,
        patient_id: int,
        content: str,
        content_type: str = "text",
        content_data: Optional[dict] = None,
    ) -> SendMessageResult:
        """Save a patient message and, if the conversation is active,
        generate an AI response.

        Business rules:
        * The patient must own the conversation.
        * The conversation must be ``active`` or ``paused``.
        * If ``paused`` — the message is saved but the AI does not respond.
        * If ``active`` — the AI pipeline runs synchronously.

        Transaction strategy:
        1. Save user message in its own transaction (so it is never lost).
        2. Call LLM outside any transaction (avoids long-held DB locks).
        3. Save AI message + counters + optional escalation in a second
           transaction.

        If the LLM call fails, the user message is already on disk and
        returned to the client.  A background worker can retry generation.
        """
        logger.info("send_message: conv=%d patient=%d len(content)=%d", conversation_id, patient_id, len(content))

        # ── 1.  Fetch and validate conversation ──
        conversation = self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found.")
        if conversation.patient_id != patient_id:
            raise UnauthorizedConversationAccessError(
                f"Patient {patient_id} does not own conversation {conversation_id}."
            )
        if conversation.status not in (ConversationStatus.ACTIVE, ConversationStatus.PAUSED):
            raise ConversationNotActiveError(
                f"Cannot send message in conversation with status "
                f"'{conversation.status}'.  Must be 'active' or 'paused'."
            )

        # ── 2.  Save user message ──
        with transaction.atomic():
            user_msg = MessageEntity(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content_type=content_type,
                content=content,
                content_data=content_data or {},
                tokens=0,
            )
            user_msg = self._message_repo.save(user_msg)
            logger.debug("Saved user message %d", user_msg.id)

        # ── 3.  Early return if paused ──
        if conversation.status == ConversationStatus.PAUSED:
            return SendMessageResult(
                user_message=user_msg,
                ai_message=None,
                triage={"urgency": "unknown", "recommendation": "Conversation is paused. AI response skipped."},
                conversation_status=ConversationStatus.PAUSED,
            )

        # ── 4.  AI pipeline ──
        ai_message: Optional[MessageEntity] = None
        triage: dict = {"urgency": "unknown", "recommendation": ""}
        conversation_status = conversation.status

        if self._llm_client is not None:
            try:
                ai_message, triage = self._execute_ai_pipeline(conversation, user_msg)
                conversation_status = conversation.status
            except LLMServiceError:
                logger.exception("AI pipeline failed for conversation %d", conversation_id)
                ai_message = None
                triage = {"urgency": "unknown", "recommendation": "AI service temporarily unavailable."}

        return SendMessageResult(
            user_message=user_msg,
            ai_message=ai_message,
            triage=triage,
            conversation_status=conversation_status,
        )

    def _execute_ai_pipeline(
        self,
        conversation: ConversationEntity,
        user_msg: MessageEntity,
    ) -> tuple[MessageEntity, dict]:
        """Run the AI generation pipeline after a user message is saved.

        Steps: build context → select model/agent → call LLM →
        parse triage → save AI message → update counters → check escalation.

        Returns ``(ai_message_entity, triage_dict)``.
        """
        # ── 4a.  Build context ──
        recent_messages = self._message_repo.get_last_n(conversation.id, n=20)

        patient_info = ""
        if self._patient_info_provider is not None:
            try:
                info = self._patient_info_provider(conversation.patient_id)
                if info:
                    patient_info = self._format_patient_info(info)
            except Exception:
                logger.warning("Failed to fetch patient info for %d", conversation.patient_id)

        # ── 4b.  Select model & agent ──
        model: Optional[AIModelEntity] = None
        if conversation.model_id:
            model = self._model_repo.get_by_id(conversation.model_id)
        if model is None:
            model = self._model_repo.get_default()

        agent = self._agent_repo.get_by_type(AgentType.TRIAGE)
        system_prompt = agent.system_prompt if agent else "You are a helpful medical assistant."

        # ── 4c.  Build prompt ──
        prompt = self._build_prompt(
            system_prompt=system_prompt,
            summary=conversation.summary,
            patient_info=patient_info,
            recent_messages=recent_messages,
            new_content=user_msg.content,
        )

        # ── 4d.  Call LLM ──
        model_id_str = model.model_id if model else "unknown"
        max_tokens = model.max_tokens if model else 4096
        temperature = model.temperature if model else 0.7

        response: LLMResponse = self._llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model_id_str,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # ── 4e.  Parse triage from response ──
        triage = self._parse_triage(response.content)

        # ── 4f.  Save AI message + counters + log — single transaction ──
        with transaction.atomic():
            ai_message = MessageEntity(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content_type="text",
                content=response.content,
                tokens=response.tokens_output,
            )
            ai_message = self._message_repo.save(ai_message)

            self._conversation_repo.increment_message_count(conversation.id)
            self._conversation_repo.add_tokens(
                conversation.id, response.tokens_input + response.tokens_output
            )

            self._execution_repo.save(
                AgentExecutionEntity(
                    agent_id=agent.id if agent else None,
                    conversation_id=conversation.id,
                    message_id=ai_message.id,
                    execution_id=f"llm-{ai_message.id}-{timezone.now().timestamp()}",
                    status=ExecutionStatus.COMPLETED,
                    input_data={"prompt": prompt, "model": model_id_str},
                    output_data={"response": response.content},
                    tokens_used=response.tokens_input + response.tokens_output,
                )
            )

            # ── 4g.  Auto-escalate if emergency ──
            if triage.get("urgency") == "emergency":
                self._conversation_repo.update_status(
                    conversation.id, ConversationStatus.ESCALATED
                )
                conversation.status = ConversationStatus.ESCALATED

                self._review_repo.save(
                    DoctorReviewEntity(
                        conversation_id=conversation.id,
                        doctor_id=None,
                        status=ReviewStatus.REQUESTED,
                        notes=f"Auto-escalated: emergency detected.\n{triage.get('recommendation', '')}",
                    )
                )
                logger.warning(
                    "Auto-escalated conversation %d (emergency triage)",
                    conversation.id,
                )

        logger.info(
            "AI response saved: conv=%d user_msg=%d ai_msg=%d tokens=%d",
            conversation.id,
            user_msg.id,
            ai_message.id,
            response.tokens_input + response.tokens_output,
        )

        return ai_message, triage

    # ── Message retrieval ────────────────────────────────────────────────

    def get_messages(
        self,
        conversation_id: int,
        user_id: int,
        user_role: str,
        cursor: Optional[str] = None,
        limit: int = 50,
        direction: str = "backward",
    ) -> CursorPage[MessageEntity]:
        """Return a cursor-paginated page of messages.

        Business rules:
        * Access control is enforced by ``get_conversation``.
        * Messages with ``hidden_from_patient=True`` are filtered out for
          patients (doctor-only system messages).
        """
        self.get_conversation(conversation_id, user_id, user_role)

        page = self._message_repo.get_cursor_page(
            conversation_id=conversation_id,
            cursor=cursor,
            limit=limit,
            direction=direction,
        )

        if user_role == "patient":
            page.items = [m for m in page.items if not m.hidden_from_patient]

        return page

    # ── Feedback ──────────────────────────────────────────────────────────

    def submit_feedback(
        self,
        message_id: int,
        patient_id: int,
        rating: int,
        category: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> MessageFeedbackEntity:
        """Create or update feedback for a message.

        Uses upsert semantics — if the patient has already rated this
        message, the existing rating is updated (not duplicated).
        """
        logger.info("submit_feedback: message=%d patient=%d rating=%d", message_id, patient_id, rating)

        entity = MessageFeedbackEntity(
            message_id=message_id,
            patient_id=patient_id,
            rating=rating,
            category=category or "",
            comment=comment or "",
        )
        saved = self._feedback_repo.upsert(entity)
        logger.debug("Saved feedback %d for message %d", saved.id, message_id)
        return saved

    # ── Doctor Reviews ────────────────────────────────────────────────────

    def request_review(
        self,
        conversation_id: int,
        doctor_id: int,
        notes: Optional[str] = None,
    ) -> DoctorReviewEntity:
        """Request a doctor review for a conversation.

        Business rules:
        * A doctor may only have one active review per conversation.
        * If a review already exists, ``DuplicateReviewError`` is raised.
        """
        existing = self._review_repo.get_by_conversation_and_doctor(
            conversation_id, doctor_id
        )
        if existing is not None:
            raise DuplicateReviewError(
                f"Doctor {doctor_id} already has a review for conversation {conversation_id} "
                f"(status={existing.status})."
            )

        entity = DoctorReviewEntity(
            conversation_id=conversation_id,
            doctor_id=doctor_id,
            notes=notes or "",
        )
        saved = self._review_repo.save(entity)
        logger.info("Review requested: conv=%d doctor=%d review=%d", conversation_id, doctor_id, saved.id)
        return saved

    def update_review(
        self,
        review_id: int,
        doctor_id: int,
        status: str,
        notes: Optional[str] = None,
    ) -> DoctorReviewEntity:
        """Update a doctor review's status and notes.

        Business rules:
        * The doctor must own the review.
        * The state machine must be followed:
          ``requested → in_review → approved | rejected | needs_revision``.
        """
        review = self._review_repo.get_by_id(review_id)
        if review is None:
            raise ConversationNotFoundError(f"Review {review_id} not found.")  # reuse: ReviewNotFoundError would also work

        if review.doctor_id != doctor_id:
            raise UnauthorizedConversationAccessError(
                f"Doctor {doctor_id} does not own review {review_id}."
            )

        allowed_transitions = {
            ReviewStatus.REQUESTED: {ReviewStatus.IN_REVIEW},
            ReviewStatus.IN_REVIEW: {
                ReviewStatus.APPROVED,
                ReviewStatus.REJECTED,
                ReviewStatus.NEEDS_REVISION,
            },
            ReviewStatus.APPROVED: set(),
            ReviewStatus.REJECTED: set(),
            ReviewStatus.NEEDS_REVISION: {ReviewStatus.IN_REVIEW},
        }

        allowed_next = allowed_transitions.get(review.status, set())
        if status not in allowed_next:
            raise ReviewStateTransitionError(
                f"Cannot transition review {review_id} from '{review.status}' "
                f"to '{status}'.  Allowed next states: "
                f"{', '.join(sorted(allowed_next)) if allowed_next else '<terminal>'}."
            )

        review.status = status
        if notes is not None:
            review.notes = notes
        if status in (ReviewStatus.APPROVED, ReviewStatus.REJECTED):
            review.reviewed_at = timezone.now()

        saved = self._review_repo.save(review)
        logger.info("Review %d updated: status=%s", review_id, status)
        return saved

    def list_reviews(
        self,
        conversation_id: int,
        user_id: int,
        user_role: str,
    ) -> list[DoctorReviewEntity]:
        """List reviews for a conversation.

        Business rules:
        * Access control is enforced by ``get_conversation``.
        """
        self.get_conversation(conversation_id, user_id, user_role)
        return self._review_repo.list_by_conversation(conversation_id)

    def list_all_reviews(
        self,
        user_id: int,
        user_role: str,
        status: Optional[str] = None,
    ) -> list[DoctorReviewEntity]:
        """List all reviews visible to the requesting user.

        Business rules:
        * Doctors see reviews assigned to them, plus unassigned reviews.
        * Admins see all reviews.
        """
        if user_role == "admin":
            return self._review_repo.list_all(status=status)
        if user_role == "doctor":
            doctor_reviews = self._review_repo.list_by_doctor(doctor_id=user_id, status=status)
            unassigned = self._review_repo.list_all(status=status or "requested")
            unassigned = [r for r in unassigned if r.doctor_id is None]
            seen = {r.id for r in doctor_reviews}
            combined = doctor_reviews + [r for r in unassigned if r.id not in seen]
            combined.sort(key=lambda r: r.created_at or r.updated_at, reverse=True)
            return combined
        return []

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_prompt(
        system_prompt: str,
        summary: str,
        patient_info: str,
        recent_messages: list[MessageEntity],
        new_content: str,
    ) -> str:
        """Format conversation context into a single prompt string."""
        parts = [f"System: {system_prompt}"]

        if summary:
            parts.append(f"\nConversation summary: {summary}")

        if patient_info:
            parts.append(f"\nPatient info:\n{patient_info}")

        parts.append("\nConversation history:")
        for msg in recent_messages:
            sender = "User" if msg.role == MessageRole.USER else "Assistant"
            parts.append(f"{sender}: {msg.content}")

        parts.append(f"\nUser: {new_content}")
        parts.append("Assistant:")

        return "\n".join(parts)

    @staticmethod
    def _format_patient_info(info: dict) -> str:
        """Format patient info dict into a human-readable string for the prompt."""
        lines = []
        age = info.get("age")
        gender = info.get("gender")
        if age:
            lines.append(f"- Age: {age}")
        if gender:
            lines.append(f"- Gender: {gender}")
        conditions = info.get("known_conditions", [])
        if conditions:
            lines.append(f"- Known conditions: {', '.join(conditions)}")
        meds = info.get("medications", [])
        if meds:
            lines.append(f"- Medications: {', '.join(meds)}")
        return "\n".join(lines)

    @staticmethod
    def _parse_triage(response_content: str) -> dict:
        """Extract triage assessment from the AI response.

        Looks for a JSON block of the form:
            { "urgency": "non_urgent"|"urgent"|"emergency",
              "recommendation": "free text" }

        If no JSON block is found, returns a safe default.
        """
        import json
        import re

        # Look for JSON between ```json ... ``` or { ... }
        json_pattern = re.compile(
            r"```(?:json)?\s*(\{.*?\})\s*```|\{[\s\n]*\"urgency\"[\s\n]*:",
            re.DOTALL,
        )
        match = json_pattern.search(response_content)
        if match:
            json_str = match.group(1) if match.lastindex == 1 else None
            if json_str is None:
                brace_start = match.start()
                depth = 0
                for i in range(brace_start, len(response_content)):
                    if response_content[i] == "{":
                        depth += 1
                    elif response_content[i] == "}":
                        depth -= 1
                        if depth == 0:
                            json_str = response_content[brace_start : i + 1]
                            break

            if json_str:
                try:
                    parsed = json.loads(json_str)
                    if "urgency" in parsed:
                        return {
                            "urgency": parsed.get("urgency", "unknown"),
                            "recommendation": parsed.get("recommendation", ""),
                            "category": parsed.get("category", "general"),
                        }
                except json.JSONDecodeError:
                    pass

        return {"urgency": "non_urgent", "recommendation": "Unable to determine urgency.", "category": "general"}
