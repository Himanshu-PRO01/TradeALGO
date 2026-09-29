"""Trading-style charts (Altair, which ships with Streamlit): candlesticks with trade markers,
equity with drawdown, daily P&L bars and P&L by market type.

Every function accepts small or empty inputs and returns a chart (or None when there is nothing
to draw), so a page never crashes because a session has no trades yet.
"""
from __future__ import annotations

from typing import Optional

import altair as alt
import numpy as np
import pandas as pd

from .palette import BLUE, BORDER, DOWN, MUTED, PANEL, TEXT, UP, WARN

TEXT_LINE = TEXT

alt.data_transformers.disable_max_rows()


def _style(chart):
    return (chart.configure(background=PANEL)
            .configure_view(stroke=BORDER)
            .configure_axis(gridColor=BORDER, domainColor=BORDER, tickColor=BORDER, labelColor=MUTED,
                            titleColor=MUTED, labelFontSize=11)
            .configure_legend(labelColor=MUTED, titleColor=MUTED))


def candlestick(df: pd.DataFrame, trades: Optional[pd.DataFrame] = None, hlines: Optional[dict] = None,
                height: int = 340, max_bars: int = 400, volume: bool = True,
                interval_minutes: Optional[int] = None, overlays: Optional[dict] = None,
                signals: Optional[pd.DataFrame] = None, risk_lines: Optional[dict] = None):
    """Candles (green up, red down) with optional volume, horizontal levels and trade markers.

    trades: the engine's trade table (entry_time, exit_time, side, entry_price, exit_price, net_pnl).
    hlines: {"label": price}, for example previous day high and low.
    """
    if df is None or len(df) == 0:
        return None
    d = df.tail(max_bars).copy()
    d.index.name = "datetime"
    d = d.reset_index()
    d["time"] = d["datetime"].dt.strftime("%d %b %Y %H:%M")
    d["bar_start"] = d["datetime"]
    inferred_minutes = int(interval_minutes or 1)
    if inferred_minutes < 1 and len(d) >= 2:
        diffs = d["datetime"].diff().dropna().dt.total_seconds().div(60)
        if len(diffs):
            inferred_minutes = max(1, int(diffs.mode().iloc[0]))
    d["bar_end"] = d["datetime"] + pd.Timedelta(minutes=inferred_minutes)
    d["direction"] = np.where(d["close"] >= d["open"], "up", "down")
    colour = alt.Color("direction:N", scale=alt.Scale(domain=["up", "down"], range=[UP, DOWN]), legend=None)
    x = alt.X("datetime:T", axis=alt.Axis(format="%d %b %H:%M", labelAngle=-35, labelOverlap=True, title=None))
    tip = [alt.Tooltip("datetime:T", title="Date/time", format="%d %b %Y %H:%M"), "open:Q", "high:Q", "low:Q", "close:Q"]
    wick = alt.Chart(d).mark_rule().encode(
        x=x, y=alt.Y("low:Q", scale=alt.Scale(zero=False), title=None), y2="high:Q", color=colour, tooltip=tip)
    body = alt.Chart(d).mark_bar(size=max(2.0, min(10.0, 560.0 / max(len(d), 1)))).encode(
        x=alt.X("bar_start:T", axis=alt.Axis(format="%d %b %H:%M", labelAngle=-35, labelOverlap=True, title=None)),
        x2="bar_end:T", y="open:Q", y2="close:Q", color=colour, tooltip=tip)
    layers = [wick, body]

    overlay_styles = {
        "EMA 20": BLUE,
        "EMA 50": WARN,
        "VWAP": TEXT_LINE,
        "Live price": UP,
    }
    for label, column in (overlays or {}).items():
        if column not in d.columns:
            continue
        overlay = d[["datetime", column]].dropna()
        if overlay.empty:
            continue
        layers.append(
            alt.Chart(overlay).mark_line(
                color=overlay_styles.get(label, BLUE),
                strokeWidth=1.8 if label != "Live price" else 1.4,
                strokeDash=[6, 3] if label == "Live price" else [1, 0],
            ).encode(
                x=alt.X("datetime:T", axis=alt.Axis(format="%d %b %H:%M", labelAngle=-35, labelOverlap=True, title=None)),
                y=alt.Y(f"{column}:Q", scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip("datetime:T", title="Date/time", format="%d %b %Y %H:%M"),
                    alt.Tooltip(f"{column}:Q", title=label, format=",.2f"),
                ],
            )
        )

    for label, price in (hlines or {}).items():
        if price is None or not np.isfinite(price):
            continue
        rule = alt.Chart(pd.DataFrame({"y": [float(price)], "label": [label]})).mark_rule(
            strokeDash=[5, 4], color=WARN, opacity=0.8).encode(y="y:Q")
        text = alt.Chart(pd.DataFrame({"y": [float(price)], "label": [label]})).mark_text(
            align="left", dx=4, dy=-6, color=WARN, fontSize=11).encode(y="y:Q", text="label:N", x=alt.value(4))
        layers += [rule, text]

    if signals is not None and len(signals):
        signal_rows = signals.copy()
        signal_rows["datetime"] = pd.to_datetime(signal_rows["datetime"])
        signal_rows = signal_rows[signal_rows["datetime"].isin(d["datetime"])]
        if not signal_rows.empty:
            layers.append(
                alt.Chart(signal_rows).mark_point(filled=True, size=130, opacity=0.95).encode(
                    x=alt.X("datetime:T", axis=alt.Axis(format="%d %b %H:%M", labelAngle=-35, labelOverlap=True, title=None)),
                    y=alt.Y("price:Q", scale=alt.Scale(zero=False)),
                    shape=alt.Shape("shape:N", scale=None, legend=None),
                    color=alt.Color(
                        "kind:N",
                        scale=alt.Scale(
                            domain=["BUY", "SELL"],
                            range=[UP, DOWN],
                        ),
                        legend=alt.Legend(title="Research signal"),
                    ),
                    tooltip=[
                        alt.Tooltip("datetime:T", title="Date/time", format="%d %b %Y %H:%M"),
                        alt.Tooltip("kind:N", title="Signal"),
                        alt.Tooltip("price:Q", title="Price", format=",.2f"),
                        alt.Tooltip("reason:N", title="Reason"),
                    ],
                )
            )

    for label, price in (risk_lines or {}).items():
        if price is None or not np.isfinite(price):
            continue
        layers.append(
            alt.Chart(pd.DataFrame({"y": [float(price)], "label": [label]}))
            .mark_rule(
                strokeDash=[7, 4],
                color=UP if "Target" in label else DOWN,
                opacity=0.8,
            )
            .encode(y="y:Q")
        )

    if trades is not None and len(trades):
        pos = pd.Series(d.index.to_numpy(), index=pd.DatetimeIndex(d["datetime"]))
        rows = []
        for t in trades.itertuples():
            entry, exit_ = pd.Timestamp(t.entry_time), pd.Timestamp(t.exit_time)
            if entry in pos.index:
                rows.append({"datetime": entry, "price": float(t.entry_price), "kind": "entry",
                             "shape": "triangle-up" if t.side == "LONG" else "triangle-down",
                             "note": f"{t.side} entry {t.entry_price:,.2f}"})
            if exit_ in pos.index:
                rows.append({"datetime": exit_, "price": float(t.exit_price), "kind": "win" if t.net_pnl > 0 else "loss",
                             "shape": "cross", "note": f"exit {t.exit_price:,.2f}, net {t.net_pnl:,.0f}"})
        if rows:
            m = pd.DataFrame(rows)
            layers.append(alt.Chart(m).mark_point(filled=True, size=90, opacity=0.95).encode(
                x=alt.X("datetime:T", axis=alt.Axis(format="%d %b %H:%M", labelAngle=-35, labelOverlap=True, title=None)), y=alt.Y("price:Q", scale=alt.Scale(zero=False)),
                shape=alt.Shape("shape:N", scale=None, legend=None),
                color=alt.Color("kind:N", scale=alt.Scale(domain=["entry", "win", "loss"], range=[BLUE, UP, DOWN]), legend=None),
                tooltip=["note:N"]))

    price_chart = alt.layer(*layers).properties(height=height, width="container")
    if not volume or "volume" not in d.columns or float(d["volume"].sum()) == 0.0:
        return _style(price_chart.interactive())
    vol = alt.Chart(d).mark_bar(opacity=0.5).encode(
        x=alt.X("datetime:T", axis=alt.Axis(format="%d %b %H:%M", labelAngle=-35, labelOverlap=True, title=None)),
        y=alt.Y("volume:Q", title=None, axis=alt.Axis(labels=False, ticks=False)), color=colour).properties(height=60, width="container")
    # resolve_scale(x="shared") keeps the price and volume panels lined up while zoomed or
    # panned; .interactive() turns on scroll-to-zoom and click-drag-to-pan like a real charting app.
    combo = alt.vconcat(price_chart, vol, spacing=2).resolve_scale(x="shared", y="independent")
    return _style(combo.interactive())


