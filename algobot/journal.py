"""Trade journal, daily P&L report and review statistics.

Why a journal: the brother keeps no trade log, so there is nothing to test
against and nothing to learn from. Every trade written down here (with the
setup, the stop and the lesson) becomes real data that the two of them can
review together, and it is what turns a "feeling" about a strategy into
numbers.
"""
from __future__ import annotations

import datetime as dt
import html
import sqlite3
from dataclasses import dataclass
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    opened_at    TEXT NOT NULL,
    closed_at    TEXT,
    instrument   TEXT NOT NULL,
    side         TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty          INTEGER NOT NULL CHECK (qty > 0),
    entry_price  REAL NOT NULL CHECK (entry_price > 0),
    exit_price   REAL,
    stop_price   REAL,
    target_price REAL,
    charges      REAL NOT NULL DEFAULT 0,
    setup        TEXT NOT NULL DEFAULT '',
    notes        TEXT NOT NULL DEFAULT '',
    lessons      TEXT NOT NULL DEFAULT ''
)
"""


class JournalError(ValueError):
    """Raised for input the user should correct."""


def _parse_time(value: Optional[str], label: str) -> str:
    if value is None:
        return dt.datetime.now().replace(second=0, microsecond=0).isoformat(sep=" ")
    try:
        return dt.datetime.fromisoformat(str(value).strip()).isoformat(sep=" ")
    except ValueError:
        raise JournalError(f"{label} must look like 2026-09-21 10:15 (got {value!r}).")


@dataclass
class Trade:
    id: int
    opened_at: str
    closed_at: Optional[str]
    instrument: str
    side: str
    qty: int
    entry_price: float
    exit_price: Optional[float]
    stop_price: Optional[float]
    target_price: Optional[float]
    charges: float
    setup: str
    notes: str
    lessons: str

    @property
    def is_closed(self) -> bool:
        return self.exit_price is not None

    @property
    def gross_pnl(self) -> Optional[float]:
        if not self.is_closed:
            return None
        direction = 1 if self.side == "BUY" else -1
        return direction * (self.exit_price - self.entry_price) * self.qty

    @property
    def net_pnl(self) -> Optional[float]:
        return None if self.gross_pnl is None else self.gross_pnl - self.charges

    @property
    def risk_amount(self) -> Optional[float]:
        if self.stop_price is None:
            return None
        return abs(self.entry_price - self.stop_price) * self.qty

    @property
    def r_multiple(self) -> Optional[float]:
        """Net result measured in units of the amount risked (1R = the planned loss)."""
        if self.net_pnl is None or not self.risk_amount:
            return None
        return self.net_pnl / self.risk_amount

    @property
    def closed_date(self) -> Optional[dt.date]:
        return dt.datetime.fromisoformat(self.closed_at).date() if self.closed_at else None

    @property
    def opened_date(self) -> dt.date:
        return dt.datetime.fromisoformat(self.opened_at).date()


class Journal:
    def __init__(self, path: str = ":memory:", check_same_thread: bool = True):
        # A dashboard session keeps a journal alive across page reruns, which may run in different
        # threads (one at a time). Such callers pass check_same_thread=False.
        self.db = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.db.execute(SCHEMA)
        self.db.commit()

    def close_db(self) -> None:
        self.db.close()

    # ------------------------------------------------------------ writing
    def add_trade(
        self, instrument: str, side: str, qty: int, entry_price: float,
        opened_at: Optional[str] = None, stop_price: Optional[float] = None,
        target_price: Optional[float] = None, setup: str = "", notes: str = "",
    ) -> int:
        side = str(side).upper().strip()
        if side not in ("BUY", "SELL"):
            raise JournalError("side must be BUY or SELL")
        if not str(instrument).strip():
            raise JournalError("instrument cannot be empty (for example: NIFTY 24500 CE 25-Sep)")
        if int(qty) != qty or qty < 1:
            raise JournalError("qty must be a whole number, 1 or more (units, not lots)")
        if entry_price <= 0:
            raise JournalError("entry_price must be above 0")
        if stop_price is not None:
            if stop_price <= 0:
                raise JournalError("stop_price must be above 0")
            if side == "BUY" and stop_price >= entry_price:
                raise JournalError("For a BUY the stop must be BELOW the entry price")
            if side == "SELL" and stop_price <= entry_price:
                raise JournalError("For a SELL the stop must be ABOVE the entry price")
        cur = self.db.execute(
            "INSERT INTO trades (opened_at, instrument, side, qty, entry_price, stop_price, target_price, setup, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (_parse_time(opened_at, "opened_at"), instrument.strip(), side, int(qty), float(entry_price),
             stop_price, target_price, setup.strip(), notes.strip()),
        )
        self.db.commit()
        return int(cur.lastrowid)

    def close_trade(
        self, trade_id: int, exit_price: float, closed_at: Optional[str] = None,
        charges: float = 0.0, lessons: str = "",
    ) -> Trade:
        trade = self.get(trade_id)
        if trade.is_closed:
            raise JournalError(f"Trade {trade_id} is already closed.")
        if exit_price <= 0:
            raise JournalError("exit_price must be above 0")
        if charges < 0:
            raise JournalError("charges cannot be negative")
        closed = _parse_time(closed_at, "closed_at")
        if dt.datetime.fromisoformat(closed) < dt.datetime.fromisoformat(trade.opened_at):
            raise JournalError("closed_at cannot be before opened_at")
        self.db.execute(
            "UPDATE trades SET exit_price = ?, closed_at = ?, charges = ?, lessons = ? WHERE id = ?",
            (float(exit_price), closed, float(charges), lessons.strip(), trade_id),
        )
        self.db.commit()
        return self.get(trade_id)

    def import_rows(self, rows: list) -> int:
        """Add trades from exported rows, through the same checks as typing them in. Returns how many."""
        count = 0
        for row in rows:
            def clean(key, default=None):
                value = row.get(key, default)
                return default if value is None or (isinstance(value, float) and value != value) or value == "" else value
            trade_id = self.add_trade(
                str(clean("instrument", "")), str(clean("side", "")), int(clean("qty", 0)), float(clean("entry_price", 0)),
                opened_at=str(clean("opened_at")) if clean("opened_at") else None,
                stop_price=float(clean("stop_price")) if clean("stop_price") is not None else None,
                target_price=float(clean("target_price")) if clean("target_price") is not None else None,
                setup=str(clean("setup", "")), notes=str(clean("notes", "")))
            if clean("exit_price") is not None:
                self.close_trade(trade_id, float(clean("exit_price")),
                                 closed_at=str(clean("closed_at")) if clean("closed_at") else None,
                                 charges=float(clean("charges", 0.0)), lessons=str(clean("lessons", "")))
            count += 1
        return count

    # ------------------------------------------------------------ reading
    def _rows(self, where: str = "", params: tuple = ()) -> list[Trade]:
        cur = self.db.execute(
            "SELECT id, opened_at, closed_at, instrument, side, qty, entry_price, exit_price, stop_price, "
            f"target_price, charges, setup, notes, lessons FROM trades {where} ORDER BY id", params)
        return [Trade(*row) for row in cur.fetchall()]

    def get(self, trade_id: int) -> Trade:
        rows = self._rows("WHERE id = ?", (trade_id,))
        if not rows:
            raise JournalError(f"There is no trade with id {trade_id}.")
        return rows[0]

    def all_trades(self) -> list[Trade]:
        return self._rows()

    def open_trades(self) -> list[Trade]:
        return self._rows("WHERE exit_price IS NULL")

    def closed_between(self, start: Optional[dt.date] = None, end: Optional[dt.date] = None) -> list[Trade]:
        out = []
        for t in self._rows("WHERE exit_price IS NOT NULL"):
            d = t.closed_date
            if (start is None or d >= start) and (end is None or d <= end):
                out.append(t)
        return out


# ---------------------------------------------------------------- reports
def _rs(x: Optional[float]) -> str:
    return "-" if x is None else f"{x:,.2f}"


def build_daily_report(
    journal: Journal, day: dt.date, capital: Optional[float] = None,
    max_loss_per_trade: Optional[float] = None, max_daily_loss: Optional[float] = None,
    max_trades_per_day: Optional[int] = None,
) -> dict:
    todays = journal.closed_between(day, day)
    upto = journal.closed_between(None, day)
    net = sum(t.net_pnl for t in todays)
    flags: list[str] = []
    for t in todays:
        if max_loss_per_trade is not None and t.net_pnl < -max_loss_per_trade:
            flags.append(f"Trade #{t.id} lost Rs {-t.net_pnl:,.2f}, more than the per-trade limit of Rs {max_loss_per_trade:,.2f}.")
        if t.stop_price is None:
            flags.append(f"Trade #{t.id} has no stop-loss recorded.")
    if max_daily_loss is not None and net < -max_daily_loss:
        flags.append(f"The day's loss of Rs {-net:,.2f} is beyond the daily limit of Rs {max_daily_loss:,.2f}.")
    if max_trades_per_day is not None and len(todays) > max_trades_per_day:
        flags.append(f"{len(todays)} trades were closed today; the plan was at most {max_trades_per_day}.")
    still_open = [t for t in journal.open_trades() if t.opened_date <= day]
    for t in still_open:
        if t.stop_price is None:
            flags.append(f"Open trade #{t.id} ({t.instrument}) has no stop-loss recorded.")
    return {
        "date": day, "trades": todays, "open_trades": still_open,
        "wins": sum(1 for t in todays if t.net_pnl > 0),
        "losses": sum(1 for t in todays if t.net_pnl <= 0),
        "gross": sum(t.gross_pnl for t in todays),
        "charges": sum(t.charges for t in todays),
        "net": net,
        "cumulative_net": sum(t.net_pnl for t in upto),
        "capital": capital, "flags": flags,
    }


def format_daily_report_text(rep: dict) -> str:
    lines = [f"DAILY P&L REPORT: {rep['date']:%A, %d %B %Y}", "=" * 60]
    if rep["trades"]:
        lines.append(f"{'#':>3} {'Instrument':<24} {'Side':<4} {'Qty':>5} {'Entry':>9} {'Exit':>9} {'Net P&L':>10} {'R':>6}")
        for t in rep["trades"]:
            r = "-" if t.r_multiple is None else f"{t.r_multiple:+.2f}"
            lines.append(f"{t.id:>3} {t.instrument[:24]:<24} {t.side:<4} {t.qty:>5} {t.entry_price:>9.2f} "
                         f"{t.exit_price:>9.2f} {t.net_pnl:>10.2f} {r:>6}")
    else:
        lines.append("No trades were closed today.")
    lines += [
        "-" * 60,
        f"Trades closed:  {len(rep['trades'])}  (wins {rep['wins']}, losses {rep['losses']})",
        f"Before charges: Rs {_rs(rep['gross'])}",
        f"Charges:        Rs {_rs(rep['charges'])}",
        f"Net for the day: Rs {_rs(rep['net'])}",
        f"Net since start: Rs {_rs(rep['cumulative_net'])}",
    ]
    if rep["capital"]:
        lines.append(f"Day as % of capital: {rep['net'] / rep['capital'] * 100:+.2f}%")
    if rep["open_trades"]:
        lines.append("Open positions:")
        for t in rep["open_trades"]:
            stop = "no stop" if t.stop_price is None else f"stop {t.stop_price:g}"
            lines.append(f"  #{t.id} {t.side} {t.qty} {t.instrument} @ {t.entry_price:g} ({stop})")
    lessons = [(t.id, t.lessons) for t in rep["trades"] if t.lessons]
    if lessons:
        lines.append("Lessons written today:")
        lines += [f"  #{i}: {text}" for i, text in lessons]
    if rep["flags"]:
        lines.append("Check these:")
        lines += [f"  ! {f}" for f in rep["flags"]]
    return "\n".join(lines)


def format_daily_report_html(rep: dict) -> str:
    e = html.escape
    rows = "".join(
        f"<tr><td>{t.id}</td><td>{e(t.instrument)}</td><td>{t.side}</td><td>{t.qty}</td>"
        f"<td>{t.entry_price:.2f}</td><td>{t.exit_price:.2f}</td>"
        f"<td class=\"{'gain' if t.net_pnl > 0 else 'loss'}\">{t.net_pnl:,.2f}</td>"
        f"<td>{'-' if t.r_multiple is None else format(t.r_multiple, '+.2f')}</td>"
        f"<td>{e(t.setup)}</td><td>{e(t.notes)}</td></tr>"
        for t in rep["trades"]
    ) or "<tr><td colspan=\"10\">No trades were closed today.</td></tr>"
    flags = "".join(f"<li>{e(f)}</li>" for f in rep["flags"])
    lessons = "".join(f"<li>#{t.id}: {e(t.lessons)}</li>" for t in rep["trades"] if t.lessons)
    net_class = "gain" if rep["net"] > 0 else "loss"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Daily P&amp;L {rep['date']}</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;max-width:960px}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd;padding:6px 8px;text-align:left}}
th{{background:#1f3a5f;color:#fff}}.gain{{color:#0a7a3d}}.loss{{color:#b3261e}}
.flags{{background:#fff4e5;border:1px solid #f5c26b;padding:.5rem 1rem}}</style></head><body>
<h1>Daily P&amp;L report: {rep['date']:%A, %d %B %Y}</h1>
<table><tr><th>#</th><th>Instrument</th><th>Side</th><th>Qty</th><th>Entry</th><th>Exit</th><th>Net P&amp;L</th><th>R</th><th>Setup</th><th>Notes</th></tr>{rows}</table>
<p>Trades closed: <b>{len(rep['trades'])}</b> (wins {rep['wins']}, losses {rep['losses']}).
Before charges: Rs {_rs(rep['gross'])}. Charges: Rs {_rs(rep['charges'])}.
Net for the day: <b class="{net_class}">Rs {_rs(rep['net'])}</b>. Net since start: Rs {_rs(rep['cumulative_net'])}.</p>
{'<h3>Lessons written today</h3><ul>' + lessons + '</ul>' if lessons else ''}
{'<div class="flags"><b>Check these:</b><ul>' + flags + '</ul></div>' if flags else ''}
<p><small>Generated by algobot. Not financial advice.</small></p></body></html>"""


