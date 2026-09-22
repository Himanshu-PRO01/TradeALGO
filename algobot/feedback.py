"""Suggestions from the brother (or anyone) about what to change.

Feedback is stored locally in feedback.csv when running on your own computer, or only in the browser
session when hosted. Either way it can be downloaded or copied as text and sent back on WhatsApp.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import os
from dataclasses import asdict, dataclass, fields
from typing import Optional

AREAS = ["Trading Desk (home)", "Position size", "Journal and report", "Practice room",
         "Option breakeven and ruin", "Backtest", "Reality check", "Test lab", "Something else"]
KINDS = ["Something is wrong or confusing", "A number or a trading term is wrong", "A feature is missing",
         "An idea for a strategy rule", "Other"]
PRIORITIES = ["Nice to have", "Important", "Must have"]
MAX_LENGTH = 3000


class FeedbackError(ValueError):
    pass


@dataclass
class FeedbackItem:
    timestamp: str
    name: str
    area: str
    kind: str
    priority: str
    message: str
    example: str = ""


def _safe_cell(text: str) -> str:
    """A spreadsheet treats a cell starting with = + - @ as a formula. Defuse that."""
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


class FeedbackStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.items: list = []
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8", newline="") as fh:
                names = {f.name for f in fields(FeedbackItem)}
                for row in csv.DictReader(fh):
                    if names <= set(row):
                        self.items.append(FeedbackItem(**{k: row[k] for k in names}))

    def add(self, name: str, area: str, kind: str, priority: str, message: str, example: str = "") -> FeedbackItem:
        message, example, name = message.strip(), example.strip(), name.strip()
        if not message:
            raise FeedbackError("Please write what you would like changed.")
        if len(message) > MAX_LENGTH or len(example) > MAX_LENGTH:
            raise FeedbackError(f"Please keep each box under {MAX_LENGTH} characters.")
        item = FeedbackItem(dt.datetime.now().isoformat(timespec="minutes").replace("T", " "), name[:80],
                            area, kind, priority, message, example)
        self.items.append(item)
        if self.path:
            new_file = not os.path.exists(self.path)
            with open(self.path, "a", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=[f.name for f in fields(FeedbackItem)])
                if new_file:
                    writer.writeheader()
                writer.writerow({k: _safe_cell(str(v)) for k, v in asdict(item).items()})
        return item

    def to_csv(self) -> str:
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=[f.name for f in fields(FeedbackItem)])
        writer.writeheader()
        for item in self.items:
            writer.writerow({k: _safe_cell(str(v)) for k, v in asdict(item).items()})
        return out.getvalue()

    def to_text(self) -> str:
        """A message that reads well on WhatsApp."""
        if not self.items:
            return "No suggestions written yet."
        order = {p: i for i, p in enumerate(reversed(PRIORITIES))}
        lines = [f"Algobot feedback ({len(self.items)} suggestion(s))", ""]
        for n, item in enumerate(sorted(self.items, key=lambda i: order.get(i.priority, 9)), start=1):
            who = f" ({item.name})" if item.name else ""
            lines.append(f"{n}. [{item.priority}] {item.area}: {item.kind}{who}")
            lines.append(f"   {item.message}")
            if item.example:
                lines.append(f"   Example: {item.example}")
        return "\n".join(lines)
