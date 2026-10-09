from __future__ import annotations
import base64
import json, os, re, urllib.error, urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

class ProviderError(RuntimeError):
    pass

def _get_candidate_secret_files() -> List[str]:
    user_home = os.path.expanduser("~")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cwd = os.getcwd()

    roots = [
        cwd,
        base_dir,
        user_home,
        "/mount/src/tradealgo",
        "/mount/src/tradealgo-main",
        "/home/appuser",
        "/root",
    ]
    filenames = [
        "secret.yml",
        "secrets.yml",
        "secret.yaml",
        "secrets.yaml",
        "secrets.toml",
        "secret.toml",
        ".env",
        ".env.local",
    ]
    subdirs = ["", ".streamlit", "configs"]

    candidates: List[str] = []
    for r in roots:
        if not r:
            continue
        for sub in subdirs:
            for fn in filenames:
                p = os.path.normpath(os.path.join(r, sub, fn))
                if p not in candidates:
                    candidates.append(p)
    return candidates


def _read_file_safe(fpath: str) -> str:
    if not os.path.exists(fpath):
        return ""
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _match_gemini_val(k_name: str, val_str: str) -> bool:
    if not val_str:
        return False
    # Avoid other provider prefixes or internal IDE tokens
    if val_str.startswith("gsk_") or val_str.startswith("xai-") or val_str.startswith("sk-") or val_str.startswith("AQ."):
        return False
    if val_str.startswith("AIza"):
        return True
    k_lower = k_name.lower()
    if any(term in k_lower for term in ("gemini", "google", "flash")):
        return True
    if k_lower in ("api_key", "key", "secret", "token"):
        return True
    return False


def _walk_gemini(obj):
    if not obj:
        return None
    if isinstance(obj, (str, int, float)):
        s = str(obj).strip()
        if s.startswith("AIza"):
            return s
    if hasattr(obj, "items") or isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (str, int, float)):
                val = str(v).strip()
                if _match_gemini_val(str(k), val):
                    return val
        for k, v in obj.items():
            if isinstance(v, dict) or hasattr(v, "items"):
                res = _walk_gemini(v)
                if res:
                    return res
    return None


def _find_gemini_key() -> str:
    # 1. Candidate secret files (secret.yml, secrets.toml, .env, etc.)
    # We check files first with regex: this ensures that even if Streamlit Cloud secrets
    # has invalid TOML (e.g. user pasted YAML GEMINI_API_KEY: AIza...), we immediately extract it!
    for fpath in _get_candidate_secret_files():
        raw_content = _read_file_safe(fpath)
        if not raw_content:
            continue
        m = re.search(r"\b(AIza[0-9A-Za-z_-]{30,})\b", raw_content)
        if m:
            return m.group(1).strip()
        try:
            import yaml
            content = yaml.safe_load(raw_content)
            res = _walk_gemini(content)
            if res:
                return res
        except Exception:
            pass
        for line in raw_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                v_clean = v.strip().strip("'\"")
                if _match_gemini_val(k.strip(), v_clean):
                    return v_clean
            elif ":" in line:
                k, v = line.split(":", 1)
                v_clean = v.strip().strip("'\"")
                if _match_gemini_val(k.strip(), v_clean):
                    return v_clean

    # 2. Environment variables
    for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_FLASH_KEY", "GEMINI_KEY", "GOOGLE_KEY"):
        v = os.environ.get(env_name) or os.environ.get(env_name.lower())
        if v and str(v).strip():
            s = str(v).strip()
            if not s.startswith("AQ."):
                return s
    for k, v in os.environ.items():
        if v and str(v).strip().startswith("AIza"):
            return str(v).strip()
        if any(term in k.lower() for term in ("gemini", "google", "flash")) and v and str(v).strip():
            s = str(v).strip()
            if not s.startswith("AQ."):
                return s

    # 3. Streamlit secrets
    try:
        import streamlit as st
        for sec_name in (
            "GEMINI_API_KEY", "gemini_api_key",
            "GOOGLE_API_KEY", "google_api_key",
            "GOOGLE_FLASH_KEY", "google_flash_key",
            "GEMINI_KEY", "gemini_key",
            "GOOGLE_KEY", "google_key",
            "GEMINI", "gemini", "GOOGLE", "google",
            "API_KEY", "api_key", "KEY", "key",
        ):
            try:
                v = st.secrets.get(sec_name)
                if v and str(v).strip():
                    val = str(v).strip()
                    if _match_gemini_val(sec_name, val):
                        return val
            except Exception:
                pass
        for sec in ("gemini", "google", "ai", "general", "secrets", "default", "keys"):
            try:
                tbl = st.secrets.get(sec)
                if tbl and hasattr(tbl, "get"):
                    for k in ("api_key", "key", "gemini_api_key", "google_api_key", "token", "secret"):
                        v = tbl.get(k) or tbl.get(k.upper())
                        if v and str(v).strip() and _match_gemini_val(k, str(v).strip()):
                            return str(v).strip()
                if tbl and hasattr(tbl, "items"):
                    for k, v in tbl.items():
                        if v and str(v).strip() and _match_gemini_val(str(k), str(v).strip()):
                            return str(v).strip()
            except Exception:
                pass
        try:
            d = st.secrets.to_dict() if hasattr(st.secrets, "to_dict") else dict(st.secrets)
            res = _walk_gemini(d)
            if res:
                return res
        except Exception:
            pass
    except Exception:
        pass

    return ""