def rsi_chart(series: pd.Series, period: int = 14, height: int = 170):
    """Render RSI with 30/70 reference levels."""
    if series is None or len(series) < max(period + 2, 16):
        return None
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < period + 2:
        return None
    delta = values.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)
    rsi_df = pd.DataFrame({"datetime": rsi.index, "rsi": rsi.to_numpy()})
    line = alt.Chart(rsi_df).mark_line(color=BLUE, strokeWidth=1.7).encode(
        x=alt.X("datetime:T", axis=alt.Axis(format="%d %b %H:%M", labelAngle=-35, labelOverlap=True, title=None)),
        y=alt.Y("rsi:Q", scale=alt.Scale(domain=[0, 100]), title="RSI"),
        tooltip=[
            alt.Tooltip("datetime:T", title="Date/time", format="%d %b %Y %H:%M"),
            alt.Tooltip("rsi:Q", title="RSI", format=".1f"),
        ],
    )
    refs = alt.Chart(pd.DataFrame({"y": [30, 70]})).mark_rule(
        strokeDash=[5, 4], color=MUTED, opacity=0.7
    ).encode(y="y:Q")
    return _style((line + refs).properties(height=height, width="container").interactive())


def equity_drawdown(equity: pd.Series, height: int = 300):
    """Equity line on top, drawdown (how far below the previous peak) underneath."""
    if equity is None or len(equity) < 2:
        return None
    d = pd.DataFrame({"bar": np.arange(len(equity)), "equity": equity.to_numpy(dtype=float)})
    d["time"] = pd.DatetimeIndex(equity.index).strftime("%d %b %H:%M")
    d["drawdown"] = d["equity"] - d["equity"].cummax()
    x = alt.X("bar:Q", axis=alt.Axis(labels=False, ticks=False, title=None), scale=alt.Scale(nice=False))
    start = float(d["equity"].iloc[0])
    line = alt.Chart(d).mark_line(color=BLUE, strokeWidth=1.6).encode(
        x=x, y=alt.Y("equity:Q", scale=alt.Scale(zero=False), title="equity"), tooltip=["time:N", "equity:Q"])
    base = alt.Chart(pd.DataFrame({"y": [start]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    dd = alt.Chart(d).mark_area(color=DOWN, opacity=0.45, line={"color": DOWN}).encode(
        x=x, y=alt.Y("drawdown:Q", title="drawdown"), tooltip=["time:N", "drawdown:Q"]).properties(height=90)
    return _style(alt.vconcat((line + base).properties(height=height), dd, spacing=4))


def pnl_bars(values: pd.Series, height: int = 220, title: str = "P&L"):
    """One bar per item (day, trade or market type), green above zero and red below."""
    if values is None or len(values) == 0:
        return None
    d = pd.DataFrame({"label": [str(i) for i in values.index], "pnl": values.to_numpy(dtype=float)})
    d["side"] = np.where(d["pnl"] >= 0, "profit", "loss")
    chart = alt.Chart(d).mark_bar().encode(
        x=alt.X("label:N", sort=None, title=None, axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("pnl:Q", title=title),
        color=alt.Color("side:N", scale=alt.Scale(domain=["profit", "loss"], range=[UP, DOWN]), legend=None),
        tooltip=["label:N", alt.Tooltip("pnl:Q", format=",.0f")]).properties(height=height)
    return _style(chart)


def premium_line(series: pd.Series, entry: Optional[float] = None, stop: Optional[float] = None, height: int = 150):
    """The option's price over time, with the entry and stop levels if a trade is open."""
    if series is None or len(series) < 2:
        return None
    d = pd.DataFrame({"bar": np.arange(len(series)), "premium": series.to_numpy(dtype=float)})
    d["time"] = pd.DatetimeIndex(series.index).strftime("%d %b %H:%M")
    x = alt.X("bar:Q", axis=alt.Axis(labels=False, ticks=False, title=None), scale=alt.Scale(nice=False))
    layers = [alt.Chart(d).mark_line(color=WARN, strokeWidth=1.6).encode(
        x=x, y=alt.Y("premium:Q", scale=alt.Scale(zero=False), title="option price"), tooltip=["time:N", alt.Tooltip("premium:Q", format=".2f")])]
    for value, colour in ((entry, BLUE), (stop, DOWN)):
        if value:
            layers.append(alt.Chart(pd.DataFrame({"y": [float(value)]})).mark_rule(color=colour, strokeDash=[5, 4]).encode(y="y:Q"))
    return _style(alt.layer(*layers).properties(height=height, width="container").interactive())


def payoff_chart(curve: pd.DataFrame, breakeven_move: Optional[float] = None, height: int = 280):
    """Profit or loss per lot against how far the index has moved. Green above zero, red below."""
    if curve is None or len(curve) < 3:
        return None
    d = curve.copy()
    d["side"] = np.where(d["pnl_per_lot"] >= 0, "profit", "loss")
    area = alt.Chart(d).mark_area(opacity=0.35, interpolate="monotone").encode(
        x=alt.X("move:Q", title="index move when you sell (points)"),
        y=alt.Y("pnl_per_lot:Q", title="profit or loss per lot (Rs)"),
        color=alt.Color("side:N", scale=alt.Scale(domain=["profit", "loss"], range=[UP, DOWN]), legend=None))
    line = alt.Chart(d).mark_line(color=TEXT_LINE, strokeWidth=1.8, interpolate="monotone").encode(
        x="move:Q", y="pnl_per_lot:Q", tooltip=[alt.Tooltip("move:Q", format=",.0f"), alt.Tooltip("pnl_per_lot:Q", format=",.0f")])
    zero = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y="y:Q")
    layers = [area, line, zero]
    if breakeven_move is not None and np.isfinite(breakeven_move):
        layers.append(alt.Chart(pd.DataFrame({"x": [float(breakeven_move)]})).mark_rule(color=WARN, strokeDash=[5, 4]).encode(x="x:Q"))
    return _style(alt.layer(*layers).properties(height=height))
