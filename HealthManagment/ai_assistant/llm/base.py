from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    content: str
    model_used: str
    tokens_input: int = 0
    tokens_output: int = 0
    finish_reason: str = ""
    raw: dict = field(default_factory=dict)


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        ...

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs):
        yield LLMResponse(content="", model_used="", tokens_input=0, tokens_output=0)
