import pandas as pd

from algobot.config import validate_config
from algobot.paper_trading import evaluate, split_open_and_closed
from algobot.sandbox_rehearsal import RehearsalLog, step
from algobot.upstox_sandbox import UpstoxSandboxClient


def _trending_df(n=60):
    """Flat long enough for both EMAs to warm up equal, then a clean
    monotonic rally: guarantees exactly one crossover entry with the
    position still open at the last bar (exit_reason 'end_of_data')."""
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
    "name": "reh_test",
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


class FakeClient:
    """Stands in for UpstoxSandboxClient without hitting the network."""
    def __init__(self):
        self.calls = []

    def place_order(self, instrument_token, quantity, transaction_type, order_type="MARKET"):
        self.calls.append((instrument_token, quantity, transaction_type))
        return {"data": {"order_id": "SB-TEST-1"}}


def test_rehearsal_flips_flat_to_open_on_a_real_entry_signal():
    df = _trending_df()
    result = evaluate(BASE_CFG, df)
    open_snapshot, _closed = split_open_and_closed(result)
    assert open_snapshot is not None, "fixture should leave the strategy in an open position"

    log = RehearsalLog(":memory:")
    client = FakeClient()
    messages = step(open_snapshot, "test_run_key", client, "NSE_FO|TEST", 5, log)

    assert any("Entered" in m for m in messages)
    assert client.calls == [("NSE_FO|TEST", 5, "BUY")]
    state = log.get_state("test_run_key")
    assert state["status"] == "open"
    assert state["side"] == "LONG"


def test_rehearsal_does_not_reenter_the_same_still_open_position():
    df = _trending_df()
    result = evaluate(BASE_CFG, df)
    open_snapshot, _ = split_open_and_closed(result)
    log = RehearsalLog(":memory:")
    client = FakeClient()

    step(open_snapshot, "k", client, "NSE_FO|TEST", 5, log)
    assert len(client.calls) == 1

    # A second refresh with the SAME open position (identical entry_time) must
    # not fire a duplicate entry order.
    messages = step(open_snapshot, "k", client, "NSE_FO|TEST", 5, log)
    assert messages == []
    assert len(client.calls) == 1


def test_rehearsal_stays_flat_with_no_open_signal():
    idx = pd.date_range("2026-01-01 09:15", periods=20, freq="5min")
    flat_close = [100.0] * 20
    df = pd.DataFrame({
        "open": flat_close, "high": [100.2] * 20, "low": [99.8] * 20,
        "close": flat_close, "volume": [1000] * 20,
    }, index=idx)
    result = evaluate(BASE_CFG, df)
    open_snapshot, _ = split_open_and_closed(result)
    assert open_snapshot is None  # no crossover on flat prices -> correctly flat

    log = RehearsalLog(":memory:")
    client = FakeClient()
    messages = step(open_snapshot, "k2", client, "NSE_FO|TEST", 5, log)
    assert messages == []
    assert client.calls == []
    assert log.get_state("k2")["status"] == "flat"