def _match_groq_val(k_name: str, val_str: str) -> bool:
    if not val_str:
        return False
    if val_str.startswith("AIza") or val_str.startswith("xai-") or val_str.startswith("sk-") or val_str.startswith("AQ."):
        return False
    if val_str.startswith("gsk_"):
        return True
    k_lower = k_name.lower()
    if "groq" in k_lower:
        return True
    if k_lower in ("api_key", "key", "secret", "token"):
        return True
    return False


def _walk_groq(obj):
    if not obj:
        return None
    if isinstance(obj, (str, int, float)):
        s = str(obj).strip()
        if s.startswith("gsk_"):
            return s
    if hasattr(obj, "items") or isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (str, int, float)):
                val = str(v).strip()
                if _match_groq_val(str(k), val):
                    return val
        for k, v in obj.items():
            if isinstance(v, dict) or hasattr(v, "items"):
                res = _walk_groq(v)
                if res:
                    return res
    return None


def _find_groq_key() -> str:
    # 1. Candidate secret files
    for fpath in _get_candidate_secret_files():
        raw_content = _read_file_safe(fpath)
        if not raw_content:
            continue
        m = re.search(r"\b(gsk_[0-9A-Za-z]{30,})\b", raw_content)
        if m:
            return m.group(1).strip()
        try:
            import yaml
            content = yaml.safe_load(raw_content)
            res = _walk_groq(content)
            if res:
                return res
        except Exception:
            pass
        for line in raw_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                v_clean = v.strip().strip("'\"")
                if _match_groq_val(k.strip(), v_clean):
                    return v_clean
            elif ":" in line:
                k, v = line.split(":", 1)
                v_clean = v.strip().strip("'\"")
                if _match_groq_val(k.strip(), v_clean):
                    return v_clean

    # 2. Environment variables
    for env_name in ("GROQ_API_KEY", "GROQ_KEY", "GROQ"):
        v = os.environ.get(env_name) or os.environ.get(env_name.lower())
        if v and str(v).strip():
            return str(v).strip()
    for k, v in os.environ.items():
        if v and str(v).strip().startswith("gsk_"):
            return str(v).strip()
        if "groq" in k.lower() and v and str(v).strip():
            return str(v).strip()

    # 3. Streamlit secrets
    try:
        import streamlit as st
        for k in ("GROQ_API_KEY", "groq_api_key", "GROQ_KEY", "groq_key", "GROQ", "groq"):
            try:
                v = st.secrets.get(k)
                if v and str(v).strip():
                    return str(v).strip()
            except Exception:
                pass
        for sec in ("groq", "ai", "general", "secrets"):
            try:
                tbl = st.secrets.get(sec)
                if tbl and hasattr(tbl, "get"):
                    for k in ("api_key", "key", "groq_api_key"):
                        v = tbl.get(k)
                        if v and str(v).strip():
                            return str(v).strip()
            except Exception:
                pass
        try:
            d = st.secrets.to_dict() if hasattr(st.secrets, "to_dict") else dict(st.secrets)
            res = _walk_groq(d)
            if res:
                return res
        except Exception:
            pass
    except Exception:
        pass

    return ""


