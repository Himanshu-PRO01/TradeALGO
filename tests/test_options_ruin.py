import math

import pytest

from algobot.options import bs_greeks, bs_price, breakeven_analysis, format_breakeven
from algobot.ruin import breakeven_win_rate, expected_value_r, format_ruin, simulate_ruin


# ------------------------------------------------------------ Black-Scholes
def test_bs_matches_the_textbook_reference_values():
    # S=100, K=100, 1 year, r=5%, vol 20%, no dividends: call 10.4506, put 5.5735
    assert bs_price(100, 100, 365, 0.20, "CE", r=0.05) == pytest.approx(10.4506, abs=1e-3)
    assert bs_price(100, 100, 365, 0.20, "PE", r=0.05) == pytest.approx(5.5735, abs=1e-3)


def test_put_call_parity_holds():
    S, K, days, iv, r, q = 24500, 24300, 20, 0.15, 0.065, 0.012
    T = days / 365
    lhs = bs_price(S, K, days, iv, "CE", r, q) - bs_price(S, K, days, iv, "PE", r, q)
    assert lhs == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-6)


def test_greeks_reference_values_and_signs():
    g = bs_greeks(100, 100, 365, 0.20, "CE", r=0.05)
    assert g["delta"] == pytest.approx(0.6368, abs=1e-3)
    assert bs_greeks(100, 100, 365, 0.20, "PE", r=0.05)["delta"] == pytest.approx(0.6368 - 1, abs=1e-3)
    assert g["theta"] < 0 and g["gamma"] > 0 and g["vega"] > 0
    assert g["theta"] == pytest.approx(-6.414 / 365, abs=2e-3)          # annual theta -6.414 spread over days


def test_at_expiry_only_intrinsic_value_is_left():
    assert bs_price(105, 100, 0, 0.2, "CE") == 5 and bs_price(105, 100, 0, 0.2, "PE") == 0
    assert bs_price(95, 100, 0, 0.2, "PE") == 5


def test_time_decay_speeds_up_near_expiry():
    far = bs_greeks(24500, 24500, 30, 0.14, "CE")["theta"]
    near = bs_greeks(24500, 24500, 2, 0.14, "CE")["theta"]
    assert near < far < 0                                               # more negative = faster decay


# ------------------------------------------------------- breakeven analysis
KW = dict(spot=24500, strike=24500, days_to_expiry=3, iv_pct=14, kind="CE", lot_size=65)


def test_holding_longer_raises_the_hurdle():
    one = breakeven_analysis(holding_days=1, **KW)
    three = breakeven_analysis(holding_days=3, **KW)
    assert three["breakeven_points"] > one["breakeven_points"] > 0
    assert one["time_decay_over_hold"] > 0 and one["decay_pct_of_premium"] > 0


def test_spread_and_charges_raise_the_hurdle():
    clean = breakeven_analysis(holding_days=1, **KW)
    costly = breakeven_analysis(holding_days=1, spread_per_unit=1.0, charges_round_trip=130, **KW)
    assert costly["breakeven_points"] > clean["breakeven_points"]
    assert costly["friction_per_unit"] == pytest.approx(1.0 + 130 / 65)


def test_actual_entry_premium_is_used_instead_of_theoretical_price():
    model = breakeven_analysis(holding_days=1, **KW)
    paid = breakeven_analysis(holding_days=1, entry_premium=model["premium"] + 10, **KW)
    assert paid["premium"] == pytest.approx(model["premium"] + 10)
    assert paid["premium_source"] == "actual market entry premium"
    assert paid["breakeven_points"] > model["breakeven_points"]
    assert "actual market entry premium" in format_breakeven(paid, "CE", 65)


def test_iv_crush_raises_the_hurdle_and_iv_rise_lowers_it():
    base = breakeven_analysis(holding_days=1, **KW)["breakeven_points"]
    crush = breakeven_analysis(holding_days=1, iv_change_pct=-3, **KW)["breakeven_points"]
    rise = breakeven_analysis(holding_days=1, iv_change_pct=+3, **KW)["breakeven_points"]
    assert crush > base > rise


def test_breakeven_move_really_breaks_even():
    res = breakeven_analysis(holding_days=1, spread_per_unit=0.5, **KW)
    moved = bs_price(24500 + res["breakeven_points"], 24500, 2, 0.14, "CE")
    assert moved == pytest.approx(res["premium"] + 0.5, abs=1e-3)


def test_put_needs_a_downward_move_and_the_text_says_so():
    res = breakeven_analysis(holding_days=1, **{**KW, "kind": "PE"})
    moved = bs_price(24500 - res["breakeven_points"], 24500, 2, 0.14, "PE")
    assert moved == pytest.approx(res["premium"], abs=1e-3)
    assert "down by" in format_breakeven(res, "PE", 65)


def test_holding_to_expiry_needs_the_premium_back_as_intrinsic_value():
    res = breakeven_analysis(holding_days=3, **KW)                      # held until expiry
    assert res["days_left_after"] == 0
    assert res["breakeven_points"] == pytest.approx(res["premium"], abs=1e-3)


def test_typical_move_context_is_reported():
    res = breakeven_analysis(holding_days=1, **KW)
    assert res["one_sigma_move"] == pytest.approx(24500 * 0.14 * math.sqrt(1 / 365), rel=1e-9)
    assert res["sigma_multiple"] == pytest.approx(res["breakeven_points"] / res["one_sigma_move"])


@pytest.mark.parametrize("bad", [
    dict(spot=0), dict(days_to_expiry=0), dict(iv_pct=0), dict(holding_days=-1), dict(kind="XX"), dict(lot_size=0),
    dict(spread_per_unit=-1),
])
def test_bad_breakeven_inputs_are_rejected(bad):
    with pytest.raises(ValueError):
        breakeven_analysis(**{**KW, "holding_days": 1, **bad})


