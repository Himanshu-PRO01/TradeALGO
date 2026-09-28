from datetime import datetime

import pandas as pd

from algobot.live_market import LiveMarketHub, _as_dict


def test_as_dict_accepts_json_text():
    assert _as_dict('{"feeds": {}}') == {"feeds": {}}


def test_live_market_hub_aggregates_ticks_into_minute_bars():
    hub = LiveMarketHub("test-token")
    hub._ingest(
        {
            "currentTs": 1780000000000,
            "feeds": {
                "NSE_INDEX|Nifty 50": {
                    "ltpc": {"ltp": 25000.0, "ltt": "1780000000000", "ltq": "10"}
                }
            },
        }
    )
    hub._ingest(
        {
            "currentTs": 1780000030000,
            "feeds": {
                "NSE_INDEX|Nifty 50": {
                    "ltpc": {"ltp": 25010.0, "ltt": "1780000030000", "ltq": "5"}
                }
            },
        }
    )
    bars = hub.snapshot("NSE_INDEX|Nifty 50")
    assert len(bars) == 1
    row = bars.iloc[0]
    assert row["open"] == 25000.0
    assert row["high"] == 25010.0
    assert row["low"] == 25000.0
    assert row["close"] == 25010.0
    assert row["volume"] == 15.0


def test_hub_latest_does_not_expose_token():
    hub = LiveMarketHub("super-secret-token")
    hub._ingest(
        {
            "currentTs": 1780000000000,
            "feeds": {
                "NSE_INDEX|Nifty 50": {
                    "ltpc": {"ltp": 25000.0, "ltt": "1780000000000", "ltq": "1"}
                }
            },
        }
    )
    latest = hub.latest("NSE_INDEX|Nifty 50")
    assert latest["price"] == 25000.0
    assert "super-secret-token" not in repr(hub.status())