def _match_grok_val(k_name: str, val_str: str) -> bool:
    if not val_str:
        return False
    if val_str.startswith("AIza") or val_str.startswith("gsk_") or val_str.startswith("sk-") or val_str.startswith("AQ."):
        return False
    if val_str.startswith("xai-"):
        return True
    k_lower = k_name.lower()
    if any(term in k_lower for term in ("grok", "xai")):
        return True
    return False


def _walk_grok(obj):
    if not obj:
        return None
    if isinstance(obj, (str, int, float)):
        s = str(obj).strip()
        if s.startswith("xai-"):
            return s
    if hasattr(obj, "items") or isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (str, int, float)):
                val = str(v).strip()
                if _match_grok_val(str(k), val):
                    return val
        for k, v in obj.items():
            if isinstance(v, dict) or hasattr(v, "items"):
                res = _walk_grok(v)
                if res:
                    return res
    return None


def _find_grok_key() -> str:
    # 1. Candidate secret files
    for fpath in _get_candidate_secret_files():
        raw_content = _read_file_safe(fpath)
        if not raw_content:
            continue
        m = re.search(r"\b(xai-[0-9A-Za-z]{30,})\b", raw_content)
        if m:
            return m.group(1).strip()
        try:
            import yaml
            content = yaml.safe_load(raw_content)
            res = _walk_grok(content)
            if res:
                return res
        except Exception:
            pass
        for line in raw_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                v_clean = v.strip().strip("'\"")
                if _match_grok_val(k.strip(), v_clean):
                    return v_clean
            elif ":" in line:
                k, v = line.split(":", 1)
                v_clean = v.strip().strip("'\"")
                if _match_grok_val(k.strip(), v_clean):
                    return v_clean

    # 2. Environment variables
    for env_name in ("GROK_API_KEY", "XAI_API_KEY", "GROK_KEY", "XAI_KEY", "GROK", "XAI", "CUSTOM_AI_KEY"):
        v = os.environ.get(env_name) or os.environ.get(env_name.lower())
        if v and str(v).strip():
            return str(v).strip()
    for k, v in os.environ.items():
        if v and str(v).strip().startswith("xai-"):
            return str(v).strip()
        if any(term in k.lower() for term in ("grok", "xai")) and v and str(v).strip():
            return str(v).strip()

    # 3. Streamlit secrets
    try:
        import streamlit as st
        for k in ("GROK_API_KEY", "XAI_API_KEY", "GROK_KEY", "XAI_KEY", "GROK", "XAI"):
            try:
                v = st.secrets.get(k) or st.secrets.get(k.lower())
                if v and str(v).strip():
                    return str(v).strip()
            except Exception:
                pass
        for sec in ("grok", "xai", "general", "secrets"):
            try:
                tbl = st.secrets.get(sec)
                if tbl and hasattr(tbl, "get"):
                    for k in ("api_key", "key", "grok_api_key", "xai_api_key"):
                        v = tbl.get(k) or tbl.get(k.upper())
                        if v and str(v).strip():
                            return str(v).strip()
            except Exception:
                pass
        try:
            d = st.secrets.to_dict() if hasattr(st.secrets, "to_dict") else dict(st.secrets)
            res = _walk_grok(d)
            if res:
                return res
        except Exception:
            pass
    except Exception:
        pass

    return ""


def _match_openai_val(k_name: str, val_str: str) -> bool:
    if not val_str:
        return False
    if val_str.startswith("AIza") or val_str.startswith("gsk_") or val_str.startswith("xai-") or val_str.startswith("AQ."):
        return False
    if val_str.startswith("sk-"):
        return True
    k_lower = k_name.lower()
    if "openai" in k_lower:
        return True
    return False


def _walk_openai(obj):
    if not obj:
        return None
    if isinstance(obj, (str, int, float)):
        s = str(obj).strip()
        if s.startswith("sk-"):
            return s
    if hasattr(obj, "items") or isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (str, int, float)):
                val = str(v).strip()
                if _match_openai_val(str(k), val):
                    return val
        for k, v in obj.items():
            if isinstance(v, dict) or hasattr(v, "items"):
                res = _walk_openai(v)
                if res:
                    return res
    return None


