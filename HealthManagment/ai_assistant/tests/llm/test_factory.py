from django.test import TestCase

from ai_assistant.llm import LLMClientFactory
from ai_assistant.llm.gemini_client import GeminiClient
from ai_assistant.llm.openai_client import OpenAIClient


class LLMClientFactoryTests(TestCase):
    def test_create_openai(self):
        client = LLMClientFactory.create("openai", api_key="sk-test")
        self.assertIsInstance(client, OpenAIClient)
        self.assertEqual(client._api_key, "sk-test")

    def test_create_gemini(self):
        client = LLMClientFactory.create("gemini", api_key="gem-test")
        self.assertIsInstance(client, GeminiClient)
        self.assertEqual(client._api_key, "gem-test")

    def test_create_google_alias(self):
        client = LLMClientFactory.create("google", api_key="gem-test")
        self.assertIsInstance(client, GeminiClient)

    def test_create_openai_with_kwargs(self):
        client = LLMClientFactory.create("openai", api_key="sk-test", model="gpt-4", max_tokens=2048)
        self.assertEqual(client._model, "gpt-4")
        self.assertEqual(client._max_tokens, 2048)

    def test_create_gemini_with_kwargs(self):
        client = LLMClientFactory.create("gemini", api_key="gem-test", model="gemini-pro", temperature=0.3)
        self.assertEqual(client._model, "gemini-pro")
        self.assertEqual(client._temperature, 0.3)

    def test_unsupported_provider_raises(self):
        with self.assertRaises(ValueError) as ctx:
            LLMClientFactory.create("claude", api_key="key")
        self.assertIn("claude", str(ctx.exception))
        self.assertIn("openai", str(ctx.exception))

    def test_case_insensitive_provider(self):
        client = LLMClientFactory.create("OpenAI", api_key="sk-test")
        self.assertIsInstance(client, OpenAIClient)
