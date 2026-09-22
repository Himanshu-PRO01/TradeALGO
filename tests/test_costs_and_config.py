import pytest
import yaml

from algobot.config import ConfigError, validate_config
from algobot.costs import CostModel


def test_buy_charges_match_hand_calculation():
    cm = CostModel()  # defaults
    # value 100,000: brokerage capped at 20, STT 0, exchange 3.0, SEBI 0.1,
    # stamp 3.0, GST 18% of (20 + 3.0 + 0.1) = 4.158
    assert cm.order_charges("BUY", 1000.0, 100) == pytest.approx(30.258)


def test_sell_charges_include_stt_and_no_stamp_duty():
    cm = CostModel()
    # brokerage 20, STT 25.0, exchange 3.0, SEBI 0.1, GST 4.158
    assert cm.order_charges("SELL", 1000.0, 100) == pytest.approx(52.258)


def test_flat_brokerage_overrides_percentage():
    cm = CostModel(brokerage_flat=10.0, stt_sell_pct=0, exchange_txn_pct=0,
                   sebi_fee_pct=0, stamp_buy_pct=0, gst_pct=0)
    assert cm.order_charges("BUY", 1000.0, 100) == pytest.approx(10.0)


def test_slippage_hurts_both_sides():
    cm = CostModel(slippage_bps=10)
    assert cm.slippage_price(100.0, "BUY") == pytest.approx(100.1)
    assert cm.slippage_price(100.0, "SELL") == pytest.approx(99.9)


def test_bad_side_rejected():
    with pytest.raises(ValueError):
        CostModel().order_charges("HOLD", 100.0, 1)


def test_unquoted_yaml_time_still_works():
    # YAML reads an unquoted 9:20 as the number 560 (and 15:15 as 915).
    # We decode those back into real times.
    raw = yaml.safe_load("risk:\n  trading_start: 9:20\n  square_off_time: 15:15\n")
    assert raw["risk"]["trading_start"] == 560
    assert raw["risk"]["square_off_time"] == 915
    cfg = validate_config(raw)
    assert cfg["risk"]["trading_start"].strftime("%H:%M") == "09:20"
    assert cfg["risk"]["square_off_time"].strftime("%H:%M") == "15:15"


def test_typo_in_setting_name_is_rejected_with_the_name_in_the_message():
    with pytest.raises(ConfigError) as err:
        validate_config({"strategy": {"stop_los_pct": 1}})
    assert "stop_los_pct" in str(err.value)


def test_times_must_be_in_order():
    with pytest.raises(ConfigError):
        validate_config({"risk": {"trading_start": "15:00", "no_new_entries_after": "14:00"}})


@pytest.mark.parametrize("bad", [
    {"capital": -5},
    {"strategy": {"quantity": 0}},
    {"strategy": {"quantity": 1.5}},
    {"strategy": {"stop_loss_pct": -1}},
    {"risk": {"max_daily_loss": 0}},
    {"costs": {"gst_pct": -1}},
])
def test_bad_values_are_rejected(bad):
    with pytest.raises(ConfigError):
        validate_config(bad)


def test_empty_config_uses_defaults():
    cfg = validate_config(None)
    assert cfg["capital"] == 100000
    assert cfg["risk"]["square_off_time"].strftime("%H:%M") == "15:15"