def _find_openai_key() -> str:
    # 1. Candidate secret files
    for fpath in _get_candidate_secret_files():
        raw_content = _read_file_safe(fpath)
        if not raw_content:
            continue
        m = re.search(r"\b(sk-[0-9A-Za-z_-]{30,})\b", raw_content)
        if m:
            return m.group(1).strip()
        try:
            import yaml
            content = yaml.safe_load(raw_content)
            res = _walk_openai(content)
            if res:
                return res
        except Exception:
            pass
        for line in raw_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                v_clean = v.strip().strip("'\"")
                if _match_openai_val(k.strip(), v_clean):
                    return v_clean
            elif ":" in line:
                k, v = line.split(":", 1)
                v_clean = v.strip().strip("'\"")
                if _match_openai_val(k.strip(), v_clean):
                    return v_clean

    # 2. Environment variables
    for env_name in ("OPENAI_API_KEY", "OPENAI_KEY", "OPENAI"):
        v = os.environ.get(env_name) or os.environ.get(env_name.lower())
        if v and str(v).strip():
            return str(v).strip()
    for k, v in os.environ.items():
        if v and str(v).strip().startswith("sk-"):
            return str(v).strip()

    # 3. Streamlit secrets
    try:
        import streamlit as st
        for k in ("OPENAI_API_KEY", "openai_api_key", "OPENAI_KEY", "openai_key", "OPENAI", "openai"):
            try:
                v = st.secrets.get(k)
                if v and str(v).strip():
                    return str(v).strip()
            except Exception:
                pass
        for sec in ("openai", "general", "secrets", "api"):
            try:
                tbl = st.secrets.get(sec)
                if tbl and hasattr(tbl, "get"):
                    for k in ("api_key", "key", "openai_api_key"):
                        v = tbl.get(k)
                        if v and str(v).strip():
                            return str(v).strip()
            except Exception:
                pass
        try:
            d = st.secrets.to_dict() if hasattr(st.secrets, "to_dict") else dict(st.secrets)
            res = _walk_openai(d)
            if res:
                return res
        except Exception:
            pass
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


class FallbackProvider(AIProvider):
    """Executes requests using primary provider and seamlessly fails over to backup on token/rate/quota limits."""
    name = "fallback"

    def __init__(self, providers: List[AIProvider]):
        self.providers = [p for p in providers if p is not None]
        if not self.providers:
            raise ValueError("FallbackProvider requires at least one provider.")
        self.active_provider_name = self.providers[0].name

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        last_exc = None
        for i, p in enumerate(self.providers):
            try:
                self.active_provider_name = p.name
                return p.generate(system_prompt, user_prompt)
            except Exception as exc:
                last_exc = exc
                if i < len(self.providers) - 1:
                    continue
                raise exc
        if last_exc:
            raise last_exc
        raise ProviderError("All providers exhausted.")

    def generate_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        last_exc = None
        for i, p in enumerate(self.providers):
            try:
                self.active_provider_name = p.name
                return p.generate_vision(system_prompt, user_prompt, image_bytes, mime_type)
            except Exception as exc:
                last_exc = exc
                if i < len(self.providers) - 1:
                    continue
                raise exc
        if last_exc:
            raise last_exc
        raise ProviderError("All vision providers exhausted.")


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
    DEFAULT_MODEL = "gemini-2.5-flash"
    CANDIDATE_MODELS = (
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.5-pro",
    )

    def __init__(self, key, model="", timeout=60):
        self.key = key
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        candidates = [self.model]
        for m in self.CANDIDATE_MODELS:
            if m not in candidates:
                candidates.append(m)
        last_err = None
        for m in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.key}"
            body = json.dumps({
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
            }).encode()
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json", "User-Agent": "TradeALGO/1.0"},
            )
            try:
                data = _send(req, self.timeout, "Gemini")
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except Exception as e:
                    raise ProviderError("Gemini returned invalid response structure.") from e
            except ProviderError as exc:
                last_err = exc
                err_text = str(exc).lower()
                if any(k in err_text for k in ("404", "400", "403", "not found", "model", "deprecated", "unknown", "permission", "access", "unsupported", "resource_exhausted", "quota")):
                    continue
                raise exc
        if last_err:
            raise last_err
        raise ProviderError("Gemini text generation failed on all candidate models.")

    def generate_vision(self, system_prompt: str, user_prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        norm_mime = "image/jpeg" if mime_type.lower() in ("image/jpg", "jpg") else mime_type
        candidates = [self.model]
        for m in self.CANDIDATE_MODELS:
            if m not in candidates:
                candidates.append(m)
        last_err = None
        for m in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.key}"
            body = json.dumps({
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{
                    "parts": [
                        {"text": user_prompt},
                        {"inline_data": {"mime_type": norm_mime, "data": b64}},
                    ]
                }],
            }).encode()
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json", "User-Agent": "TradeALGO/1.0"},
            )
            try:
                data = _send(req, self.timeout, "Gemini")
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except Exception as e:
                    raise ProviderError("Gemini returned invalid response structure.") from e
            except ProviderError as exc:
                last_err = exc
                err_text = str(exc).lower()
                if any(k in err_text for k in ("404", "400", "403", "not found", "model", "deprecated", "unknown", "permission", "access", "unsupported", "resource_exhausted", "quota")):
                    continue
                raise exc
        if last_err:
            raise last_err
        raise ProviderError("Gemini vision failed on all candidate models.")


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

