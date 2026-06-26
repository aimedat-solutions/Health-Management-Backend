"""
Triage analysis service.

``TriageService`` evaluates conversation content for medical urgency.
In v1 it uses rule-based pattern matching.  In future versions it can
delegate to a dedicated LLM agent for more accurate assessment.
"""

import logging
import re
from typing import Optional

from ai_assistant.domain.entities.conversation import ConversationEntity, MessageEntity
from ai_assistant.domain.interfaces.repositories import MessageRepository

logger = logging.getLogger(__name__)


# ── DTO ──────────────────────────────────────────────────────────────────────


class TriageResult:
    """Structured outcome of a triage analysis."""

    URGENCY_LEVELS = frozenset({"non_urgent", "urgent", "emergency"})

    def __init__(
        self,
        urgency: str = "non_urgent",
        recommendation: str = "",
        category: str = "general",
        confidence: float = 0.0,
    ) -> None:
        if urgency not in self.URGENCY_LEVELS:
            raise ValueError(f"Invalid urgency '{urgency}'. Must be one of {self.URGENCY_LEVELS}.")
        self.urgency = urgency
        self.recommendation = recommendation
        self.category = category
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "urgency": self.urgency,
            "recommendation": self.recommendation,
            "category": self.category,
            "confidence": self.confidence,
        }

    def __repr__(self) -> str:
        return f"TriageResult(urgency={self.urgency}, category={self.category})"


# ── Service ──────────────────────────────────────────────────────────────────


class TriageService:
    """Analyse conversation content for medical urgency.

    The service operates in two modes:
    1. **Reactive** — analyse a batch of messages (e.g. before escalation).
    2. **Inline** — extract urgency from the AI response (used by
       ``ConsultationService._execute_ai_pipeline``).
    """

    # Emergency keywords — match against lowercased message content.
    _EMERGENCY_KEYWORDS: tuple[str, ...] = (
        "chest pain",
        "difficulty breathing",
        "shortness of breath",
        "unconscious",
        "severe bleeding",
        "head injury",
        "stroke",
        "seizure",
        "suicidal",
        "overdose",
        "allergic reaction",
        "anaphylaxis",
        "heart attack",
    )

    def __init__(
        self,
        message_repo: Optional[MessageRepository] = None,
    ) -> None:
        self._message_repo = message_repo

    def analyze_recent_messages(
        self,
        conversation: ConversationEntity,
        max_messages: int = 10,
    ) -> TriageResult:
        """Analyse the most recent messages for urgency signals.

        Uses keyword-matching as a fast first-pass filter.  If an emergency
        keyword is found, the result is ``emergency``.  If urgent-sounding
        language is detected, the result is ``urgent``.  Otherwise ``non_urgent``.

        The ``confidence`` field reflects how many signals matched.
        """
        if self._message_repo is None:
            return TriageResult()

        recent = self._message_repo.get_last_n(conversation.id, n=max_messages)
        combined = " ".join(m.content.lower() for m in recent if m.role == "user")

        return self._score_content(combined)

    def analyze_content(self, content: str) -> TriageResult:
        """Analyse a single text string (e.g. the latest user message)."""
        return self._score_content(content.lower())

    def _score_content(self, text: str) -> TriageResult:
        """Score ``text`` against emergency and urgency signals."""
        if not text.strip():
            return TriageResult()

        emergency_hits = 0
        urgent_hints = 0

        for keyword in self._EMERGENCY_KEYWORDS:
            if keyword in text:
                emergency_hits += 1

        # Urgency signals (less severe than keyword hits).
        if re.search(r"\b(severe|worsening|unbearable|extreme)\b", text):
            urgent_hints += 1
        if re.search(r"\b(days|weeks)\s+of\b", text) and re.search(r"\b(pain|fever|symptom)\b", text):
            urgent_hints += 1
        if re.search(r"\b(not\s+improving|getting\s+worse|no\s+better)\b", text):
            urgent_hints += 1

        if emergency_hits > 0:
            return TriageResult(
                urgency="emergency",
                recommendation="Emergency keywords detected. Immediate medical attention advised.",
                confidence=min(0.5 + emergency_hits * 0.2, 1.0),
            )
        if urgent_hints >= 2:
            return TriageResult(
                urgency="urgent",
                recommendation="Multiple urgency signals detected. Prompt medical consultation recommended.",
                confidence=0.6,
            )
        if urgent_hints == 1:
            return TriageResult(
                urgency="urgent",
                recommendation="Urgency signal detected. Patient should monitor closely.",
                confidence=0.4,
            )

        return TriageResult(
            urgency="non_urgent",
            recommendation="No urgency signals detected. Routine advice appropriate.",
            confidence=0.9,
        )
