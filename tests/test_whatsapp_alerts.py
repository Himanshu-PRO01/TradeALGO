import urllib.parse

import pytest

from algobot.whatsapp_alerts import (
    Recipient,
    WhatsAppError,
    load_recipients,
    send_whatsapp,
)


class FakeTransport:
    """Records every URL fetched; answers or raises per a canned schedule."""

    def __init__(self, fail_for=None):
        self.calls = []
        self.fail_for = fail_for or set()

    def __call__(self, url, timeout):
        self.calls.append(url)
        for phone in self.fail_for:
            if f"phone={urllib.parse.quote_plus(phone)}" in url:
                raise RuntimeError("simulated CallMeBot failure")
        return "ok"


# --------------------------------------------------------------- recipients
def test_load_recipients_parses_multiple(monkeypatch):
    monkeypatch.setenv("WHATSAPP_RECIPIENTS", "+911111111111:keyA,+912222222222:keyB")
    recipients = load_recipients()
    assert recipients == [
        Recipient(phone="+911111111111", apikey="keyA"),
        Recipient(phone="+912222222222", apikey="keyB"),
    ]


def test_load_recipients_empty_when_unset(monkeypatch):
    monkeypatch.delenv("WHATSAPP_RECIPIENTS", raising=False)
    assert load_recipients() == []


def test_load_recipients_rejects_malformed_entry(monkeypatch):
    monkeypatch.setenv("WHATSAPP_RECIPIENTS", "not-a-valid-entry")
    with pytest.raises(WhatsAppError):
        load_recipients()


# ----------------------------------------------------------------- sending
def test_send_whatsapp_raises_with_no_recipients():
    with pytest.raises(WhatsAppError):
        send_whatsapp("hello", recipients=[])


def test_send_whatsapp_sends_to_every_recipient():
    fake = FakeTransport()
    recipients = [Recipient(phone="+911111111111", apikey="keyA"),
                  Recipient(phone="+912222222222", apikey="keyB")]
    notes = send_whatsapp("Signal fired", recipients=recipients, transport=fake)
    assert notes == ["+911111111111: sent", "+912222222222: sent"]
    assert len(fake.calls) == 2
    assert "text=Signal" in fake.calls[0]


def test_send_whatsapp_one_failure_does_not_stop_the_others():
    fake = FakeTransport(fail_for={"+911111111111"})
    recipients = [Recipient(phone="+911111111111", apikey="keyA"),
                  Recipient(phone="+912222222222", apikey="keyB")]
    notes = send_whatsapp("Signal fired", recipients=recipients, transport=fake)
    assert notes[0].startswith("+911111111111: FAILED")
    assert notes[1] == "+912222222222: sent"


def test_send_whatsapp_never_leaks_apikey_in_failure_note():
    fake = FakeTransport(fail_for={"+911111111111"})
    recipients = [Recipient(phone="+911111111111", apikey="super-secret-key")]
    notes = send_whatsapp("Signal fired", recipients=recipients, transport=fake)
    assert "super-secret-key" not in notes[0]
