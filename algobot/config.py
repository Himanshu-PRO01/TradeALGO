"""Config loading and validation.

The config is a YAML file that the trader (not just the developer) edits, so
mistakes must produce clear, friendly errors. Unknown keys are rejected on
purpose: a silently ignored typo such as "stop_los_pct" could remove a
stop-loss without anyone noticing.
"""
from __future__ import annotations

import copy
import datetime as dt
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the config file has a problem the user should fix."""


DEFAULTS: dict[str, Any] = {
    "name": "unnamed_run",
    "capital": 100000,
    "data": {"path": None},
    "strategy": {
        "name": "sma_crossover",
        "params": {},
        "quantity": 1,
        "allow_short": False,
        "stop_loss_pct": None,
        "target_pct": None,
    },
    "risk": {
        "max_daily_loss": None,
        "max_trades_per_day": None,
        "max_position_value": None,
        "trading_start": "09:15",
        "no_new_entries_after": "15:00",
        "square_off_time": "15:15",
    },
    # EXAMPLE values for Indian equity intraday. Charges change over time:
    # always check your own broker's charge calculator and edit these.
    "costs": {
        "brokerage_pct": 0.03,
        "brokerage_cap": 20.0,
        "brokerage_flat": None,
        "stt_buy_pct": 0.0,
        "stt_sell_pct": 0.025,
        "exchange_txn_pct": 0.003,
        "sebi_fee_pct": 0.0001,
        "stamp_buy_pct": 0.003,
        "gst_pct": 18.0,
        "slippage_bps": 2.0,
    },
}

TIME_FIELDS = ("trading_start", "no_new_entries_after", "square_off_time")


def _merge(base: dict, override: dict, path: str = "") -> dict:
    """Recursively merge `override` into a copy of `base`, rejecting unknown keys."""
    out = copy.deepcopy(base)
    for key, value in override.items():
        where = f"{path}{key}"
        if key not in base:
            allowed = ", ".join(base.keys())
            raise ConfigError(
                f"Unknown setting '{where}'. Allowed settings here: {allowed}"
            )
        # 'params' is free-form: each strategy checks its own parameters.
        if isinstance(base[key], dict) and key != "params" and base[key]:
            if value is None:
                continue
            if not isinstance(value, dict):
                raise ConfigError(f"'{where}' must be a section with settings inside it.")
            out[key] = _merge(base[key], value, path=f"{where}.")
        else:
            out[key] = value
    return out


def parse_time(value: Any, field: str) -> dt.time:
    """Parse "HH:MM" (or HH:MM:SS) into a time.

    YAML quirk: an unquoted 09:20 is read by YAML as the number 560
    (9 * 60 + 20). We decode that back so an unquoted time still works.
    """
    if isinstance(value, dt.time):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        hours, minutes = divmod(value, 60)
        if 0 <= hours < 24:
            return dt.time(hours, minutes)
    if isinstance(value, str):
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return dt.datetime.strptime(value.strip(), fmt).time()
            except ValueError:
                pass
    raise ConfigError(f"'{field}' must be a time like \"09:20\" (got {value!r}).")


def _positive_or_none(value: Any, field: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"'{field}' must be a number above 0, or left empty (got {value!r}).")


def _non_negative(value: Any, field: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ConfigError(f"'{field}' must be 0 or more (got {value!r}).")


def validate_config(raw: dict | None) -> dict:
    """Merge the user's settings over the defaults and check every value."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("The config file must contain settings in 'name: value' form.")
    cfg = _merge(DEFAULTS, raw)

    capital = cfg["capital"]
    if isinstance(capital, bool) or not isinstance(capital, (int, float)) or capital <= 0:
        raise ConfigError(f"'capital' must be a number above 0 (got {capital!r}).")

    strat = cfg["strategy"]
    qty = strat["quantity"]
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
        raise ConfigError(f"'strategy.quantity' must be a whole number, 1 or more (got {qty!r}).")
    if not isinstance(strat["allow_short"], bool):
        raise ConfigError("'strategy.allow_short' must be true or false.")
    _positive_or_none(strat["stop_loss_pct"], "strategy.stop_loss_pct")
    _positive_or_none(strat["target_pct"], "strategy.target_pct")
    if not isinstance(strat["params"], dict):
        raise ConfigError("'strategy.params' must be a section with settings inside it.")

    risk = cfg["risk"]
    _positive_or_none(risk["max_daily_loss"], "risk.max_daily_loss")
    _positive_or_none(risk["max_position_value"], "risk.max_position_value")
    mt = risk["max_trades_per_day"]
    if mt is not None and (isinstance(mt, bool) or not isinstance(mt, int) or mt < 1):
        raise ConfigError(f"'risk.max_trades_per_day' must be a whole number, 1 or more (got {mt!r}).")
    for f in TIME_FIELDS:
        risk[f] = parse_time(risk[f], f"risk.{f}")
    if not (risk["trading_start"] < risk["no_new_entries_after"] < risk["square_off_time"]):
        raise ConfigError(
            "Times must be in this order: risk.trading_start < risk.no_new_entries_after "
            "< risk.square_off_time."
        )

    for key, value in cfg["costs"].items():
        _non_negative(value, f"costs.{key}")

    return cfg


def load_config(path: str) -> dict:
    """Read a YAML file and return the validated config."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}")
    except yaml.YAMLError as exc:
        raise ConfigError(f"The config file is not valid YAML: {exc}")
    return validate_config(raw)