def get_provider(custom_key: str = "", provider_name: str = "", model: str = "") -> Optional[AIProvider]:
    pname = (provider_name or "").lower().strip()
    if custom_key:
        if custom_key.startswith("AIza") or any(t in pname for t in ("gemini", "google", "flash")):
            return GeminiProvider(custom_key, model or _value("GEMINI_MODEL") or "gemini-2.5-flash")
        if custom_key.startswith("xai-") or any(t in pname for t in ("grok", "xai")):
            return GrokProvider(custom_key, model or _value("GROK_MODEL") or "grok-4.5")
        if custom_key.startswith("gsk_") or "groq" in pname:
            return GroqProvider(custom_key, model or _value("GROQ_MODEL") or "openai/gpt-oss-120b")
        if any(t in pname for t in ("anthropic", "claude")):
            return AnthropicProvider(custom_key, model or _value("ANTHROPIC_MODEL") or "claude-sonnet-4-6")
        if "openai" in pname or custom_key.startswith("sk-"):
            return OpenAIProvider(custom_key, model or _value("OPENAI_MODEL") or "gpt-4o-mini")
        return GeminiProvider(custom_key, model or _value("GEMINI_MODEL") or "gemini-2.5-flash")

    if any(t in pname for t in ("gemini", "google", "flash")):
        gemini_k = _find_gemini_key()
        if gemini_k:
            return GeminiProvider(gemini_k, model or _value("GEMINI_MODEL") or "gemini-2.5-flash")
        return None

    if "groq" in pname:
        groq_k = _find_groq_key()
        if groq_k:
            return GroqProvider(groq_k, model or _value("GROQ_MODEL") or "openai/gpt-oss-120b")
        return None

    if any(t in pname for t in ("grok", "xai")):
        grok_k = _find_grok_key()
        if grok_k:
            return GrokProvider(grok_k, model or _value("GROK_MODEL") or "grok-4.5")
        return None

    if any(t in pname for t in ("anthropic", "claude")):
        k = _value("ANTHROPIC_API_KEY")
        if k:
            return AnthropicProvider(k, model or _value("ANTHROPIC_MODEL") or "claude-sonnet-4-6")
        return None

    if "openai" in pname:
        k = _find_openai_key()
        if k:
            return OpenAIProvider(k, model or _value("OPENAI_MODEL") or "gpt-4o")
        return None

    # 1. Multi-provider resolution with automatic failover
    gemini_k = _find_gemini_key()
    groq_k = _find_groq_key()

    active_list = []
    if gemini_k:
        active_list.append(GeminiProvider(gemini_k, model or _value("GEMINI_MODEL") or "gemini-2.5-flash"))
    if groq_k:
        active_list.append(GroqProvider(groq_k, model or _value("GROQ_MODEL") or "openai/gpt-oss-120b"))

    if len(active_list) > 1:
        return FallbackProvider(active_list)
    if len(active_list) == 1:
        return active_list[0]

    # 2. Check Grok / xAI key
    grok_k = _find_grok_key()
    if grok_k:
        return GrokProvider(grok_k, model or _value("GROK_MODEL") or "grok-4.5")

    # 3. Fallbacks
    k = _value("ANTHROPIC_API_KEY")
    if k:
        return AnthropicProvider(k, model or _value("ANTHROPIC_MODEL") or "claude-sonnet-4-6")

    k = _find_openai_key()
    if k:
        return OpenAIProvider(k, model or _value("OPENAI_MODEL") or "gpt-4o")

    return None


