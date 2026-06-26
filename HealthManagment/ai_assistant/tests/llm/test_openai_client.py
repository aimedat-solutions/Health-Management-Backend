from collections.abc import Generator

from django.test import TestCase

from ai_assistant.llm.openai_client import OpenAIClient


class OpenAIClientTests(TestCase):
    def setUp(self):
        self.client = OpenAIClient(api_key="sk-test")

    def test_default_constructor(self):
        self.assertEqual(self.client._model, "gpt-4o")
        self.assertEqual(self.client._max_tokens, 4096)
        self.assertEqual(self.client._temperature, 0.7)

    def test_custom_constructor(self):
        client = OpenAIClient(api_key="sk-test", model="gpt-3.5", max_tokens=2048, temperature=0.5)
        self.assertEqual(client._model, "gpt-3.5")
        self.assertEqual(client._max_tokens, 2048)
        self.assertEqual(client._temperature, 0.5)

    def test_generate_returns_llm_response(self):
        resp = self.client.generate("Hello")
        self.assertEqual(resp.model_used, "gpt-4o")
        self.assertIn("simulated response", resp.content)
        self.assertGreater(resp.tokens_input, 0)
        self.assertEqual(resp.tokens_output, 150)
        self.assertEqual(resp.finish_reason, "stop")

    def test_generate_with_system_prompt(self):
        resp = self.client.generate("Hello", system_prompt="Be helpful.")
        self.assertIn("simulated response", resp.content)
        self.assertGreater(resp.tokens_input, 0)

    def test_generate_with_custom_kwargs(self):
        resp = self.client.generate("Hello", model="gpt-4-turbo", max_tokens=2048, temperature=0.3)
        self.assertEqual(resp.model_used, "gpt-4-turbo")

    def test_generate_stream_returns_generator(self):
        gen = self.client.generate_stream("Hello")
        self.assertIsInstance(gen, Generator)
        chunks = list(gen)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertIsNotNone(chunk.content)
        self.assertEqual(chunks[-1].finish_reason, "stop")

    def test_generate_stream_with_system_prompt(self):
        gen = self.client.generate_stream("Hello", system_prompt="Be brief.")
        chunks = list(gen)
        self.assertGreater(len(chunks), 0)

    def test_estimate_tokens_empty(self):
        self.assertEqual(OpenAIClient._estimate_tokens(""), 1)

    def test_estimate_tokens_with_text(self):
        result = OpenAIClient._estimate_tokens("Hello world", system_prompt="System")
        self.assertGreater(result, 0)

    def test_api_key_stored(self):
        client = OpenAIClient(api_key="sk-secret-123")
        self.assertEqual(client._api_key, "sk-secret-123")
