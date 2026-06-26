"""Seeder for ``AgentExecution`` records.

Creates executions for a subset of AI assistant messages, covering
completed, failed, running, and timed-out states.
"""

import random
from collections.abc import Sequence
from typing import Optional

from django.utils import timezone

from ai_assistant.enums import ExecutionStatus
from ai_assistant.models import AIAgent, AgentExecution, Message
from ai_assistant.seeders.healthcare_data import AGENT_INPUT_TEMPLATES

_EXECUTION_STATUS_WEIGHTS: dict[str, float] = {
    ExecutionStatus.COMPLETED: 0.65,
    ExecutionStatus.FAILED: 0.15,
    ExecutionStatus.RUNNING: 0.10,
    ExecutionStatus.TIMED_OUT: 0.05,
    ExecutionStatus.PENDING: 0.05,
}

_ERROR_MESSAGES: list[str] = [
    "LLM provider returned a 503 Service Unavailable after 3 retries.",
    "Token limit exceeded for the requested model (max 8192 tokens).",
    "Response parsing failed: unexpected JSON structure in LLM output.",
    "Rate limit exceeded for the API key. Retry after 60 seconds.",
    "Context window overflow: conversation history exceeds model limit.",
]


def seed_agent_executions(
    messages: Sequence[Message],
    agents: Sequence[AIAgent],
    probability: float = 0.4,
) -> list[AgentExecution]:
    """Create agent executions for a random subset of AI assistant messages.

    *probability* controls how many assistant messages get an execution
    (default 40 %).

    Returns the list of created ``AgentExecution`` instances.
    """
    executions: list[AgentExecution] = []
    assistant_messages = [m for m in messages if m.role == "assistant"]

    if not assistant_messages:
        return executions

    candidates = random.sample(
        assistant_messages,
        k=max(1, int(len(assistant_messages) * probability)),
    )

    statuses = list(_EXECUTION_STATUS_WEIGHTS.keys())
    weights = list(_EXECUTION_STATUS_WEIGHTS.values())

    for msg in candidates:
        agent = random.choice(agents) if agents else None
        status = random.choices(statuses, weights=weights, k=1)[0]

        template = random.choice(AGENT_INPUT_TEMPLATES) if status != ExecutionStatus.FAILED else {}

        started = msg.created_at
        duration = random.randint(5, 120)
        completed = (
            started + timezone.timedelta(seconds=duration)
            if status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT)
            else None
        )

        error_message = ""
        if status in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT):
            error_message = random.choice(_ERROR_MESSAGES)

        execution = AgentExecution.objects.create(
            agent=agent,
            conversation=msg.conversation,
            message=msg,
            execution_id=f"exec_{msg.id}_{timezone.now().timestamp()}",
            status=status,
            input_data=template.get("input", {}),
            output_data=template.get("output", {}),
            error_message=error_message,
            tokens_used=random.randint(50, 2000) if status == ExecutionStatus.COMPLETED else 0,
            started_at=started,
            completed_at=completed,
        )
        executions.append(execution)

    return executions