def read_strategy_image(image_bytes: bytes, mime_type: str = "image/png", custom_key: str = "", provider_name: str = "", model: str = "") -> dict:
    """Reads a strategy photo/screenshot and extracts strict TradeALGO rules YAML."""
    provider = get_provider(custom_key=custom_key, provider_name=provider_name, model=model)
    if not provider:
        pname = (provider_name or "").lower()
        if "groq" in pname:
            target = "Groq"
        elif any(t in pname for t in ("grok", "xai")):
            target = "xAI Grok"
        elif "openai" in pname:
            target = "OpenAI"
        elif any(t in pname for t in ("anthropic", "claude")):
            target = "Anthropic"
        else:
            target = "Google Gemini"
        raise ProviderError(
            f"No {target} API key found in secrets. Please configure {target.upper().replace(' ', '_')}_API_KEY in secret.yml or Streamlit secrets."
        )

    system_prompt = (
        "You are an expert trading strategy vision assistant for TradeALGO. "
        "Carefully read all words, numbers, chart labels, Pine script, or handwritten notes in this image. "
        "Extract the trading indicators, entry conditions (long/short), and exit conditions (long/short). "
        "Format the output strictly as a valid YAML rules block inside ```yaml ... ``` tags, adhering to this format:\n\n"
        "```yaml\n"
        "indicators:\n"
        "  - {name: <name>, type: <sma|ema|wma|hma|rsi|mfi|cci|atr|highest|lowest|vwap|pivot|pivot_s1|pivot_r1>, period: <int>}\n"
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

    if yaml_text:
        try:
            import yaml
            from .strategy import normalize_rule_expression
            parsed = yaml.safe_load(yaml_text)
            if isinstance(parsed, dict):
                changed = False
                for rkey in ("entry_long", "exit_long", "entry_short", "exit_short"):
                    if rkey in parsed and isinstance(parsed[rkey], str):
                        norm = normalize_rule_expression(parsed[rkey])
                        if norm != parsed[rkey]:
                            parsed[rkey] = norm
                            changed = True
                if changed:
                    yaml_text = yaml.safe_dump(parsed, sort_keys=False).strip()
        except Exception:
            pass

    return {"yaml": yaml_text, "explanation": explanation, "raw": raw}


def get_ai_status() -> Dict[str, Any]:
    """Inspects credentials and returns active AI engine connection state."""
    gemini_k = _find_gemini_key()
    groq_k = _find_groq_key()
    return {
        "gemini_connected": bool(gemini_k),
        "groq_connected": bool(groq_k),
        "dual_active": bool(gemini_k and groq_k),
        "primary": "gemini" if gemini_k else ("groq" if groq_k else None),
        "backup": "groq" if (gemini_k and groq_k) else None,
    }


# Public aliases
find_gemini_key = _find_gemini_key
find_groq_key = _find_groq_key
find_grok_key = _find_grok_key
find_openai_key = _find_openai_key

__all__ = [
    "ProviderError",
    "AIProvider",
    "FallbackProvider",
    "GeminiProvider",
    "GroqProvider",
    "GrokProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "get_provider",
    "read_strategy_image",
    "get_ai_status",
    "find_gemini_key",
    "find_groq_key",
    "find_grok_key",
    "find_openai_key",
    "_find_gemini_key",
    "_find_groq_key",
    "_find_grok_key",
    "_find_openai_key",
]


