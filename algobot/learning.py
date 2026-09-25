"""Small, persistent learning memory for research experiments.

The learning layer records evidence and lessons. It never edits strategy rules,
risk limits, broker settings, or execution permissions.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Lesson:
    category: str
    message: str
    evidence: str
    occurrences: int = 1
    confidence: str = "low"
    action: str = "observe"
    first_seen: str = ""
    last_seen: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_path() -> str:
    return os.path.join("data", "learning_memory.json")


def load_memory(path: str | None = None) -> dict[str, Any]:
    path = path or _default_path()
    if not os.path.exists(path):
        return {"lessons": []}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("lessons"), list):
            return {"lessons": []}
        return data
    except (OSError, json.JSONDecodeError):
        return {"lessons": []}


def save_memory(memory: dict[str, Any], path: str | None = None) -> None:
    path = path or _default_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as fh:
        json.dump(memory, fh, indent=2, sort_keys=True)
    os.replace(temp, path)


def record_lesson(
    category: str,
    message: str,
    evidence: str,
    action: str = "observe",
    path: str | None = None,
) -> Lesson:
    """Record repeated evidence without changing any trading configuration."""
    memory = load_memory(path)
    now = _now()
    for item in memory["lessons"]:
        if item.get("category") == category and item.get("message") == message:
            item["occurrences"] = int(item.get("occurrences", 0)) + 1
            item["evidence"] = evidence
            item["last_seen"] = now
            count = item["occurrences"]
            item["confidence"] = "high" if count >= 4 else "medium" if count >= 2 else "low"
            item["action"] = action
            save_memory(memory, path)
            return Lesson(**{k: item.get(k, "") for k in Lesson.__dataclass_fields__})
    lesson = Lesson(
        category=category,
        message=message,
        evidence=evidence,
        action=action,
        first_seen=now,
        last_seen=now,
    )
    memory["lessons"].append(asdict(lesson))
    save_memory(memory, path)
    return lesson


def summarize_auto_test(rows: list[dict], path: str | None = None) -> list[Lesson]:
    """Learn only from repeated, observable failures in Auto Tester results."""
    if not rows:
        return []
    lessons: list[Lesson] = []
    failed_risk = sum(not bool(r.get("risk_rules_ok", False)) for r in rows)
    if failed_risk:
        lessons.append(
            record_lesson(
                "risk",
                "Some tested candidates violated risk/integrity rules.",
                f"{failed_risk} of {len(rows)} candidates had a risk/integrity failure.",
                action="exclude from research shortlist",
                path=path,
            )
        )
    poor_drawdown = sum(float(r.get("worst_drawdown_Rs", 0)) < -10 for r in rows)
    if poor_drawdown >= 2:
        lessons.append(
            record_lesson(
                "drawdown",
                "Repeated candidates showed material drawdown in fake-market stress tests.",
                f"{poor_drawdown} of {len(rows)} candidates crossed the drawdown warning threshold.",
                action="require stronger robustness checks",
                path=path,
            )
        )
    return lessons


def research_shortlist(rows: list[dict]) -> list[dict]:
    """Return a transparent research shortlist; not a profit guarantee."""
    valid = [r for r in rows if bool(r.get("risk_rules_ok"))]
    return sorted(
        valid,
        key=lambda r: (
            float(r.get("avg_result_Rs", float("-inf"))),
            float(r.get("profitable_worlds_%", 0)),
            float(r.get("worst_drawdown_Rs", float("-inf"))),
        ),
        reverse=True,
    )


def learning_summary(path: str | None = None) -> list[dict]:
    return load_memory(path)["lessons"]
