"""Management command to seed the AI Assistant database with realistic
healthcare development data.

Usage::

    python manage.py seed_database                     # defaults (10 patients)
    python manage.py seed_database --patients=25        # 25 patients
    python manage.py seed_database --conversations=5    # 5 convs per patient
    python manage.py seed_database --messages=8         # 8 msgs per conv
    python manage.py seed_database --flush              # wipe before seeding
    python manage.py seed_database --flush --noinput    # skip confirmation

Execution order:

1. Flush existing data (if ``--flush``).
2. Seed AI models (idempotent master data).
3. Seed AI agents (idempotent master data, linked to models).
4. Seed patient & doctor users.
5. Seed conversations.
6. Seed messages.
7. Seed agent executions.
8. Seed message feedback.
9. Seed doctor reviews.

The entire operation runs inside a single transaction for atomicity.
"""

import logging
import time
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from ai_assistant.models import (
    AIAgent,
    AIModel,
    AgentExecution,
    Conversation,
    DoctorReview,
    Message,
    MessageFeedback,
)
from ai_assistant.seeders.ai_agent_seeder import seed_ai_agents
from ai_assistant.seeders.ai_model_seeder import seed_ai_models
from ai_assistant.seeders.agent_execution_seeder import seed_agent_executions
from ai_assistant.seeders.conversation_seeder import seed_conversations
from ai_assistant.seeders.feedback_seeder import seed_feedback
from ai_assistant.seeders.message_seeder import seed_messages
from ai_assistant.seeders.review_seeder import seed_reviews
from ai_assistant.seeders.user_seeder import seed_users

logger = logging.getLogger(__name__)

_MODEL_DELETION_ORDER = [
    DoctorReview,
    MessageFeedback,
    AgentExecution,
    Message,
    Conversation,
    AIAgent,
    AIModel,
]


class Command(BaseCommand):
    help = "Seed the database with realistic AI assistant development data."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--patients",
            type=int,
            default=10,
            help="Number of patient users to create (default: 10).",
        )
        parser.add_argument(
            "--doctors",
            type=int,
            default=5,
            help="Number of doctor users to create (default: 5).",
        )
        parser.add_argument(
            "--conversations",
            type=int,
            default=3,
            help="Conversations per patient (default: 3).",
        )
        parser.add_argument(
            "--messages",
            type=int,
            default=5,
            help="Messages per conversation (default: 5).",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing AI assistant data before seeding.",
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Skip confirmation prompt when used with --flush.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        start = time.perf_counter()

        if options["flush"]:
            self._flush(options["noinput"])

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding AI Assistant database"))
        self.stdout.write("")

        with transaction.atomic():
            self._seed_section("AI Models", self._seed_models)
            self._seed_section("AI Agents", self._seed_agents)
            self._seed_section("Users", self._seed_users, options)
            self._seed_section("Conversations", self._seed_conversations, options)
            self._seed_section("Messages", self._seed_messages, options)
            self._seed_section("Agent Executions", self._seed_executions)
            self._seed_section("Message Feedback", self._seed_feedback)
            self._seed_section("Doctor Reviews", self._seed_reviews)

        elapsed = time.perf_counter() - start
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Seeding completed in {elapsed:.2f}s")
        )

    # ── internal helpers ────────────────────────────────────────────────

    def _flush(self, noinput: bool) -> None:
        """Delete all AI assistant data in reverse-dependency order."""
        if not noinput:
            confirm = input(
                "This will DELETE all existing AI assistant data.\n"
                "Are you sure? [y/N]: "
            )
            if confirm.lower() not in ("y", "yes"):
                self.stdout.write(self.style.WARNING("Flush cancelled."))
                return

        self.stdout.write(self.style.WARNING("Flushing existing data..."))
        for model in _MODEL_DELETION_ORDER:
            count = model.objects.count()
            if count:
                model.objects.all().delete()
                self.stdout.write(f"  Deleted {count} {model.__name__} record(s)")
        self.stdout.write("")

    def _seed_section(self, label: str, fn: callable, options: dict | None = None) -> None:
        """Execute a seeder function and report its result."""
        self.stdout.write(self.style.MIGRATE_LABEL(f"  {label}..."), ending="")
        self.stdout.flush()
        try:
            result = fn(**(options or {}))
            count = len(result) if hasattr(result, "__len__") else (result or 0)
            self.stdout.write(self.style.SUCCESS(f" {count} created"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f" FAILED"))
            self.stderr.write(self.style.ERROR(f"    {exc}"))
            raise

    # ── seeder wrappers (capture return values for later seeders) ────────

    def _seed_models(self) -> int:
        models = seed_ai_models()
        self._models = models
        return len(models)

    def _seed_agents(self) -> int:
        agents = seed_ai_agents()
        self._agents = agents
        return len(agents)

    def _seed_users(self, **options: Any) -> int:
        patients, doctors = seed_users(
            patient_count=options.get("patients", 10),
            doctor_count=options.get("doctors", 5),
        )
        self._patients = patients
        self._doctors = doctors
        return len(patients) + len(doctors)

    def _seed_conversations(self, **options: Any) -> int:
        conversations = seed_conversations(
            patients=self._patients,
            models=self._models,
            conversations_per_patient=options.get("conversations", 3),
        )
        self._conversations = conversations
        return len(conversations)

    def _seed_messages(self, **options: Any) -> int:
        messages = seed_messages(
            conversations=self._conversations,
            messages_per_conversation=options.get("messages", 5),
        )
        self._messages = messages
        return len(messages)

    def _seed_executions(self) -> int:
        executions = seed_agent_executions(
            messages=self._messages,
            agents=self._agents,
        )
        return len(executions)

    def _seed_feedback(self) -> int:
        feedback = seed_feedback(
            messages=self._messages,
            patients=self._patients,
        )
        return len(feedback)

    def _seed_reviews(self) -> int:
        reviews = seed_reviews(
            conversations=self._conversations,
            doctors=self._doctors,
        )
        return len(reviews)
