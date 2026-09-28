from algobot.upstox_market_data import MarketTick


def test_market_tick_normalizes_core_fields():
    tick = MarketTick(
        instrument_key="NSE_INDEX|Nifty 50",
        ltp=24500.5,
        ltt=123,
        received_ts=456,
        bid_price=24500.4,
        ask_price=24500.6,
        bid_qty=10,
        ask_qty=12,
    )
    assert tick.instrument_key == "NSE_INDEX|Nifty 50"
    assert tick.ltp == 24500.5
    assert tick.bid_price < tick.ask_price
