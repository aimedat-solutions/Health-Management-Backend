from collections.abc import Generator

from django.test import TestCase

from ai_assistant.llm.base import BaseLLMClient, LLMResponse


class LLMResponseTests(TestCase):
    def test_default_values(self):
        resp = LLMResponse(content="Hello", model_used="gpt-4")
        self.assertEqual(resp.content, "Hello")
        self.assertEqual(resp.model_used, "gpt-4")
        self.assertEqual(resp.tokens_input, 0)
        self.assertEqual(resp.tokens_output, 0)
        self.assertEqual(resp.finish_reason, "")
        self.assertEqual(resp.raw, {})

    def test_all_fields(self):
        resp = LLMResponse(
            content="Response text",
            model_used="gemini-pro",
            tokens_input=100,
            tokens_output=50,
            finish_reason="stop",
            raw={"key": "value"},
        )
        self.assertEqual(resp.content, "Response text")
        self.assertEqual(resp.tokens_input, 100)
        self.assertEqual(resp.tokens_output, 50)
        self.assertEqual(resp.finish_reason, "stop")
        self.assertEqual(resp.raw, {"key": "value"})


class BaseLLMClientTests(TestCase):
    def test_instantiation_raises(self):
        with self.assertRaises(TypeError):
            BaseLLMClient()

    def test_generate_stream_default(self):
        class ConcreteClient(BaseLLMClient):
            def generate(self, prompt, system_prompt=None, **kwargs):
                return LLMResponse(content="ok", model_used="test")

        client = ConcreteClient()
        gen = client.generate_stream("hello")
        self.assertIsInstance(gen, Generator)
        chunks = list(gen)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content, "")
