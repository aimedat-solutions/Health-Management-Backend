from django.db import models


class ConversationStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    RESOLVED = "resolved", "Resolved"
    ESCALATED = "escalated_to_doctor", "Escalated to Doctor"
    ARCHIVED = "archived", "Archived"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    SYSTEM = "system", "System"
    TOOL = "tool", "Tool"


class MessageContentType(models.TextChoices):
    TEXT = "text", "Text"
    IMAGE_URL = "image_url", "Image URL"
    FILE = "file", "File"
    STRUCTURED = "structured_data", "Structured Data"


class AgentType(models.TextChoices):
    TRIAGE = "triage", "Triage Agent"
    SUMMARIZER = "summarizer", "Summarizer Agent"
    SYMPTOM_ANALYZER = "symptom_analyzer", "Symptom Analyzer"
    TRANSLATOR = "translator", "Translator"
    DIET_ADVISOR = "diet_advisor", "Diet Advisor"


class FeedbackCategory(models.TextChoices):
    HELPFUL = "helpful", "Helpful"
    INACCURATE = "inaccurate", "Inaccurate"
    CONFUSING = "confusing", "Confusing"
    INCOMPLETE = "incomplete", "Incomplete"
    HARMFUL = "harmful", "Harmful"
    OFF_TOPIC = "off_topic", "Off Topic"
    OTHER = "other", "Other"


class ReviewStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    IN_REVIEW = "in_review", "In Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    NEEDS_REVISION = "needs_revision", "Needs Revision"


class AIModelProvider(models.TextChoices):
    OPENAI = "openai", "OpenAI"
    GOOGLE = "google", "Google"
    ANTHROPIC = "anthropic", "Anthropic"
    HUGGINGFACE = "huggingface", "HuggingFace"
    OLLAMA = "ollama", "Ollama"


class ExecutionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    TIMED_OUT = "timed_out", "Timed Out"


class DocumentSource(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    KNOWLEDGE_BASE = "knowledge_base", "Knowledge Base"
    CLINICAL_GUIDELINE = "clinical_guideline", "Clinical Guideline"
    RESEARCH_PAPER = "research_paper", "Research Paper"
    PATIENT_EDUCATION = "patient_education", "Patient Education"
