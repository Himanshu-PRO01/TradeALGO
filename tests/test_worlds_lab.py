import numpy as np
import pandas as pd
import pytest

from algobot.config import validate_config
from algobot.data import validate_bars
from algobot.lab import format_lab, null_test, run_lab
from algobot.lookahead import LeakyStrategy
from algobot.strategy import REGIMES, REGISTRY
from algobot.worlds import REGIMES, generate_mixed_world, generate_world, get_regime


def lag1(df):
    r = np.log(df["close"]).diff()
    same_day = df.index.normalize() == pd.Series(df.index.normalize(), index=df.index).shift(1)
    r = r[same_day].dropna().to_numpy()
    return float(np.corrcoef(r[:-1], r[1:])[0, 1])


def test_worlds_are_valid_reproducible_and_seeded():
    a, b, c = generate_world("noise", 5, 1), generate_world("noise", 5, 1), generate_world("noise", 5, 2)
    pd.testing.assert_frame_equal(a, b)
    assert not a["close"].equals(c["close"])
    assert len(a) == 5 * 75 and a.index[0].strftime("%H:%M") == "09:15"
    for name in REGIMES:
        validate_bars(generate_world(name, 6, 3, 24500.0))


def test_market_personalities_really_differ():
    assert lag1(generate_world("trend", 40, 1)) > 0.25
    assert lag1(generate_world("mean_reversion", 40, 1)) < -0.25
    assert abs(lag1(generate_world("noise", 40, 1))) < 0.1
    quiet = generate_world("chop", 20, 1)["close"].pct_change().abs().mean()
    wild = generate_world("volatile", 20, 1)["close"].pct_change().abs().mean()
    assert wild > 3 * quiet


def test_a_crash_world_falls_and_shocks_create_big_jumps():
    finals = [generate_world("crash", 20, s, 1000.0)["close"].iloc[-1] for s in range(1, 13)]
    assert np.mean(np.log(np.array(finals) / 1000.0)) < -0.05
    def biggest(name):
        return np.mean([generate_world(name, 20, s)["close"].pct_change().abs().max() for s in range(1, 9)])
    assert biggest("shocks") > 2 * biggest("noise")


def test_mixed_world_changes_character_and_stays_continuous():
    df, segments = generate_mixed_world(30, 3, 1000.0, segment_days=(3, 6))
    assert len(df) == 30 * 75 and len(segments) >= 4 and len({s[0] for s in segments}) >= 3
    assert df.index.is_monotonic_increasing and not df.index.duplicated().any()
    validate_bars(df)
    for (_, _, last), (_, first, _) in zip(segments, segments[1:]):
        assert first > last
    closes = df["close"]
    assert (closes.pct_change().abs().dropna() < 0.2).all()


def test_bad_world_requests_are_refused():
    with pytest.raises(ValueError, match="Unknown regime"):
        get_regime("sideways-ish")
    with pytest.raises(ValueError):
        generate_world("noise", 0, 1)


CFG = validate_config({
    "name": "lab_demo", "capital": 100000,
    "strategy": {"name": "sma_crossover", "params": {"fast": 5, "slow": 20}, "quantity": 10, "allow_short": True,
                 "stop_loss_pct": 0.6, "target_pct": 1.2},
    "risk": {"max_daily_loss": 3000, "max_trades_per_day": 6},
})


def test_lab_covers_every_market_type_and_is_reproducible():
    a = run_lab(CFG, worlds_per_regime=3, days=6, control_worlds=0)
    b = run_lab(CFG, worlds_per_regime=3, days=6, control_worlds=0)
    assert list(a.by_regime.index) == list(REGIMES) and (a.by_regime["worlds"] == 3).all()
    pd.testing.assert_frame_equal(a.by_regime, b.by_regime)
    assert a.control == {} and a.integrity == []
    text = format_lab(a)
    assert text.startswith("STRESS LAB") and "made-up markets" in text and "Risk rules held" in text


def test_lab_can_be_limited_to_chosen_markets():
    rep = run_lab(CFG, ["trend", "chop"], worlds_per_regime=2, days=5, control_worlds=0)
    assert list(rep.by_regime.index) == ["trend", "chop"] and len(rep.runs) == 4


def test_lab_notices_when_risk_rules_are_broken():
    tight = validate_config({
        "capital": 100000, "strategy": {"name": "sma_crossover", "params": {"fast": 3, "slow": 10}, "quantity": 200,
                                        "allow_short": True},
        "risk": {"max_daily_loss": 1}})
    rep = run_lab(tight, ["volatile"], worlds_per_regime=3, days=6, control_worlds=0)
    assert any("double the daily limit" in v for v in rep.integrity)
    assert "RISK RULES BROKEN" in format_lab(rep)


def test_null_test_passes_an_honest_strategy_and_catches_a_cheater():
    honest = null_test(CFG, worlds=20, days=8)
    assert not honest["suspicious"] and abs(honest["t"]) < 3
    REGISTRY["leaky_for_test"] = LeakyStrategy
    try:
        cheat_cfg = validate_config({"capital": 100000, "strategy": {"name": "leaky_for_test", "quantity": 10,
                                                                     "allow_short": True}})
        cheat = null_test(cheat_cfg, worlds=15, days=6)
        assert cheat["suspicious"] and cheat["t"] > 10 and "SUSPICIOUS" in cheat["text"]
    finally:
        del REGISTRY["leaky_for_test"]


def test_lab_flags_a_cheater_in_its_report():
    REGISTRY["leaky_for_test"] = LeakyStrategy
    try:
        cheat_cfg = validate_config({"capital": 100000, "strategy": {"name": "leaky_for_test", "quantity": 10,
                                                                     "allow_short": True}})
        rep = run_lab(cheat_cfg, ["noise"], worlds_per_regime=2, days=5, control_worlds=12)
        assert rep.control["suspicious"] and "SUSPICIOUS" in format_lab(rep)
    finally:
        del REGISTRY["leaky_for_test"]