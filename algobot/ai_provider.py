from __future__ import annotations
import json, os, urllib.error, urllib.request
from typing import Optional

class ProviderError(RuntimeError):
    pass

def _secret(name):
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None

def _value(name):
    v = os.environ.get(name) or _secret(name)
    return str(v).strip() if v else ""

class AIProvider:
    name = "base"
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

class OpenAIProvider(AIProvider):
    name = "openai"
    def __init__(self, key, model="gpt-4o-mini", timeout=60):
        self.key, self.model, self.timeout = key, model, timeout
    def generate(self, system_prompt, user_prompt):
        return _chat_completion(
            "https://api.openai.com/v1/chat/completions",
            self.key,
            self.model,
            system_prompt,
            user_prompt,
            self.timeout,
            "OpenAI",
        )


class GroqProvider(AIProvider):
    """Groq's OpenAI-compatible Chat Completions provider."""
    name = "groq"
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, key, model="openai/gpt-oss-120b", timeout=60):
        self.key, self.model, self.timeout = key, model, timeout

    def generate(self, system_prompt, user_prompt):
        return _chat_completion(
            self.BASE_URL,
            self.key,
            self.model,
            system_prompt,
            user_prompt,
            self.timeout,
            "Groq",
        )

class AnthropicProvider(AIProvider):
    name = "anthropic"
    def __init__(self, key, model="claude-sonnet-4-6", timeout=60):
        self.key, self.model, self.timeout = key, model, timeout
    def generate(self, system_prompt, user_prompt):
        body = json.dumps({"model":self.model,"max_tokens":2400,"system":system_prompt,
                           "messages":[{"role":"user","content":user_prompt}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
            headers={"Content-Type":"application/json","x-api-key":self.key,"anthropic-version":"2023-06-01"})
        data = _send(req, self.timeout, "Anthropic")
        out = "".join(x.get("text","") for x in data.get("content",[])
                      if isinstance(x,dict) and x.get("type")=="text")
        if not out: raise ProviderError("Anthropic returned no text.")
        return out.strip()

def _chat_completion(url, key, model, system_prompt, user_prompt, timeout, vendor):
    body = json.dumps({
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    data = _send(req, timeout, vendor)
    try:
        out = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        out = ""
    if not out:
        raise ProviderError(f"{vendor} returned no text.")
    return out.strip()


def _send(req, timeout, vendor):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        raise ProviderError(f"{vendor} API error: HTTP {e.code}.") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ProviderError(f"Could not reach {vendor} API.") from e
    try: return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProviderError(f"{vendor} returned invalid JSON.") from e

def get_provider() -> Optional[AIProvider]:
    # Prefer Groq when configured. This keeps the provider choice explicit
    # while preserving OpenAI/Anthropic fallbacks.
    k = _value("GROQ_API_KEY")
    if k:
        return GroqProvider(k, _value("GROQ_MODEL") or "openai/gpt-oss-120b")

    k = _value("ANTHROPIC_API_KEY")
    if k: return AnthropicProvider(k, _value("ANTHROPIC_MODEL") or "claude-sonnet-4-6")
    k = _value("OPENAI_API_KEY")
    if k: return OpenAIProvider(k, _value("OPENAI_MODEL") or "gpt-4o-mini")
    return None
