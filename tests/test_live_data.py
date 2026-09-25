import pytest

from algobot.live_data import INTERVALS, MARKETS, LiveDataError, fetch_ohlc


def test_markets_and_intervals_are_well_formed():
    assert "Nifty 50" in MARKETS and MARKETS["Nifty 50"] == "^NSEI"
    assert "Sensex" in MARKETS and MARKETS["Sensex"] == "^BSESN"
    for label, (interval, period) in INTERVALS.items():
        assert interval and period, label


def test_fetch_ohlc_raises_live_data_error_without_yfinance(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yfinance":
            raise ImportError("no yfinance in this test env")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(LiveDataError, match="yfinance is not installed"):
        fetch_ohlc("^NSEI", "5m", "5d")
