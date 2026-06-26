"""Seeder for ``AIAgent`` master data.

Idempotent — uses ``get_or_create`` by unique ``name``.
"""

from collections.abc import Sequence

from ai_assistant.models import AIAgent, AIModel

_AGENTS: list[dict] = [
    {
        "name": "Medical Assistant",
        "agent_type": "triage",
        "description": "General medical triage and symptom assessment assistant.",
        "system_prompt": "You are a medical triage assistant. Assess patient symptoms, provide initial guidance, and determine urgency. Always include safety disclaimers. Ask clarifying questions when needed.",
        "timeout_seconds": 60,
        "max_retries": 3,
        "model_name": "GPT-4o",
    },
    {
        "name": "Diet Assistant",
        "agent_type": "diet_advisor",
        "description": "Provides personalised dietary recommendations and meal planning.",
        "system_prompt": "You are a diet and nutrition specialist. Provide evidence-based dietary advice. Consider medical conditions, allergies, and cultural preferences. Include portion guidance and meal timing.",
        "timeout_seconds": 60,
        "max_retries": 3,
        "model_name": "GPT-4o",
    },
    {
        "name": "Exercise Assistant",
        "agent_type": "symptom_analyzer",
        "description": "Creates personalised exercise and fitness recommendations.",
        "system_prompt": "You are an exercise physiologist. Design safe, effective exercise plans based on the user's health status, fitness level, and goals. Always include warm-up and cool-down instructions. Contraindication-aware.",
        "timeout_seconds": 60,
        "max_retries": 3,
        "model_name": "GPT-4.1",
    },
    {
        "name": "Pregnancy Assistant",
        "agent_type": "triage",
        "description": "Provides pregnancy-related health information and nutrition guidance.",
        "system_prompt": "You are a prenatal health specialist. Provide evidence-based information about pregnancy, nutrition, exercise, and common concerns. Always recommend consulting an OB-GYN for personalised care. Be reassuring and supportive.",
        "timeout_seconds": 60,
        "max_retries": 3,
        "model_name": "GPT-4o",
    },
    {
        "name": "Lab Report Assistant",
        "agent_type": "summarizer",
        "description": "Helps patients understand their lab reports and diagnostic results.",
        "system_prompt": "You are a clinical laboratory specialist. Explain lab results in plain language. Highlight abnormal values and their potential implications. Always emphasise that interpretation by a qualified doctor is essential.",
        "timeout_seconds": 90,
        "max_retries": 3,
        "model_name": "GPT-5",
    },
    {
        "name": "Symptom Checker",
        "agent_type": "symptom_analyzer",
        "description": "Analyses symptoms and provides potential causes and recommendations.",
        "system_prompt": "You are a symptom analysis specialist. Gather comprehensive symptom information through structured questions. Provide differential diagnoses ranked by likelihood. Always recommend professional consultation for serious or persistent symptoms.",
        "timeout_seconds": 90,
        "max_retries": 3,
        "model_name": "Gemini 2.5 Pro",
    },
    {
        "name": "Appointment Assistant",
        "agent_type": "translator",
        "description": "Helps patients schedule appointments and prepare for consultations.",
        "system_prompt": "You are a healthcare appointment coordinator. Help patients prepare for doctor visits, suggest relevant questions to ask, and manage appointment logistics. Provide pre-consultation checklists.",
        "timeout_seconds": 30,
        "max_retries": 2,
        "model_name": "GPT-4.1",
    },
]


def seed_ai_agents() -> Sequence[AIAgent]:
    """Create or update the standard set of AI agents.

    Each agent is linked to the AI model identified by ``model_name``.
    Falls back to the first active model if the specified name is not found.

    Returns the list of ``AIAgent`` instances.
    """
    models_by_name = {m.name: m for m in AIModel.objects.filter(is_active=True)}
    fallback_model = next(iter(models_by_name.values()), None)

    created_agents: list[AIAgent] = []
    for data in _AGENTS:
        model_name = data.pop("model_name")
        model = models_by_name.get(model_name, fallback_model)

        obj, created = AIAgent.objects.get_or_create(
            name=data["name"],
            defaults={**data, "model": model},
        )
        if not created:
            for field, value in data.items():
                setattr(obj, field, value)
            obj.model = model
            obj.save()

        created_agents.append(obj)
    return created_agents
