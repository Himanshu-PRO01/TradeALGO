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
    # Keep the second tick inside the same Asia/Kolkata minute. The previous
    # fixture crossed a minute boundary (01:56:40 -> 01:57:10), so two bars
    # were correctly produced and the test was asserting the wrong fixture.
    hub._ingest(
        {
            "currentTs": 1780000005000,
            "feeds": {
                "NSE_INDEX|Nifty 50": {
                    "ltpc": {"ltp": 25010.0, "ltt": "1780000005000", "ltq": "5"}
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


def test_parse_candles_converts_upstox_rows_to_ist_minutes():
    from algobot.live_market import _parse_candles

    payload = {"data": {"candles": [["2026-09-29T15:29:00+05:30", 100, 105, 99, 102, 1500, 0], ["bad"]]}}
    rows = _parse_candles(payload)
    assert len(rows) == 1
    assert str(rows[0]["datetime"]) == "2026-09-29 15:29:00"
    assert rows[0]["close"] == 102.0 and rows[0]["volume"] == 1500.0


def test_history_merge_keeps_live_bars_and_orders_by_time():
    import pandas as pd

    hub = LiveMarketHub("t")
    key = "NSE_INDEX|Nifty 50"
    t1, t2 = pd.Timestamp("2026-09-29 15:28"), pd.Timestamp("2026-09-29 15:29")
    hub._update_bar(key, t2, 111.0, 0.0)  # live bar already present
    hub._merge_history(
        key,
        [
            {"datetime": t1, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10.0},
            {"datetime": t2, "open": 9, "high": 9, "low": 9, "close": 9, "volume": 1.0},
        ],
    )
    bars = hub.snapshot(key)
    assert len(bars) == 2
    assert bars["close"].iloc[-1] == 111.0  # live value wins
    assert bars.index.is_monotonic_increasing


def test_rest_ticks_after_hours_update_price_but_do_not_add_candles():
    import pandas as pd

    hub = LiveMarketHub("t")
    key = "NSE_INDEX|Nifty 50"
    payload = {"data": {"NSE_INDEX:Nifty 50": {"last_price": 22716.2, "instrument_token": key}}}
    hub._ingest_rest(payload, (key,), now=pd.Timestamp("2026-09-29 18:22:25"))
    assert hub.latest(key)["price"] == 22716.2
    assert hub.snapshot(key).empty
    hub._ingest_rest(payload, (key,), now=pd.Timestamp("2026-09-30 10:00:05"))
    assert len(hub.snapshot(key)) == 1
