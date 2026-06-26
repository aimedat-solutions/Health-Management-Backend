from collections.abc import Generator

from django.test import TestCase

from ai_assistant.llm.gemini_client import GeminiClient


class GeminiClientTests(TestCase):
    def setUp(self):
        self.client = GeminiClient(api_key="gem-test")

    def test_default_constructor(self):
        self.assertEqual(self.client._model, "gemini-1.5-pro")
        self.assertEqual(self.client._max_tokens, 4096)
        self.assertEqual(self.client._temperature, 0.7)

    def test_custom_constructor(self):
        client = GeminiClient(api_key="gem-test", model="gemini-pro", max_tokens=2048, temperature=0.5)
        self.assertEqual(client._model, "gemini-pro")
        self.assertEqual(client._max_tokens, 2048)
        self.assertEqual(client._temperature, 0.5)

    def test_generate_returns_llm_response(self):
        resp = self.client.generate("Hello")
        self.assertEqual(resp.model_used, "gemini-1.5-pro")
        self.assertIn("simulated response", resp.content)
        self.assertGreater(resp.tokens_input, 0)
        self.assertEqual(resp.tokens_output, 150)
        self.assertEqual(resp.finish_reason, "stop")

    def test_generate_with_system_prompt(self):
        resp = self.client.generate("Hello", system_prompt="Be helpful.")
        self.assertIn("simulated response", resp.content)
        self.assertGreater(resp.tokens_input, 0)

    def test_generate_with_custom_kwargs(self):
        resp = self.client.generate("Hello", model="gemini-ultra", max_tokens=8192, temperature=0.1)
        self.assertEqual(resp.model_used, "gemini-ultra")

    def test_generate_stream_returns_generator(self):
        gen = self.client.generate_stream("Hello")
        self.assertIsInstance(gen, Generator)
        chunks = list(gen)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[-1].finish_reason, "stop")

    def test_generate_stream_with_system_prompt(self):
        gen = self.client.generate_stream("Hello", system_prompt="Be brief.")
        chunks = list(gen)
        self.assertGreater(len(chunks), 0)

    def test_estimate_tokens_empty(self):
        self.assertEqual(GeminiClient._estimate_tokens(""), 1)

    def test_estimate_tokens_with_text(self):
        result = GeminiClient._estimate_tokens("Hello world", system_prompt="System")
        self.assertGreater(result, 0)

    def test_api_key_stored(self):
        client = GeminiClient(api_key="gem-secret-456")
        self.assertEqual(client._api_key, "gem-secret-456")