def behavior_flags(
    trades: list, max_loss_per_trade: Optional[float] = None, max_trades_per_day: Optional[int] = None,
    max_daily_loss: Optional[float] = None, revenge_minutes: int = 15,
) -> list:
    """Look for the habits that, more than any strategy, drain small accounts.

    A strategy tested at "stop at 1R" is a different strategy from the one that
    is traded when stops are moved, losses are chased and limits are ignored.
    """
    flags: list[str] = []
    closed = sorted((t for t in trades if t.is_closed), key=lambda t: t.closed_at)
    everything = sorted(trades, key=lambda t: t.opened_at)

    for t in closed:
        if t.risk_amount and t.net_pnl < -1.25 * t.risk_amount:
            flags.append(f"Trade #{t.id} lost {-t.net_pnl / t.risk_amount:.1f}x the amount planned at the stop: "
                         "the stop was moved or ignored.")
        if max_loss_per_trade is not None and t.net_pnl < -max_loss_per_trade:
            flags.append(f"Trade #{t.id} lost Rs {-t.net_pnl:,.2f}, beyond the per-trade limit of Rs {max_loss_per_trade:,.2f}.")

    for loser in (t for t in closed if t.net_pnl <= 0):
        lost_at = dt.datetime.fromisoformat(loser.closed_at)
        for nxt in everything:
            gap = (dt.datetime.fromisoformat(nxt.opened_at) - lost_at).total_seconds() / 60.0
            if nxt.id != loser.id and 0 <= gap <= revenge_minutes:
                flags.append(f"Trade #{nxt.id} was opened {gap:.0f} minutes after losing trade #{loser.id}: "
                             "possible revenge trade.")

    by_day: dict = {}
    for t in everything:
        by_day.setdefault(t.opened_date, []).append(t)
    for day, day_trades in sorted(by_day.items()):
        if max_trades_per_day is not None and len(day_trades) > max_trades_per_day:
            flags.append(f"{len(day_trades)} trades were opened on {day}; the plan was at most {max_trades_per_day}.")
        if max_daily_loss is not None:
            for t in day_trades:
                opened = dt.datetime.fromisoformat(t.opened_at)
                realized = sum(x.net_pnl for x in day_trades
                               if x.is_closed and x.id != t.id and dt.datetime.fromisoformat(x.closed_at) <= opened)
                if realized <= -max_daily_loss:
                    flags.append(f"Trade #{t.id} was opened after the daily loss limit of Rs {max_daily_loss:,.0f} "
                                 f"had already been reached on {day}.")

    def hold_minutes(t):
        return (dt.datetime.fromisoformat(t.closed_at) - dt.datetime.fromisoformat(t.opened_at)).total_seconds() / 60.0
    winners = [hold_minutes(t) for t in closed if t.net_pnl > 0]
    losers = [hold_minutes(t) for t in closed if t.net_pnl <= 0]
    if len(winners) >= 5 and len(losers) >= 5 and sum(losers) / len(losers) > 1.5 * sum(winners) / len(winners):
        flags.append("Losing trades are held much longer than winning trades on average: a common habit of "
                     "hoping a loser comes back while cutting winners short.")
    return list(dict.fromkeys(flags))


