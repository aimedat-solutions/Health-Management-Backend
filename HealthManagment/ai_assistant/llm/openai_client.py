from typing import Iterator, Optional

from ai_assistant.llm.base import BaseLLMClient, LLMResponse


class OpenAIClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
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

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        estimated_input = self._estimate_tokens(prompt, system_prompt)

        return LLMResponse(
            content="This is a simulated response from the OpenAI provider.",
            model_used=model,
            tokens_input=estimated_input,
            tokens_output=150,
            finish_reason="stop",
            raw={"model": model, "object": "chat.completion", "choices": [{"index": 0, "finish_reason": "stop"}]},
        )

    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Iterator[LLMResponse]:
        model = kwargs.get("model", self._model)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        chunks = ["This ", "is ", "a ", "streamed ", "OpenAI ", "response."]
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
