import pytest

from algobot.sizing import NIFTY_LOT_SIZE, option_position_size, format_size


def test_default_nifty_lot_size_is_65():
    assert NIFTY_LOT_SIZE == 65


def test_lots_limited_by_the_loss_limit():
    # Loss per lot = (100 - 85) * 65 = 975. A Rs 2,000 limit allows 2 lots; capital is ample.
    r = option_position_size(max_loss=2000, entry_premium=100, stop_premium=85, lot_size=65, capital=100000)
    assert r.lots == 2 and r.quantity == 130
    assert r.loss_if_stopped == pytest.approx(1950)
    assert r.premium_outlay == pytest.approx(13000)


def test_lots_limited_by_capital_and_it_says_so():
    r = option_position_size(max_loss=50000, entry_premium=100, stop_premium=90, lot_size=65, capital=10000)
    assert r.lots == 1                           # cost per lot 6,500; capital 10,000
    assert any("Capital" in w for w in r.warnings)


def test_zero_lots_when_stop_is_too_wide_and_the_message_gives_the_fix():
    # 1 lot loses (100 - 80) * 65 = 1,300 > 1,000 limit. Longest allowed stop distance = 1000 / 65 = 15.38 points.
    r = option_position_size(max_loss=1000, entry_premium=100, stop_premium=80, lot_size=65, capital=10000)
    assert r.lots == 0 and r.quantity == 0
    assert "15.38" in " ".join(r.warnings)


def test_zero_lots_when_one_lot_costs_more_than_capital():
    r = option_position_size(max_loss=1000, entry_premium=200, stop_premium=190, lot_size=65, capital=10000)
    assert r.lots == 0                                    # 13,000 to buy one lot
    assert any("more than your capital" in w for w in r.warnings)


def test_charges_reduce_the_loss_budget():
    # Without charges: 975 fits in 1,000 -> 1 lot. With Rs 50 charges the budget is 950 -> 0 lots.
    assert option_position_size(1000, 100, 85, 65, capital=20000).lots == 1
    assert option_position_size(1000, 100, 85, 65, capital=20000, est_charges=50).lots == 0


def test_high_risk_percentage_is_flagged_with_simple_arithmetic():
    r = option_position_size(max_loss=1000, entry_premium=50, stop_premium=40, lot_size=65, capital=10000)
    assert r.risk_pct_of_capital == pytest.approx(10.0)
    assert any("10% of capital" in w and "30%" in w for w in r.warnings)


def test_heavy_use_of_capital_is_flagged():
    # One lot costs 130 * 65 = 8,450, which is 84% of the Rs 10,000 account.
    r = option_position_size(max_loss=1000, entry_premium=130, stop_premium=122, lot_size=65, capital=10000)
    assert r.lots == 1
    assert any("ties up 84%" in w for w in r.warnings)


@pytest.mark.parametrize("kwargs", [
    dict(max_loss=0, entry_premium=100, stop_premium=90),
    dict(max_loss=1000, entry_premium=0, stop_premium=0),
    dict(max_loss=1000, entry_premium=100, stop_premium=100),
    dict(max_loss=1000, entry_premium=100, stop_premium=120),
    dict(max_loss=1000, entry_premium=100, stop_premium=90, lot_size=0),
    dict(max_loss=1000, entry_premium=100, stop_premium=90, capital=-5),
])
def test_bad_inputs_are_rejected(kwargs):
    with pytest.raises(ValueError):
        option_position_size(**kwargs)


def test_format_is_readable():
    r = option_position_size(2000, 100, 85, 65, capital=100000)
    text = format_size(r, 65)
    assert "Lots allowed:        2" in text and "Loss if stop is hit" in text
