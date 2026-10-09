import json
import os

import pytest

from algobot.ai_provider import (
    FallbackProvider,
    GeminiProvider,
    GrokProvider,
    GroqProvider,
    ProviderError,
    _find_gemini_key,
    _find_grok_key,
    _find_groq_key,
    get_provider,
)


def test_gemini_is_preferred_when_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-gemini-key")
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    provider = get_provider()

    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-2.5-flash"
    assert provider.key == "AIza-test-gemini-key"


def test_dual_provider_fallback_when_both_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-groq-key")
    monkeypatch.delenv("GROK_API_KEY", raising=False)

    provider = get_provider()
    assert isinstance(provider, FallbackProvider)
    assert len(provider.providers) == 2
    assert isinstance(provider.providers[0], GeminiProvider)
    assert isinstance(provider.providers[1], GroqProvider)

    # Test automatic failover when Gemini runs out of tokens
    def gemini_fail(*args, **kwargs):
        raise ProviderError("Gemini out of tokens: HTTP 429 quota exhausted.")

    def groq_ok(*args, **kwargs):
        return "```yaml\nindicators: []\n```\nGroq strategy rules."

    monkeypatch.setattr(provider.providers[0], "generate_vision", gemini_fail)
    monkeypatch.setattr(provider.providers[1], "generate_vision", groq_ok)

    result = provider.generate_vision("system", "user", b"image")
    assert "Groq strategy rules" in result


def test_find_gemini_key_discovers_from_secret_yml(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    secret_file = tmp_path / "secret.yml"
    secret_file.write_text("GEMINI_API_KEY: 'AIzaSecretYamlKey'\n")

    monkeypatch.chdir(tmp_path)
    assert _find_gemini_key() == "AIzaSecretYamlKey"


def test_find_groq_key_discovers_from_secret_yml(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    secret_file = tmp_path / "secret.yml"
    secret_file.write_text("GROQ_API_KEY: 'gsk_SecretYamlGroqKey'\n")

    monkeypatch.chdir(tmp_path)
    assert _find_groq_key() == "gsk_SecretYamlGroqKey"


def test_grok_is_preferred_when_configured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GROK_API_KEY", "xai-test-grok-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    provider = get_provider()

    assert isinstance(provider, GrokProvider)
    assert provider.model == "grok-4.5"
    assert provider.key == "xai-test-grok-key"


def test_find_grok_key_discovers_xai_prefixed_env_and_grok_names(monkeypatch):
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.setenv("CUSTOM_AI_KEY", "xai-12345-grok")
    assert _find_grok_key() == "xai-12345-grok"

    monkeypatch.delenv("CUSTOM_AI_KEY")
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")
    assert _find_grok_key() == "test-xai-key"


def test_grok_provider_does_not_put_key_in_provider_errors(monkeypatch):
    provider = GrokProvider("secret-grok-key", "grok-2-vision-1212")

    def fail(*args, **kwargs):
        raise ProviderError("Grok API error: HTTP 401.")

    monkeypatch.setattr("algobot.ai_provider._send", fail)

    with pytest.raises(ProviderError) as exc:
        provider.generate("system", "user")

    assert "secret-grok-key" not in str(exc.value)


def test_groq_is_preferred_when_configured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    provider = get_provider()

    assert isinstance(provider, GroqProvider)
    assert provider.model == "openai/gpt-oss-20b"
    assert provider.key == "test-groq-key"


def test_groq_uses_default_model(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
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


def test_get_ai_status_and_aliases(monkeypatch):
    from algobot.ai_provider import (
        find_gemini_key,
        find_groq_key,
        get_ai_status,
    )

    monkeypatch.setenv("GEMINI_API_KEY", "AIzaTestKey")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_TestGroqKey")

    assert find_gemini_key() == "AIzaTestKey"
    assert find_groq_key() == "gsk_TestGroqKey"

    st = get_ai_status()
    assert st["gemini_connected"] is True
    assert st["groq_connected"] is True
    assert st["dual_active"] is True
    assert st["primary"] == "gemini"
    assert st["backup"] == "groq"


def test_cross_key_collision_protection(tmp_path, monkeypatch):
    from algobot.ai_provider import _find_gemini_key, _find_groq_key

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    # File with generic API_KEY pointing to a Groq key
    secret_file = tmp_path / "secret.yml"
    secret_file.write_text("API_KEY: 'gsk_SomeGroqKey'\n")

    monkeypatch.chdir(tmp_path)
    # Gemini must NOT steal the Groq key
    assert _find_gemini_key() == ""
    # Groq MUST recognize it
    assert _find_groq_key() == "gsk_SomeGroqKey"

    # Now change to an AIza key
    secret_file.write_text("API_KEY: 'AIzaSomeGeminiKey'\n")
    # Gemini MUST recognize it
    assert _find_gemini_key() == "AIzaSomeGeminiKey"
    # Groq must NOT steal it
    assert _find_groq_key() == ""

