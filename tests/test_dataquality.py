import pandas as pd

from algobot.data import generate_sample_data
from algobot.dataquality import data_quality_report, format_data_quality


def messages(df):
    return " | ".join(i.message for i in data_quality_report(df))


def test_clean_sample_data_has_no_warnings():
    df = generate_sample_data(days=6, seed=1)
    assert [i for i in data_quality_report(df) if i.severity == "WARN"] == []
    assert "No problems found" in format_data_quality(data_quality_report(df), df) or "Nothing serious" in \
        format_data_quality(data_quality_report(df), df)


def test_missing_bars_inside_a_day_are_found():
    df = generate_sample_data(days=4, seed=1)
    holed = df.drop(df.index[[100, 101, 102, 103]])
    assert "4 bar(s) are missing inside trading days" in messages(holed)


def test_a_day_with_far_too_few_bars_is_found():
    df = generate_sample_data(days=6, seed=1)
    third = df.index.normalize() == df.index.normalize().unique()[2]
    short = df[~(third & (df.index.hour >= 11))]
    assert "far fewer bars" in messages(short)


def test_bars_outside_the_session_and_on_weekends_are_found():
    df = generate_sample_data(days=3, seed=1)
    extra = df.iloc[[0]].copy()
    extra.index = pd.DatetimeIndex(["2025-01-01 07:00"])
    assert "outside 09:15 to 15:30" in messages(pd.concat([extra, df]).sort_index())
    sat = df.iloc[[5]].copy()
    sat.index = pd.DatetimeIndex(["2025-01-04 10:00"])                       # a Saturday
    assert "Saturday or Sunday" in messages(pd.concat([df, sat]).sort_index())


def test_a_bad_tick_spike_is_found():
    df = generate_sample_data(days=3, seed=1)
    bad = df.copy()
    k = 50
    bad.iloc[k, bad.columns.get_loc("close")] = bad["close"].iloc[k] * 1.20
    bad.iloc[k, bad.columns.get_loc("high")] = bad["close"].iloc[k]
    assert "above 5%" in messages(bad)


def test_a_frozen_feed_is_found():
    df = generate_sample_data(days=3, seed=1)
    frozen = df.copy()
    price = frozen["close"].iloc[20]
    for col in ("open", "high", "low", "close"):
        frozen.iloc[20:30, frozen.columns.get_loc(col)] = price
    assert "identical flat bars" in messages(frozen)


def test_missing_volume_is_noted_not_alarmed():
    df = generate_sample_data(days=3, seed=1)
    df["volume"] = 0.0
    issues = data_quality_report(df)
    assert any(i.severity == "INFO" and "no volume data" in i.message for i in issues)
