import pandas as pd

from algobot.config import validate_config
from algobot.paper_trading import evaluate, split_open_and_closed
from algobot.signal_alerts import AlertLog, step
from algobot.whatsapp_alerts import WhatsAppError


def _trending_df(n=60):
    """Flat long enough for both EMAs to warm up equal, then a clean
    monotonic rally: guarantees exactly one crossover entry with the
    position still open at the last bar."""
    idx = pd.date_range("2026-01-01 09:15", periods=n, freq="5min")
    flat = [100.0] * 20
    rally = [100 + i * 1.0 for i in range(1, n - len(flat) + 1)]
    close = flat + rally
    return pd.DataFrame({
        "open": close, "high": [c + 0.2 for c in close],
        "low": [c - 0.2 for c in close], "close": close,
        "volume": [1000] * n,
    }, index=idx)


BASE_CFG = validate_config({
    "name": "alert_test",
    "capital": 100000,
    "strategy": {
        "name": "rules", "quantity": 5, "allow_short": True,
        "params": {
            "indicators": [
                {"name": "ema_fast", "type": "ema", "period": 3},
                {"name": "ema_slow", "type": "ema", "period": 10},
            ],
            "entry_long": "ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev",
            "exit_long": "ema_fast < ema_slow",
            "entry_short": "ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev",
            "exit_short": "ema_fast > ema_slow",
        },
    },
})


def test_alert_flips_flat_to_open_on_a_real_entry_signal(monkeypatch):
    df = _trending_df()
    result = evaluate(BASE_CFG, df)
    open_snapshot, _closed = split_open_and_closed(result)
    assert open_snapshot is not None, "fixture should leave the strategy in an open position"

    sent = []
    monkeypatch.setattr("algobot.signal_alerts.send_whatsapp",
                        lambda text, **kw: sent.append(text) or ["+911111111111: sent"])

    log = AlertLog(":memory:")
    messages = step(open_snapshot, "test_run_key", "NIFTY 25000 CE", 5, log)

    assert any("Entry alert sent" in m for m in messages)
    assert len(sent) == 1 and "LONG signal fired" in sent[0]
    state = log.get_state("test_run_key")
    assert state["status"] == "open"
    assert state["side"] == "LONG"


def test_alert_does_not_resend_for_the_same_still_open_position(monkeypatch):
    df = _trending_df()
    result = evaluate(BASE_CFG, df)
    open_snapshot, _ = split_open_and_closed(result)

    sent = []
    monkeypatch.setattr("algobot.signal_alerts.send_whatsapp",
                        lambda text, **kw: sent.append(text) or ["+911111111111: sent"])

    log = AlertLog(":memory:")
    step(open_snapshot, "k", "NIFTY 25000 CE", 5, log)
    assert len(sent) == 1

    # A second refresh with the SAME open position (identical entry_time) must
    # not fire a duplicate alert.
    messages = step(open_snapshot, "k", "NIFTY 25000 CE", 5, log)
    assert messages == []
    assert len(sent) == 1


def test_alert_stays_flat_with_no_open_signal(monkeypatch):
    idx = pd.date_range("2026-01-01 09:15", periods=20, freq="5min")
    flat_close = [100.0] * 20
    df = pd.DataFrame({
        "open": flat_close, "high": [100.2] * 20, "low": [99.8] * 20,
        "close": flat_close, "volume": [1000] * 20,
    }, index=idx)
    result = evaluate(BASE_CFG, df)
    open_snapshot, _ = split_open_and_closed(result)
    assert open_snapshot is None  # no crossover on flat prices -> correctly flat

    sent = []
    monkeypatch.setattr("algobot.signal_alerts.send_whatsapp",
                        lambda text, **kw: sent.append(text) or ["+911111111111: sent"])

    log = AlertLog(":memory:")
    messages = step(open_snapshot, "k2", "NIFTY 25000 CE", 5, log)
    assert messages == []
    assert sent == []
    assert log.get_state("k2")["status"] == "flat"


def test_alert_failure_is_logged_but_does_not_raise(monkeypatch):
    df = _trending_df()
    result = evaluate(BASE_CFG, df)
    open_snapshot, _ = split_open_and_closed(result)

    def _boom(text, **kw):
        raise WhatsAppError("no recipients configured")

    monkeypatch.setattr("algobot.signal_alerts.send_whatsapp", _boom)

    log = AlertLog(":memory:")
    messages = step(open_snapshot, "k3", "NIFTY 25000 CE", 5, log)
    assert any("FAILED" in m for m in messages)
    # A failed alert must not be mistaken for "already alerted" -- state stays flat
    # so the next refresh retries rather than silently giving up forever.
    assert log.get_state("k3")["status"] == "flat"
