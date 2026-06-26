"""Seeder for ``Message`` records.

Builds multi-message conversations from the healthcare conversation
templates.  Every last AI message in an active conversation is tagged
so the feedback / agent-execution seeders can find candidates.
"""

import random
from collections.abc import Sequence

from django.utils import timezone

from ai_assistant.enums import MessageRole
from ai_assistant.models import Conversation, Message
from ai_assistant.seeders.healthcare_data import CONVERSATION_TEMPLATES


def seed_messages(
    conversations: Sequence[Conversation],
    messages_per_conversation: int = 5,
) -> list[Message]:
    """Populate each conversation with realistic messages.

    For each conversation a matching template is looked up by title;
    if found the template's messages are used, otherwise random messages
    are generated.  The last AI message in each conversation is recorded
    in ``last_ai_messages`` for downstream seeders.

    Returns the full list of created ``Message`` instances.
    """
    all_messages: list[Message] = []
    now = timezone.now()

    for conv in conversations:
        template = _find_template(conv.title)
        if template:
            conv_messages = _from_template(conv, template)
        else:
            conv_messages = _random_messages(conv, messages_per_conversation)

        for i, msg in enumerate(conv_messages):
            msg.created_at = now - timezone.timedelta(
                minutes=(len(conv_messages) - i) * random.randint(2, 15),
            )
            msg.save()

        all_messages.extend(conv_messages)

        if conv.message_count != len(conv_messages):
            Message.objects.filter(conversation=conv).update(
                conversation_id=conv.pk,
            )

    return all_messages


def _find_template(title: str) -> dict | None:
    """Return the first template whose title (without patient name) is
    contained in the conversation title."""
    for t in CONVERSATION_TEMPLATES:
        base = t["title"].split("{patient_name}")[0].strip() if "{patient_name}" in t["title"] else t["title"]
        if base and base in title:
            return t
    return None


def _from_template(conv: Conversation, template: dict) -> list[Message]:
    """Build messages from a conversation template."""
    messages: list[Message] = []
    for role, content in template["messages"]:
        messages.append(
            Message(
                conversation=conv,
                role=role,
                content_type="text",
                content=content,
                tokens=len(content.split()),
            )
        )
    return messages


def _random_messages(conv: Conversation, count: int) -> list[Message]:
    """Build messages for conversations that don't match a template."""
    from ai_assistant.seeders.healthcare_data import (
        DIET_QUESTIONS,
        DIET_RESPONSES,
        DOCTOR_RESPONSES,
        EXERCISE_QUESTIONS,
        EXERCISE_RESPONSES,
        LAB_REPORT_QUESTIONS,
        LAB_REPORT_RESPONSES,
        PATIENT_COMPLAINTS,
        SYMPTOM_DETAILS,
    )

    topics = [
        (PATIENT_COMPLAINTS, DOCTOR_RESPONSES),
        (DIET_QUESTIONS, DIET_RESPONSES),
        (EXERCISE_QUESTIONS, EXERCISE_RESPONSES),
        (LAB_REPORT_QUESTIONS, LAB_REPORT_RESPONSES),
    ]

    topic = random.choice(topics)
    messages: list[Message] = []

    user_msg = Message(
        conversation=conv,
        role=MessageRole.USER,
        content_type="text",
        content=random.choice(topic[0]),
        tokens=random.randint(15, 80),
    )
    messages.append(user_msg)

    for _ in range(1, count):
        if len(messages) % 2 == 1:
            role = MessageRole.ASSISTANT
            content = random.choice(topic[1])
        else:
            role = MessageRole.USER
            content = random.choice(SYMPTOM_DETAILS)

        messages.append(
            Message(
                conversation=conv,
                role=role,
                content_type="text",
                content=content,
                tokens=len(content.split()),
            )
        )

    if len(messages) == count and messages[-1].role == MessageRole.USER:
        messages.append(
            Message(
                conversation=conv,
                role=MessageRole.ASSISTANT,
                content_type="text",
                content=random.choice(DOCTOR_RESPONSES),
                tokens=random.randint(20, 60),
            )
        )

    if count > len(messages):
        messages.append(
            Message(
                conversation=conv,
                role=MessageRole.SYSTEM,
                content_type="text",
                content="This conversation has been automatically summarized and archived.",
                hidden_from_patient=True,
                tokens=10,
            )
        )

    return messages
