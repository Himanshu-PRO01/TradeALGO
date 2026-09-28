import json
import os

import pytest

from algobot.ai_provider import GroqProvider, ProviderError, get_provider


def test_groq_is_preferred_when_configured(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    provider = get_provider()

    assert isinstance(provider, GroqProvider)
    assert provider.model == "openai/gpt-oss-20b"
    assert provider.key == "test-groq-key"


def test_groq_uses_default_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    provider = get_provider()

    assert isinstance(provider, GroqProvider)
    assert provider.model == "openai/gpt-oss-120b"


def test_groq_provider_does_not_put_key_in_provider_errors(monkeypatch):
    provider = GroqProvider("secret-groq-key", "openai/gpt-oss-120b")

    def fail(*args, **kwargs):
        raise ProviderError("Groq API error: HTTP 401.")

    monkeypatch.setattr("algobot.ai_provider._send", fail)

    with pytest.raises(ProviderError) as exc:
        provider.generate("system", "user")

    assert "secret-groq-key" not in str(exc.value)
