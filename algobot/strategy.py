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
from typing import Callable, Optional

import pandas as pd

from .config import ConfigError
from .indicators import add_indicators, add_prev_columns, sma

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
