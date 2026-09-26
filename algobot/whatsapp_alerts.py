"""WhatsApp alerts via the free CallMeBot API (personal use only).

This module only ever sends a text message. It has no function that places,
modifies, or cancels a broker order -- same design principle as the existing
OpenAlgo Telegram bridge (see openalgo_bridge.py): the brother wants alerts,
not automatic orders, and a module that cannot send orders cannot send a
wrong one.

One-time setup, per phone number that should receive alerts:
  1. Save +34 694 23 41 84 in that phone's WhatsApp contacts.
  2. From that phone, send the contact the message:
       I allow callmebot to send me messages
  3. CallMeBot replies with a personal API key for that number.

Put every recipient's phone (with country code) and personal API key in a
private .env file -- never in code, a config file, or Git:
  WHATSAPP_RECIPIENTS=+91XXXXXXXXXX:key1,+91YYYYYYYYYY:key2

CallMeBot's free tier is unofficial, shared, and rate-limited -- fine for a
couple of people getting occasional signal alerts, not a guaranteed-delivery
channel. A failed send here must never raise past the caller in a way that
could be mistaken for a strategy error; see send_whatsapp()'s per-recipient
handling below.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"
RECIPIENTS_ENV = "WHATSAPP_RECIPIENTS"


class WhatsAppError(RuntimeError):
    """Something a person can fix: no recipients configured, an unreachable
    endpoint, or a request CallMeBot rejected."""


@dataclass(frozen=True)
class Recipient:
    phone: str
    apikey: str


def _scrub(text: str, recipients: list) -> str:
    for r in recipients:
        text = text.replace(r.apikey, "***")
    return text


def _secret(name: str):
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def load_recipients(env_var: str = RECIPIENTS_ENV) -> list:
    """Parse '+91XXXXXXXXXX:key1,+91YYYYYYYYYY:key2' from the environment
    (or Streamlit secrets, when running under Streamlit)."""
    raw = os.environ.get(env_var) or _secret(env_var) or ""
    recipients: list = []
    for chunk in str(raw).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        phone, _, apikey = chunk.partition(":")
        phone, apikey = phone.strip(), apikey.strip()
        if not phone or not apikey:
            raise WhatsAppError(
                f"{env_var} entry {chunk!r} must look like +91XXXXXXXXXX:apikey."
            )
        recipients.append(Recipient(phone=phone, apikey=apikey))
    return recipients


def _http_get(url: str, timeout: float) -> str:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise WhatsAppError(f"CallMeBot answered with HTTP {exc.code}.")
    except urllib.error.URLError as exc:
        raise WhatsAppError(f"Could not reach CallMeBot ({exc.reason}).")
    except TimeoutError:
        raise WhatsAppError("CallMeBot did not answer in time.")


def send_whatsapp(
    message: str,
    recipients: Optional[list] = None,
    timeout: float = 15.0,
    transport: Optional[Callable[[str, float], str]] = None,
) -> list:
    """Send `message` to every configured recipient.

    Returns one short result note per recipient (e.g. "+91...: sent" or
    "+91...: FAILED -- <reason>"). One recipient's failure never stops the
    others. Raises WhatsAppError only if there is nothing to send to at all
    -- that is a setup problem the caller should surface loudly, not a
    per-message delivery hiccup.
    """
    recipients = recipients if recipients is not None else load_recipients()
    if not recipients:
        raise WhatsAppError(
            f"No WhatsApp recipients configured. Set {RECIPIENTS_ENV} in a private .env file."
        )
    fetch = transport or _http_get
    notes = []
    for r in recipients:
        url = f"{CALLMEBOT_URL}?{urllib.parse.urlencode({'phone': r.phone, 'text': message, 'apikey': r.apikey})}"
        try:
            fetch(url, timeout)
            notes.append(f"{r.phone}: sent")
        except Exception as exc:
            notes.append(f"{r.phone}: FAILED -- {_scrub(str(exc), recipients)}")
    return notes
