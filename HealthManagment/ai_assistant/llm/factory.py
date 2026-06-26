from ai_assistant.llm.base import BaseLLMClient
from ai_assistant.llm.gemini_client import GeminiClient
from ai_assistant.llm.openai_client import OpenAIClient


class LLMClientFactory:
    _PROVIDER_MAP = {
        "openai": OpenAIClient,
        "gemini": GeminiClient,
        "google": GeminiClient,
    }

    @classmethod
    def create(cls, provider: str, api_key: str, **kwargs) -> BaseLLMClient:
        client_cls = cls._PROVIDER_MAP.get(provider.lower())
        if client_cls is None:
            raise ValueError(
                f"Unsupported LLM provider '{provider}'. "
                f"Supported: {', '.join(sorted(cls._PROVIDER_MAP))}."
            )
        return client_cls(api_key=api_key, **kwargs)
