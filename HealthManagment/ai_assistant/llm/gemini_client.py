from typing import Iterator, Optional

from ai_assistant.llm.base import BaseLLMClient, LLMResponse


class GeminiClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-pro",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> LLMResponse:
        model = kwargs.get("model", self._model)
        max_tokens = kwargs.get("max_tokens", self._max_tokens)
        temperature = kwargs.get("temperature", self._temperature)

        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        system_instruction = None
        if system_prompt:
            system_instruction = {"parts": [{"text": system_prompt}]}

        estimated_input = self._estimate_tokens(prompt, system_prompt)

        return LLMResponse(
            content="This is a simulated response from the Gemini provider.",
            model_used=model,
            tokens_input=estimated_input,
            tokens_output=150,
            finish_reason="stop",
            raw={"model": model, "candidates": [{"finish_reason": "STOP"}]},
        )

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Iterator[LLMResponse]:
        model = kwargs.get("model", self._model)
        chunks = ["This ", "is ", "a ", "streamed ", "Gemini ", "response."]
        for i, chunk in enumerate(chunks):
            yield LLMResponse(
                content=chunk,
                model_used=model,
                tokens_input=0,
                tokens_output=1,
                finish_reason="" if i < len(chunks) - 1 else "stop",
            )

    @staticmethod
    def _estimate_tokens(prompt: str, system_prompt: Optional[str] = None) -> int:
        text = prompt
        if system_prompt:
            text = system_prompt + "\n" + text
        return len(text) // 4 + 1
