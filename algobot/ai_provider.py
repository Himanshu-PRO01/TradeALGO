from __future__ import annotations
import base64
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

    def generate_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        raise NotImplementedError(f"{self.name} does not support vision/image analysis.")

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

    def generate_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        body = json.dumps({
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                    ],
                },
            ],
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.key}",
                "User-Agent": "TradeALGO/1.0",
            },
        )
        data = _send(req, self.timeout, "OpenAI")
        try:
            out = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            out = ""
        if not out:
            raise ProviderError("OpenAI returned no text.")
        return out.strip()


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
            headers={"Content-Type":"application/json","x-api-key":self.key,"anthropic-version":"2023-06-01","User-Agent":"TradeALGO/1.0"})
        data = _send(req, self.timeout, "Anthropic")
        out = "".join(x.get("text","") for x in data.get("content",[])
                      if isinstance(x,dict) and x.get("type")=="text")
        if not out: raise ProviderError("Anthropic returned no text.")
        return out.strip()

    def generate_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        body = json.dumps({
            "model": self.model,
            "max_tokens": 2400,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                        {"type": "text", "text": user_prompt},
                    ],
                }
            ],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.key,
                "anthropic-version": "2023-06-01",
                "User-Agent": "TradeALGO/1.0",
            },
        )
        data = _send(req, self.timeout, "Anthropic")
        out = "".join(x.get("text", "") for x in data.get("content", []) if isinstance(x, dict) and x.get("type") == "text")
        if not out:
            raise ProviderError("Anthropic returned no text.")
        return out.strip()


class GeminiProvider(AIProvider):
    name = "gemini"
    def __init__(self, key, model="gemini-2.5-flash", timeout=60):
        self.key, self.model, self.timeout = key, model, timeout

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.key}"
        body = json.dumps({
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
        }).encode()
        req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "User-Agent": "TradeALGO/1.0"})
        data = _send(req, self.timeout, "Gemini")
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            raise ProviderError("Gemini returned invalid response structure.") from e

    def generate_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.key}"
        body = json.dumps({
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{
                "parts": [
                    {"text": user_prompt},
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                ]
            }],
        }).encode()
        req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "User-Agent": "TradeALGO/1.0"})
        data = _send(req, self.timeout, "Gemini")
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            raise ProviderError("Gemini returned invalid response structure.") from e


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
            "User-Agent": "TradeALGO/1.0",
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

def get_provider(custom_key: str = "", provider_name: str = "") -> Optional[AIProvider]:
    if custom_key:
        pname = (provider_name or "").lower().strip()
        if "gemini" in pname:
            return GeminiProvider(custom_key)
        if "groq" in pname:
            return GroqProvider(custom_key)
        if "anthropic" in pname or "claude" in pname:
            return AnthropicProvider(custom_key)
        return OpenAIProvider(custom_key)

    # Prefer Groq when configured. This keeps the provider choice explicit
    # while preserving OpenAI/Anthropic/Gemini fallbacks.
    k = _value("GROQ_API_KEY")
    if k:
        return GroqProvider(k, _value("GROQ_MODEL") or "openai/gpt-oss-120b")

    k = _value("GEMINI_API_KEY")
    if k:
        return GeminiProvider(k, _value("GEMINI_MODEL") or "gemini-2.5-flash")

    k = _value("ANTHROPIC_API_KEY")
    if k: return AnthropicProvider(k, _value("ANTHROPIC_MODEL") or "claude-sonnet-4-6")
    k = _value("OPENAI_API_KEY")
    if k: return OpenAIProvider(k, _value("OPENAI_MODEL") or "gpt-4o-mini")
    return None


def read_strategy_image(image_bytes: bytes, mime_type: str = "image/png", custom_key: str = "", provider_name: str = "") -> dict:
    """Reads a strategy photo/screenshot and extracts strict TradeALGO rules YAML."""
    provider = get_provider(custom_key=custom_key, provider_name=provider_name)
    if not provider:
        raise ProviderError("No AI provider available. Please provide an OpenAI or Gemini API key.")

    system_prompt = (
        "You are an expert trading strategy vision assistant for TradeALGO. "
        "Carefully read all words, numbers, chart labels, Pine script, or handwritten notes in this image. "
        "Extract the trading indicators, entry conditions (long/short), and exit conditions (long/short). "
        "Format the output strictly as a valid YAML rules block inside ```yaml ... ``` tags, adhering to this format:\n\n"
        "```yaml\n"
        "indicators:\n"
        "  - {name: <name>, type: <sma|ema|wma|hma|rsi|mfi|atr|highest|lowest|vwap|pivot|pivot_s1|pivot_r1>, period: <int>}\n"
        "entry_long: \"<condition>\"\n"
        "exit_long: \"<condition>\"\n"
        "entry_short: \"<condition>\"\n"
        "exit_short: \"<condition>\"\n"
        "```\n\n"
        "Conditions must use ONLY: open, high, low, close, volume, defined indicator names, <name>_prev, numbers, "
        "operators (+, -, *, /), comparisons (>, <, >=, <=, ==, !=), and logical operators (and, or, not).\n"
        "After the YAML code block, write a concise 2-line plain English explanation of what rules were detected."
    )
    user_prompt = "Transcribe the trading strategy shown in this image into TradeALGO rules YAML."
    raw = provider.generate_vision(system_prompt, user_prompt, image_bytes, mime_type)

    yaml_text = ""
    explanation = ""
    if "```yaml" in raw:
        parts = raw.split("```yaml", 1)[1].split("```", 1)
        yaml_text = parts[0].strip()
        if len(parts) > 1:
            explanation = parts[1].strip()
    elif "```" in raw:
        parts = raw.split("```", 1)[1].split("```", 1)
        yaml_text = parts[0].strip()
        if len(parts) > 1:
            explanation = parts[1].strip()
    else:
        yaml_text = raw.strip()

    return {"yaml": yaml_text, "explanation": explanation, "raw": raw}