def review_stats(trades: list) -> dict:
    """Statistics over closed trades: what a weekly review looks at."""
    closed = [t for t in trades if t.is_closed]
    n = len(closed)
    out: dict = {"trades": n}
    if not n:
        return out
    nets = [t.net_pnl for t in closed]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    loss_sum = -sum(losses)
    rs = [t.r_multiple for t in closed if t.r_multiple is not None]
    streak = best_streak = 0
    for x in nets:
        streak = streak + 1 if x <= 0 else 0
        best_streak = max(best_streak, streak)
    by_setup: dict = {}
    for t in closed:
        by_setup.setdefault(t.setup or "(no setup written)", []).append(t.net_pnl)
    out.update({
        "net": sum(nets), "charges": sum(t.charges for t in closed),
        "win_rate_pct": len(wins) / n * 100,
        "avg_win": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss": sum(losses) / len(losses) if losses else 0.0,
        "profit_factor": (sum(wins) / loss_sum) if loss_sum > 0 else (float("inf") if wins else None),
        "expectancy": sum(nets) / n,
        "avg_r": sum(rs) / len(rs) if rs else None,
        "r_trades": len(rs),
        "best": max(nets), "worst": min(nets),
        "max_losing_streak": best_streak,
        "without_stop": sum(1 for t in closed if t.stop_price is None),
        "by_setup": {k: (len(v), sum(v)) for k, v in by_setup.items()},
    })
    return out


