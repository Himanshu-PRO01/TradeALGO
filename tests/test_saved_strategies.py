from algobot.saved_strategies import SavedStrategyLibrary


def test_saved_strategy_library_round_trip_and_count():
    lib = SavedStrategyLibrary(":memory:")
    cfg = {"name": "demo", "capital": 100000, "strategy": {"quantity": 1}}
    sid = lib.save("Demo strategy", cfg, market="NIFTY", timeframe="15m")
    assert lib.count() == 1
    record = lib.get(sid)
    assert record["name"] == "Demo strategy"
    assert record["config"]["strategy"]["quantity"] == 1
    assert record["market"] == "NIFTY"
    lib.mark_used(sid)
    assert lib.get(sid)["use_count"] == 1
    lib.delete(sid)
    assert lib.count() == 0
    lib.close_db()
