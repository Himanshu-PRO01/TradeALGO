"""Strategies.

A strategy looks at the bars up to and including the CURRENT bar and answers
with one of:  "BUY", "SELL", "EXIT" or None (do nothing).

The engine executes the answer at the NEXT bar's open. That mirrors real
trading (you can only act after a bar has closed) and prevents look-ahead
bias, which is the classic way backtests look better than reality.

Two strategies are included:
  * sma_crossover  - a tiny demo strategy written in Python.
  * rules          - entry and exit rules written as plain expressions in the
                     config file, so a trader can change them without coding.

Both are DEMOS to prove the pipeline works. Neither is a recommendation.
"""
from __future__ import annotations

import re

import numpy as np
from typing import Callable, Optional

import pandas as pd

from .config import ConfigError
from .indicators import add_indicators, add_prev_columns, ema, rsi, sma
from .indicators import hma as _hma
from .indicators import wma

BUY, SELL, EXIT = "BUY", "SELL", "EXIT"


class Strategy:
    """Base class. Subclass it and register it with @register("name")."""

    def __init__(self, params: dict):
        self.params = params

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add indicator columns. Must only use past and current data."""
        return df

    def on_bar(self, i: int, df: pd.DataFrame, position: int) -> Optional[str]:
        """Called at the close of bar i. position: 1 long, -1 short, 0 flat."""
        return None


REGISTRY: dict[str, type] = {}


def register(name: str) -> Callable:
    def wrap(cls: type) -> type:
        REGISTRY[name] = cls
        return cls
    return wrap


def build_strategy(cfg: dict) -> Strategy:
    name = cfg["strategy"]["name"]
    if name not in REGISTRY:
        raise ConfigError(
            f"Unknown strategy '{name}'. Available: {', '.join(sorted(REGISTRY))}."
        )
    return REGISTRY[name](cfg["strategy"]["params"])


@register("sma_crossover")
class SmaCrossover(Strategy):
    """Long when the fast average is above the slow one, short (if allowed) below."""

    def __init__(self, params: dict):
        super().__init__(params)
        unknown = set(params) - {"fast", "slow"}
        if unknown:
            raise ConfigError(
                f"sma_crossover has unknown params: {', '.join(sorted(unknown))}. "
                "Allowed: fast, slow."
            )
        self.fast = params.get("fast", 10)
        self.slow = params.get("slow", 30)
        for label, val in (("fast", self.fast), ("slow", self.slow)):
            if isinstance(val, bool) or not isinstance(val, int) or val < 1:
                raise ConfigError(f"sma_crossover: '{label}' must be a whole number, 1 or more.")
        if self.fast >= self.slow:
            raise ConfigError("sma_crossover: 'fast' must be smaller than 'slow'.")

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["sma_fast"] = sma(df["close"], self.fast)
        df["sma_slow"] = sma(df["close"], self.slow)
        return df

    def on_bar(self, i: int, df: pd.DataFrame, position: int) -> Optional[str]:
        fast, slow = df["sma_fast"].iat[i], df["sma_slow"].iat[i]
        if pd.isna(fast) or pd.isna(slow):
            return None
        if fast > slow and position <= 0:
            return BUY
        if fast < slow and position >= 0:
            return SELL
        return None



@register("new_era_1_0")
class NewEraStrategy(Strategy):
    """Deterministic translation of the supplied TradingView New Era Strategy 1.0.

    The formation/signal state is kept bar-by-bar so it is not reduced to a
    simple boolean expression. Entry is decided at the signal bar close and
    the engine fills it at the next bar open, matching the project's execution
    convention.

    The supplied Pine code's stop/target are based on the signal bar close:
      short: stop=min(high[1], high), target=close-2*(stop-close)
      long:  stop=min(low[1], low),  target=close+2*(close-stop)
    """
    def __init__(self, params: dict):
        super().__init__(params)
        allowed = {"sl_max_points_percent", "target_ratio"}
        unknown = set(params) - allowed
        if unknown:
            raise ConfigError(
                "new_era_1_0 has unknown params: "
                + ", ".join(sorted(unknown))
                + ". Allowed: sl_max_points_percent, target_ratio."
            )
        self.sl_max_points_percent = float(params.get("sl_max_points_percent", 0))
        self.target_ratio = float(params.get("target_ratio", 2))
        if self.sl_max_points_percent < 0 or self.target_ratio < 0:
            raise ConfigError("New Era parameters must be 0 or greater.")
        self._reset_state()

    def _reset_state(self):
        self.sig_low = None
        self.sig_high = None
        self.active_pe = False
        self.active_ce = False
        self.trade_running_pe = False
        self.trade_running_ce = False
        self._pending_levels = None

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["rsi_5"] = rsi(df["close"], 5)
        df["rsi_smooth_5"] = sma(df["rsi_5"], 5)
        df["cci_14"] = _cci(df["close"], 14)
        df["cci_smooth_5"] = sma(df["cci_14"], 5)
        df["ema_9"] = ema(df["close"], 9)
        df["ema_33"] = ema(df["close"], 33)
        df["ema_smooth_9"] = sma(df["ema_33"], 9)
        df["hma_18"] = _hma(df["close"], 18)
        df["hma_22"] = _hma(df["close"], 22)
        df["hma_27"] = _hma(df["close"], 27)

        df["formation_pe"] = (
            (df["ema_smooth_9"] < df["ema_33"])
            & (df["ema_33"] < df["hma_27"])
            & (df["hma_27"] < df["hma_22"])
            & (df["hma_22"] < df["hma_18"])
            & (df["rsi_5"] > 65)
            & (df["rsi_smooth_5"] > 60)
            & (df["cci_14"] > 100)
            & (df["cci_smooth_5"] > 80)
        )
        df["formation_ce"] = (
            (df["ema_smooth_9"] > df["ema_33"])
            & (df["ema_33"] > df["hma_27"])
            & (df["hma_27"] > df["hma_22"])
            & (df["hma_22"] > df["hma_18"])
            & (df["rsi_5"] < 25)
            & (df["rsi_smooth_5"] < 30)
            & (df["cci_14"] < -50)
            & (df["cci_smooth_5"] < -20)
        )
        self._reset_state()
        return df

    def _in_trade_time(self, ts) -> bool:
        t = ts.time()
        return t >= pd.Timestamp("09:15").time() and t < pd.Timestamp("15:00").time()

    def on_bar(self, i: int, df: pd.DataFrame, position: int) -> Optional[str]:
        if position == 0:
            self.trade_running_pe = False
            self.trade_running_ce = False
            self._pending_levels = None

        ts = df.index[i]
        if not self._in_trade_time(ts):
            return None

        high = float(df["high"].iat[i])
        low = float(df["low"].iat[i])
        close = float(df["close"].iat[i])
        formation_pe = bool(df["formation_pe"].iat[i])
        formation_ce = bool(df["formation_ce"].iat[i])
        prev_formation_pe = bool(df["formation_pe"].iat[i - 1]) if i > 0 else False
        prev_formation_ce = bool(df["formation_ce"].iat[i - 1]) if i > 0 else False

        if not self.trade_running_pe:
            if formation_pe:
                if prev_formation_pe and self.sig_high is not None and self.sig_low is not None:
                    if (high > self.sig_high or low < self.sig_low) and close > self.sig_low:
                        self.sig_low, self.sig_high = low, high
                        self.active_pe = True
                else:
                    self.sig_low, self.sig_high = low, high
                    self.active_pe = True

            if self.active_pe and self.sig_low is not None and close > self.sig_low:
                if high > self.sig_high:
                    self.sig_low, self.sig_high = low, high
                elif low < self.sig_low:
                    self.sig_low, self.sig_high = low, high
                elif low > self.sig_low and high < self.sig_high:
                    self.sig_low, self.sig_high = low, high

            signal_pe = (
                self.active_pe
                and self.sig_low is not None
                and close < self.sig_low
                and not self.trade_running_pe
            )
            if signal_pe:
                stop = min(float(df["high"].iat[i - 1]), high) if i > 0 else high
                sl_points = stop - close
                if self.sl_max_points_percent > 0:
                    max_points = (close / 100.0) * self.sl_max_points_percent
                    if sl_points > max_points:
                        stop = high
                        sl_points = stop - close
                        if sl_points > max_points:
                            stop = 0.0
                target = close - (self.target_ratio * sl_points)
                if stop > 0:
                    self.trade_running_pe = True
                    self.active_pe = False
                    self.sig_low = self.sig_high = None
                    self._pending_levels = (stop, target)
                    return SELL

        if not self.trade_running_ce:
            if formation_ce:
                if prev_formation_ce and self.sig_low is not None and self.sig_high is not None:
                    if (low < self.sig_low or high > self.sig_high) and close < self.sig_high:
                        self.sig_low, self.sig_high = low, high
                        self.active_ce = True
                else:
                    self.sig_low, self.sig_high = low, high
                    self.active_ce = True

            if self.active_ce and self.sig_high is not None and close < self.sig_high:
                if low < self.sig_low:
                    self.sig_low, self.sig_high = low, high
                elif high > self.sig_high:
                    self.sig_low, self.sig_high = low, high
                elif high < self.sig_high and low > self.sig_low:
                    self.sig_low, self.sig_high = low, high

            signal_ce = (
                self.active_ce
                and self.sig_high is not None
                and close > self.sig_high
                and not self.trade_running_ce
            )
            if signal_ce:
                stop = min(float(df["low"].iat[i - 1]), low) if i > 0 else low
                sl_points = close - stop
                if self.sl_max_points_percent > 0:
                    max_points = (close / 100.0) * self.sl_max_points_percent
                    if sl_points > max_points:
                        stop = low
                        sl_points = close - stop
                        if sl_points > max_points:
                            stop = 0.0
                target = close + (self.target_ratio * sl_points)
                if stop > 0:
                    self.trade_running_ce = True
                    self.active_ce = False
                    self.sig_low = self.sig_high = None
                    self._pending_levels = (stop, target)
                    return BUY
        return None

    def take_pending_levels(self):
        levels = self._pending_levels
        self._pending_levels = None
        return levels


def _cci(close: pd.Series, n: int) -> pd.Series:
    typical = close
    mean = typical.rolling(n).mean()
    mean_dev = typical.rolling(n).apply(lambda x: float(np.mean(np.abs(x - np.mean(x)))), raw=True)
    return (typical - mean) / (0.015 * mean_dev.replace(0.0, np.nan))


_ALLOWED_CHARS = re.compile(r"^[A-Za-z0-9_\s\.\+\-\*/%<>=!&|()~]*$")
_RULE_NAMES = ("entry_long", "exit_long", "entry_short", "exit_short")


def check_expression(expr: str, label: str) -> None:
    """Allow only simple conditions: comparisons, arithmetic, and/or/not.

    Function calls, attribute access (like close.shift(1)) and anything that
    looks like code are rejected. Use the <column>_prev columns instead.
    """
    if not _ALLOWED_CHARS.match(expr):
        raise ConfigError(
            f"Rule '{label}' contains characters that are not allowed. Use only "
            "column names, numbers, + - * / comparisons, and/or/not and brackets."
        )
    stripped = re.sub(r"\b(and|or|not)\b", " ", expr)
    if re.search(r"[A-Za-z_]\w*\s*\(", stripped):
        raise ConfigError(f"Rule '{label}': function calls are not allowed.")
    if re.search(r"[A-Za-z_]\s*\.", stripped) or "__" in expr:
        raise ConfigError(
            f"Rule '{label}': '.' after a name is not allowed. For the previous bar "
            "use the _prev columns, for example close_prev."
        )


def evaluate_rule(df: pd.DataFrame, expr: Optional[str], label: str) -> pd.Series:
    """Evaluate a rule over all bars. Missing values (indicator warm-up) count as False."""
    if expr is None or str(expr).strip() == "":
        return pd.Series(False, index=df.index)
    expr = str(expr)
    check_expression(expr, label)
    try:
        result = df.eval(expr)
    except Exception as exc:  # pandas raises many different error types
        cols = ", ".join(c for c in df.columns)
        raise ConfigError(
            f"Rule '{label}' could not be evaluated: {exc}. Columns you can use: {cols}"
        )
    if not isinstance(result, pd.Series) or result.dtype != bool:
        raise ConfigError(
            f"Rule '{label}' must be a true/false condition such as \"close > sma_20\" "
            f"(got: {expr})."
        )
    return result.fillna(False)


@register("rules")
class RuleStrategy(Strategy):
    """Entry and exit rules written as expressions in the config file.

    params:
      indicators: [ {name: ema_fast, type: ema, period: 9}, ... ]
      entry_long / exit_long / entry_short / exit_short: "<condition>"
    """

    def __init__(self, params: dict):
        super().__init__(params)
        allowed = {"indicators", *_RULE_NAMES}
        unknown = set(params) - allowed
        if unknown:
            raise ConfigError(
                f"'rules' strategy has unknown params: {', '.join(sorted(unknown))}. "
                f"Allowed: {', '.join(sorted(allowed))}."
            )
        if not any(params.get(r) for r in _RULE_NAMES):
            raise ConfigError(
                "The 'rules' strategy needs at least one of: " + ", ".join(_RULE_NAMES)
            )
        self._rules: dict[str, pd.Series] = {}

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = add_indicators(df, self.params.get("indicators", []))
        df = add_prev_columns(df)
        for name in _RULE_NAMES:
            self._rules[name] = evaluate_rule(df, self.params.get(name), name).to_numpy()
        return df

    def on_bar(self, i: int, df: pd.DataFrame, position: int) -> Optional[str]:
        r = self._rules
        if position == 0:
            if r["entry_long"][i]:
                return BUY
            if r["entry_short"][i]:
                return SELL
        elif position == 1:
            if r["exit_long"][i]:
                return EXIT
        elif position == -1:
            if r["exit_short"][i]:
                return EXIT
        return None