def format_review(stats: dict, flags: Optional[list] = None) -> str:
    if not stats.get("trades"):
        return "No closed trades in this period yet."
    pf = stats["profit_factor"]
    pf_text = "n/a" if pf is None else ("infinite" if pf == float("inf") else f"{pf:.2f}")
    lines = [
        f"REVIEW: {stats['trades']} closed trade{'s' if stats['trades'] != 1 else ''}",
        "-" * 44,
        f"Net P&L:            Rs {stats['net']:,.2f}  (charges Rs {stats['charges']:,.2f} included)",
        f"Win rate:           {stats['win_rate_pct']:.0f}%",
        f"Average win / loss: Rs {stats['avg_win']:,.2f} / Rs {stats['avg_loss']:,.2f}",
        f"Profit factor:      {pf_text}",
        f"Expectancy/trade:   Rs {stats['expectancy']:,.2f}",
        "Average R:          " + ("n/a (no stops recorded)" if stats["avg_r"] is None
                                  else f"{stats['avg_r']:+.2f} over {stats['r_trades']} trades with a stop"),
        f"Best / worst trade: Rs {stats['best']:,.2f} / Rs {stats['worst']:,.2f}",
        f"Longest losing run: {stats['max_losing_streak']} trades",
        f"Trades with no stop recorded: {stats['without_stop']}",
        "By setup:",
    ]
    for name, (count, total) in sorted(stats["by_setup"].items(), key=lambda kv: -kv[1][1]):
        lines.append(f"  {name}: {count} trade(s), Rs {total:,.2f}")
    if flags is not None:
        lines.append("Behaviour checks:")
        lines += [f"  ! {f}" for f in flags] if flags else ["  No rule breaks found."]
    if stats["trades"] < 30:
        lines.append(f"Note: {stats['trades']} trade(s) is a small sample. Do not read much into these numbers before about 30 to 50 trades.")
    return "\n".join(lines)


JOURNAL_COLUMNS = ["id", "opened_at", "closed_at", "instrument", "side", "qty", "entry_price", "exit_price",
                   "stop_price", "target_price", "charges", "setup", "notes", "lessons"]


def journal_to_csv(journal: Journal) -> str:
    """Every trade as CSV text, for backup or to send to someone."""
    import pandas as pd
    rows = [{c: getattr(t, c) for c in JOURNAL_COLUMNS} for t in journal.all_trades()]
    return pd.DataFrame(rows, columns=JOURNAL_COLUMNS).to_csv(index=False)


def journal_rows_from_csv(text: str) -> list:
    """Parse CSV text made by journal_to_csv into rows for Journal.import_rows."""
    import io
    import pandas as pd
    try:
        frame = pd.read_csv(io.StringIO(text))
    except Exception as exc:
        raise JournalError(f"That file could not be read as a journal CSV: {exc}")
    missing = [c for c in ("opened_at", "instrument", "side", "qty", "entry_price") if c not in frame.columns]
    if missing:
        raise JournalError("That CSV is missing columns: " + ", ".join(missing))
    return frame.astype(object).where(frame.notna(), None).to_dict("records")
