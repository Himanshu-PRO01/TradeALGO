import pandas as pd
import pytest

from algobot.config import load_config
from algobot.data import DataError, generate_sample_data, load_csv
from algobot.engine import run_backtest
from algobot.metrics import compute_metrics
from algobot.strategy import build_strategy


def _write(tmp_path, text, name="d.csv"):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def test_load_csv_accepts_common_layout_and_optional_volume(tmp_path):
    p = _write(tmp_path, "Datetime,Open,High,Low,Close\n"
                         "2025-01-06 09:20,101,102,100,101.5\n"
                         "2025-01-06 09:15,100,101,99,100.5\n")
    df = load_csv(p)
    assert df.index.is_monotonic_increasing          # sorted for us
    assert "volume" in df.columns and len(df) == 2


@pytest.mark.parametrize("body, message", [
    ("datetime,open,high,low,close\n2025-01-06 09:15,100,99,101,100\n", "high below low"),
    ("datetime,open,high,low,close\n2025-01-06 09:15,100,101,99,\n", "missing"),
    ("datetime,open,high,low,close\n2025-01-06 09:15,-1,101,99,100\n", "negative"),
    ("open,high,low,close\n100,101,99,100\n", "time column"),
    ("datetime,open,high,low\n2025-01-06 09:15,100,101,99\n", "missing columns"),
])
def test_load_csv_rejects_bad_data(tmp_path, body, message):
    with pytest.raises(DataError, match=message):
        load_csv(_write(tmp_path, body))


def test_missing_file_gives_friendly_error(tmp_path):
    with pytest.raises(DataError, match="not found"):
        load_csv(str(tmp_path / "nope.csv"))


def test_sample_data_is_valid_reproducible_and_intraday():
    a = generate_sample_data(days=4, seed=1)
    b = generate_sample_data(days=4, seed=1)
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 4 * 75
    assert a.index[0].strftime("%H:%M") == "09:15" and a.index[74].strftime("%H:%M") == "15:25"


def test_metrics_on_known_trades():
    trades = pd.DataFrame({
        "entry_time": pd.to_datetime(["2025-01-06 09:20", "2025-01-06 10:00", "2025-01-07 09:20"]),
        "gross_pnl": [120.0, -40.0, 60.0],
        "costs": [20.0, 10.0, 10.0],
        "net_pnl": [100.0, -50.0, 50.0],
    })
    idx = pd.to_datetime(["2025-01-06 09:15", "2025-01-06 15:25", "2025-01-07 15:25"])
    equity = pd.Series([1000.0, 1100.0, 1050.0], index=idx)
    m = compute_metrics(trades, equity, 1000.0)
    assert m["trades"] == 3 and m["days_traded"] == 2
    assert m["win_rate_pct"] == pytest.approx(200 / 3)
    assert m["profit_factor"] == pytest.approx(150 / 50)
    assert m["expectancy_per_trade"] == pytest.approx(100 / 3)
    assert m["total_costs"] == pytest.approx(40.0)
    assert m["max_drawdown"] == pytest.approx(-50.0)


def test_metrics_with_no_trades():
    idx = pd.to_datetime(["2025-01-06 09:15", "2025-01-06 09:20"])
    m = compute_metrics(pd.DataFrame(columns=["net_pnl"]), pd.Series([1000.0, 1000.0], index=idx), 1000.0)
    assert m["trades"] == 0 and m["net_pnl"] == 0 and m["win_rate_pct"] is None


@pytest.mark.parametrize("config", ["configs/demo_sma.yaml", "configs/demo_rules.yaml"])
def test_demo_configs_run_end_to_end_and_the_books_balance(config):
    cfg = load_config(config)
    df = generate_sample_data(days=15, seed=5)
    res = run_backtest(df, cfg, build_strategy(cfg))
    assert len(res.equity) == len(df)
    assert res.metrics["net_pnl"] == pytest.approx(res.trades["net_pnl"].sum())
    # No position may ever be left open overnight.
    assert (pd.to_datetime(res.trades["exit_time"]).dt.date
            >= pd.to_datetime(res.trades["entry_time"]).dt.date).all()
    same_day = (pd.to_datetime(res.trades["exit_time"]).dt.date
                == pd.to_datetime(res.trades["entry_time"]).dt.date)
    assert same_day.all()
    # Costs must always reduce results.
    assert res.metrics["total_costs"] > 0
    assert res.metrics["net_pnl"] == pytest.approx(res.metrics["gross_pnl"] - res.metrics["total_costs"])
