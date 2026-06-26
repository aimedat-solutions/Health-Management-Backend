"""Seeder for ``AIModel`` master data.

Idempotent — uses ``get_or_create`` by unique ``name`` so repeated
invocations do not duplicate rows.
"""

from collections.abc import Sequence

from ai_assistant.models import AIModel

_MODELS: list[dict] = [
    {
        "name": "GPT-5",
        "provider": "openai",
        "model_id": "gpt-5",
        "max_tokens": 32768,
        "temperature": 0.7,
        "cost_per_input_token": "0.00005",
        "cost_per_output_token": "0.00015",
    },
    {
        "name": "GPT-4.1",
        "provider": "openai",
        "model_id": "gpt-4.1",
        "max_tokens": 16384,
        "temperature": 0.7,
        "cost_per_input_token": "0.00003",
        "cost_per_output_token": "0.00006",
    },
    {
        "name": "GPT-4o",
        "provider": "openai",
        "model_id": "gpt-4o",
        "max_tokens": 8192,
        "temperature": 0.7,
        "cost_per_input_token": "0.000025",
        "cost_per_output_token": "0.00005",
    },
    {
        "name": "Gemini 2.5 Pro",
        "provider": "google",
        "model_id": "gemini-2.5-pro-001",
        "max_tokens": 32768,
        "temperature": 0.7,
        "cost_per_input_token": "0.000035",
        "cost_per_output_token": "0.00007",
    },
    {
        "name": "Gemini 2.5 Flash",
        "provider": "google",
        "model_id": "gemini-2.5-flash-001",
        "max_tokens": 8192,
        "temperature": 0.7,
        "cost_per_input_token": "0.00001",
        "cost_per_output_token": "0.00002",
    },
    {
        "name": "Claude Sonnet",
        "provider": "anthropic",
        "model_id": "claude-3-sonnet-20241022",
        "max_tokens": 16384,
        "temperature": 0.7,
        "cost_per_input_token": "0.00003",
        "cost_per_output_token": "0.00012",
    },
]


def seed_ai_models() -> Sequence[AIModel]:
    """Create or update the standard set of AI models.

    Returns the list of ``AIModel`` instances (existing + newly created).
    """
    created_models: list[AIModel] = []
    for data in _MODELS:
        obj, created = AIModel.objects.get_or_create(
            name=data["name"],
            defaults=data,
        )
        if not created:
            for field, value in data.items():
                setattr(obj, field, value)
            obj.save()
        created_models.append(obj)
    return created_models
