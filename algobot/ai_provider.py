from __future__ import annotations
import base64
import json, os, urllib.error, urllib.request
from typing import Optional

class ProviderError(RuntimeError):
    pass

def _find_grok_key() -> str:
    # 1. Environment variables
    for env_name in ("GROK_API_KEY", "XAI_API_KEY", "GROK_KEY", "XAI_KEY", "GROK", "XAI", "GROK_AI_KEY"):
        v = os.environ.get(env_name) or os.environ.get(env_name.lower())
        if v and str(v).strip():
            return str(v).strip()
    for k, v in os.environ.items():
        if v and str(v).strip().startswith("xai-"):
            return str(v).strip()
        if any(term in k.lower() for term in ("grok", "xai")) and v and str(v).strip():
            return str(v).strip()

    # 2. Streamlit secrets
    try:
        import streamlit as st
        for k in ("GROK_API_KEY", "XAI_API_KEY", "GROK_KEY", "XAI_KEY", "GROK", "XAI", "GROK_AI_KEY", "API_KEY", "KEY"):
            try:
                v = st.secrets.get(k) or st.secrets.get(k.lower())
                if v and str(v).strip():
                    val = str(v).strip()
                    if val.startswith("xai-") or "grok" in k.lower() or "xai" in k.lower():
                        return val
            except Exception:
                pass

        def _scan(obj):
            if not obj:
                return None
            if hasattr(obj, "items"):
                for k, v in obj.items():
                    k_str = str(k).strip()
                    k_lower = k_str.lower()
                    if isinstance(v, (str, int, float)):
                        val = str(v).strip()
                        if val.startswith("xai-"):
                            return val
                        if any(term in k_lower for term in ("grok", "xai")) and val:
                            return val
                for k, v in obj.items():
                    if hasattr(v, "items") or isinstance(v, dict):
                        res = _scan(v)
                        if res:
                            return res
            return None
        res = _scan(st.secrets)
        if res:
            return res
    except Exception:
        pass

    return ""


def _find_groq_key() -> str:
    for env_name in ("GROQ_API_KEY", "GROQ_KEY", "GROQ"):
        v = os.environ.get(env_name) or os.environ.get(env_name.lower())
        if v and str(v).strip():
            return str(v).strip()
    for k, v in os.environ.items():
        if v and str(v).strip().startswith("gsk_"):
            return str(v).strip()
        if "groq" in k.lower() and v and str(v).strip():
            return str(v).strip()
    try:
        import streamlit as st
        for k in ("GROQ_API_KEY", "GROQ_KEY", "GROQ"):
            try:
                v = st.secrets.get(k) or st.secrets.get(k.lower())
                if v and str(v).strip():
                    return str(v).strip()
            except Exception:
                pass
        def _scan(obj):
            if not obj:
                return None
            if hasattr(obj, "items"):
                for k, v in obj.items():
                    k_lower = str(k).strip().lower()
                    if isinstance(v, (str, int, float)):
                        val = str(v).strip()
                        if val.startswith("gsk_") or "groq" in k_lower:
                            return val
                for k, v in obj.items():
                    if hasattr(v, "items") or isinstance(v, dict):
                        res = _scan(v)
                        if res:
                            return res
            return None
        res = _scan(st.secrets)
        if res:
            return res
    except Exception:
        pass
    return ""


def _secret(name):
    try:
        import streamlit as st
        if not hasattr(st, "secrets") or not st.secrets:
            return None
        v = st.secrets.get(name) or st.secrets.get(name.lower()) or st.secrets.get(name.upper())
        if v:
            return str(v).strip()
        for sec in ("grok", "xai", "groq", "ai", "general"):
            table = st.secrets.get(sec)
            if hasattr(table, "get"):
                tv = table.get(name) or table.get(name.lower()) or table.get("api_key") or table.get("key")
                if tv:
                    return str(tv).strip()
        return None
    except Exception:
        return None