# ------------------------------------------------------------ risk of ruin
def test_expected_value_and_breakeven_win_rate():
    assert expected_value_r(0.5, 2.0) == pytest.approx(0.5)             # 0.5*2 - 0.5
    assert expected_value_r(0.4, 1.0) == pytest.approx(-0.2)
    assert breakeven_win_rate(1.0) == pytest.approx(0.5) and breakeven_win_rate(2.0) == pytest.approx(1 / 3)
    assert breakeven_win_rate(1.0, cost_r=0.1) == pytest.approx(0.55)   # costs need a higher win rate


def test_bigger_bets_mean_more_ruin_with_the_same_edge():
    kw = dict(win_rate=0.45, reward_r=1.6, n_trades=100, ruin_loss_pct=50, n_paths=3000, seed=3)
    small = simulate_ruin(risk_pct=1, **kw)
    big = simulate_ruin(risk_pct=10, **kw)
    assert small["expected_value_r"] == pytest.approx(big["expected_value_r"])       # same edge...
    assert small["expected_value_r"] > 0                                            # ...and it is positive
    assert small["p_ruin"] < 0.01 and big["p_ruin"] > small["p_ruin"] + 0.05


def test_no_edge_and_costs_make_things_worse():
    fair = simulate_ruin(0.5, 1.0, 5, n_trades=100, n_paths=3000, seed=2)
    costly = simulate_ruin(0.5, 1.0, 5, n_trades=100, n_paths=3000, seed=2, cost_r=0.15)
    assert costly["final_median_pct"] < fair["final_median_pct"]
    assert costly["expected_value_r"] == pytest.approx(-0.15)


def test_ruin_simulation_is_reproducible_and_bounded():
    a = simulate_ruin(0.4, 1.5, 10, seed=5, n_paths=500)
    b = simulate_ruin(0.4, 1.5, 10, seed=5, n_paths=500)
    assert a == b
    # Touching the ruin level at ANY point can happen even on paths that later recover, so p_ruin is not
    # bounded by p_loss. Both are probabilities, though.
    assert 0 <= a["p_ruin"] <= 1 and 0 <= a["p_loss"] <= 1
    assert a["worst_streak_median"] >= 1


def test_the_brothers_setup_is_flagged_as_dangerous():
    # Rs 1,000 risk on Rs 10,000 = 10% per trade, 45% win rate, 1.5R average win, ~0.1R charges.
    res = simulate_ruin(0.45, 1.5, 10, n_trades=100, ruin_loss_pct=50, cost_r=0.1, n_paths=4000, seed=1)
    assert res["p_ruin"] > 0.3
    text = format_ruin(res, 0.45, 1.5, 10, 100, 50)
    assert "Chance of losing 50%" in text and "longest losing streak" in text


@pytest.mark.parametrize("bad", [
    dict(win_rate=0), dict(win_rate=1), dict(reward_r=0), dict(risk_pct=0), dict(risk_pct=100),
    dict(n_trades=0), dict(ruin_loss_pct=0), dict(cost_r=-0.1),
])
def test_bad_ruin_inputs_are_rejected(bad):
    with pytest.raises(ValueError):
        simulate_ruin(**{**dict(win_rate=0.5, reward_r=1.5, risk_pct=5), **bad})


def test_an_account_cannot_lose_more_than_everything():
    res = simulate_ruin(0.3, 1.0, 20, n_trades=100, ruin_loss_pct=50, n_paths=2000, seed=1)   # heavy losses
    assert res["final_p5_pct"] >= -100.0 and res["final_median_pct"] >= -100.0
    assert res["p_ruin"] > 0.95


def test_an_actual_ask_already_contains_the_entry_half_of_the_spread():
    spread, charges = 1.0, 130.0
    model = breakeven_analysis(holding_days=1, spread_per_unit=spread, charges_round_trip=charges, **KW)
    ask = model["premium"] + spread / 2                                   # what the model says you would pay
    paid = breakeven_analysis(holding_days=1, entry_premium=ask, spread_per_unit=spread,
                              charges_round_trip=charges, **KW)
    # Only the exit half of the spread is still to come, plus charges.
    assert paid["friction_per_unit"] == pytest.approx(spread / 2 + charges / 65)
    assert model["friction_per_unit"] == pytest.approx(spread + charges / 65)
    # The two routes describe the same trade, so they must give the same answer.
    assert paid["breakeven_points"] == pytest.approx(model["breakeven_points"], abs=1e-6)
    # And the answer is what it should be: sell at the bid after the move and just get the ask plus charges back.
    fair_after = bs_price(24500 + paid["breakeven_points"], 24500, 2, 0.14, "CE")
    assert fair_after - spread / 2 == pytest.approx(ask + charges / 65, abs=1e-3)


def test_a_dearer_ask_than_the_model_raises_the_hurdle_by_about_the_extra_cost():
    base = breakeven_analysis(holding_days=1, spread_per_unit=0.5, **KW)
    ask = base["premium"] + 0.25 + 15.0                                   # 15 points above the model's price
    dear = breakeven_analysis(holding_days=1, entry_premium=ask, spread_per_unit=0.5, **KW)
    extra_move = dear["breakeven_points"] - base["breakeven_points"]
    assert 15.0 / 0.75 < extra_move < 15.0 / 0.45                         # 15 premium points / an effective delta of 0.45 to 0.75
    assert dear["premium_source"] == "actual market entry premium" and base["premium_source"] != dear["premium_source"]
