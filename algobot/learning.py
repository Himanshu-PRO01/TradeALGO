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


def analyze_and_learn_from_trades(trades: Any, metrics: dict | None = None, path: str | None = None) -> list[Lesson]:
    """Inspect trade logs and metrics, diagnose mistakes, and record actionable lessons."""
    if trades is None:
        return []
    import pandas as pd
    df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame(trades)
    if df.empty:
        return []

    lessons: list[Lesson] = []

    # 1. Diagnose loss clustering by time-of-day
    if "entry_time" in df.columns and "net_pnl" in df.columns:
        times = pd.to_datetime(df["entry_time"])
        morning_losses = df[(times.dt.hour == 9) & (times.dt.minute < 45) & (df["net_pnl"] < 0)]
        if len(morning_losses) >= 1:
            lessons.append(record_lesson(
                "timing",
                "Opening bell volatility whipsaw detected before 09:45.",
                f"{len(morning_losses)} trade(s) triggered stop loss in first 30 mins of session.",
                action="restrict trading_start to 09:45 or later",
                path=path,
            ))

    # 2. Diagnose fee erosion (trades where gross PnL was positive or near zero but charges turned it negative)
    if "gross_pnl" in df.columns and "net_pnl" in df.columns:
        fee_drag_trades = df[(df["gross_pnl"] >= 0) & (df["net_pnl"] < 0)]
        if len(fee_drag_trades) >= 1:
            lessons.append(record_lesson(
                "friction",
                "Transaction charges exceeded gross edge on small scalp moves.",
                f"{len(fee_drag_trades)} winning/breakeven gross trade(s) became net losses after brokerage and STT.",
                action="enforce higher min target ratio and cap max daily trades",
                path=path,
            ))

    # 3. Diagnose consecutive losses
    if metrics and metrics.get("max_loss_streak", 0) >= 2:
        lessons.append(record_lesson(
            "drawdown",
            "Consecutive stop-outs observed during adverse regime.",
            f"Encountered {metrics['max_loss_streak']} consecutive losses.",
            action="enforce cooldown period after consecutive stops",
            path=path,
        ))

    # 4. Stop-loss execution frequency
    if "exit_reason" in df.columns and len(df) >= 3:
        stop_outs = df[df["exit_reason"] == "stop"]
        if len(stop_outs) / len(df) > 0.40:
            lessons.append(record_lesson(
                "stop_placement",
                "High stop-out rate (>40%) indicates entry trigger is too sensitive.",
                f"{len(stop_outs)} of {len(df)} trades hit full stop loss.",
                action="tighten entry conditions with stronger confirmation or wider stop with smaller size",
                path=path,
            ))

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


def record_experiment(strategy_id, version_label, hypothesis, parameters, dataset_period, result, metrics, ai_explanation="", train_period="", test_period="", path=None):
    if not str(hypothesis).strip(): raise ValueError("An experiment needs a hypothesis: what were you trying to find out?")
    memory=load_memory(path); experiments=memory.setdefault("experiments",[])
    next_id=1+max((int(e.get("id",0)) for e in experiments),default=0)
    experiment={"id":next_id,"timestamp":_now(),"strategy_id":str(strategy_id),"version_label":str(version_label),
        "hypothesis":str(hypothesis).strip(),"parameters":json.loads(json.dumps(parameters,default=str)),
        "dataset_period":str(dataset_period),"train_period":str(train_period),"test_period":str(test_period),
        "result":str(result),"metrics":json.loads(json.dumps(metrics,default=str)),"ai_explanation":str(ai_explanation)}
    experiments.append(experiment); save_memory(memory,path); return experiment

def list_experiments(path=None, strategy_id=None):
    experiments=load_memory(path).get("experiments",[])
    if not isinstance(experiments,list): return []
    return [e for e in experiments if strategy_id is None or e.get("strategy_id")==strategy_id]

def experiments_for_ai(path=None, strategy_id=None, limit=20):
    out=[]
    for e in list_experiments(path,strategy_id)[-max(1,int(limit)):]:
        out.append({"id":e.get("id"),"strategy_id":e.get("strategy_id"),"version_label":e.get("version_label"),
            "hypothesis":str(e.get("hypothesis",""))[:300],"parameters":e.get("parameters"),
            "train_period":e.get("train_period"),"test_period":e.get("test_period"),"result":str(e.get("result",""))[:300]})
    return out