def _value(name):
    v = os.environ.get(name) or os.environ.get(name.lower()) or os.environ.get(name.upper()) or _secret(name)
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
        norm_mime = "image/jpeg" if mime_type.lower() in ("image/jpg", "jpg") else mime_type
        body = json.dumps({
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{norm_mime};base64,{b64}"}},
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


class GrokProvider(AIProvider):
    """xAI Grok Chat Completions and Multimodal Vision provider."""
    name = "grok"
    BASE_URL = "https://api.x.ai/v1/chat/completions"
    DEFAULT_MODEL = "grok-4.5"
    CANDIDATE_MODELS = (
        "grok-4.5",
        "grok-4.7",
        "grok-4.3",
        "grok-4.20-non-reasoning",
        "grok-2-vision-1212",
        "grok-2-vision",
        "grok-vision-beta",
    )

    def __init__(self, key, model="grok-4.5", timeout=60):
        self.key = key
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        candidates = [self.model]
        for m in self.CANDIDATE_MODELS:
            if m not in candidates:
                candidates.append(m)
        last_err = None
        for model_name in candidates:
            try:
                return _chat_completion(
                    self.BASE_URL,
                    self.key,
                    model_name,
                    system_prompt,
                    user_prompt,
                    self.timeout,
                    "Grok",
                )
            except ProviderError as exc:
                last_err = exc
                err_text = str(exc).lower()
                if any(k in err_text for k in ("model", "404", "400", "not found", "deprecated", "unknown")):
                    continue
                raise exc
        if last_err:
            raise last_err
        raise ProviderError("Grok text generation failed with all candidate models.")

    def generate_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        norm_mime = "image/jpeg" if mime_type.lower() in ("image/jpg", "jpg") else mime_type

        candidates = [self.model]
        for m in self.CANDIDATE_MODELS:
            if m not in candidates:
                candidates.append(m)

        last_err = None
        for model_name in candidates:
            body = json.dumps({
                "model": model_name,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{norm_mime};base64,{b64}"}},
                        ],
                    },
                ],
            }).encode()
            req = urllib.request.Request(
                self.BASE_URL,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.key}",
                    "User-Agent": "TradeALGO/1.0",
                },
            )
            try:
                data = _send(req, self.timeout, "Grok")
                try:
                    out = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    out = ""
                if not out:
                    raise ProviderError("Grok returned no text.")
                return out.strip()
            except ProviderError as exc:
                last_err = exc
                err_text = str(exc).lower()
                if any(k in err_text for k in ("model", "404", "400", "not found", "deprecated", "unknown")):
                    continue
                raise exc
        if last_err:
            raise last_err
        raise ProviderError("Grok vision failed with all candidate models.")


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

    def generate_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        vision_model = self.model if "vision" in self.model else "llama-3.2-11b-vision-preview"
        body = json.dumps({
            "model": vision_model,
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
            self.BASE_URL,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.key}",
                "User-Agent": "TradeALGO/1.0",
            },
        )
        data = _send(req, self.timeout, "Groq")
        try:
            out = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            out = ""
        if not out:
            raise ProviderError("Groq returned no text.")
        return out.strip()


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
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        detail = ""
        if body:
            try:
                err_json = json.loads(body)
                err_msg = err_json.get("error") or err_json.get("message")
                if isinstance(err_msg, dict):
                    err_msg = err_msg.get("message") or err_msg.get("code") or str(err_msg)
                if err_msg:
                    detail = f": {err_msg}"
                else:
                    detail = f": {body[:250]}"
            except Exception:
                detail = f": {body[:250]}"
        raise ProviderError(f"{vendor} API error HTTP {e.code}{detail}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ProviderError(f"Could not reach {vendor} API: {e}") from e
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProviderError(f"{vendor} returned invalid JSON.") from e

def get_provider(custom_key: str = "", provider_name: str = "") -> Optional[AIProvider]:
    pname = (provider_name or "").lower().strip()
    if custom_key:
        if custom_key.startswith("xai-") or "grok" in pname or "xai" in pname:
            return GrokProvider(custom_key, _value("GROK_MODEL") or "grok-4.5")
        if custom_key.startswith("gsk_") or "groq" in pname:
            return GroqProvider(custom_key, _value("GROQ_MODEL") or "llama-3.2-11b-vision-preview")
        if "gemini" in pname:
            return GeminiProvider(custom_key, _value("GEMINI_MODEL") or "gemini-2.5-flash")
        if "anthropic" in pname or "claude" in pname:
            return AnthropicProvider(custom_key, _value("ANTHROPIC_MODEL") or "claude-sonnet-4-6")
        return OpenAIProvider(custom_key, _value("OPENAI_MODEL") or "gpt-4o-mini")

    # 1. Prefer Grok / xAI key from secrets or environment
    grok_k = _find_grok_key()
    if grok_k:
        return GrokProvider(grok_k, _value("GROK_MODEL") or "grok-4.5")

    # 2. Check Groq key (if key starts with xai-, resolve as GrokProvider)
    groq_k = _find_groq_key()
    if groq_k:
        if groq_k.startswith("xai-"):
            return GrokProvider(groq_k, _value("GROK_MODEL") or "grok-4.5")
        return GroqProvider(groq_k, _value("GROQ_MODEL") or "openai/gpt-oss-120b")

    # 3. Fallbacks
    k = _value("GEMINI_API_KEY")
    if k:
        return GeminiProvider(k, _value("GEMINI_MODEL") or "gemini-2.5-flash")

    k = _value("ANTHROPIC_API_KEY")
    if k:
        return AnthropicProvider(k, _value("ANTHROPIC_MODEL") or "claude-sonnet-4-6")

    k = _value("OPENAI_API_KEY")
    if k:
        return OpenAIProvider(k, _value("OPENAI_MODEL") or "gpt-4o-mini")

    return None


def read_strategy_image(image_bytes: bytes, mime_type: str = "image/png", custom_key: str = "", provider_name: str = "") -> dict:
    """Reads a strategy photo/screenshot and extracts strict TradeALGO rules YAML."""
    provider = get_provider(custom_key=custom_key, provider_name=provider_name)
    if not provider:
        raise ProviderError(
            "No Grok AI API key found in secrets or environment. Please add GROK_API_KEY (or XAI_API_KEY / GROQ_API_KEY) in Streamlit secrets."
        )

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

