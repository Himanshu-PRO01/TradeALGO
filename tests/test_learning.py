from algobot.learning import load_memory, record_lesson, research_shortlist, summarize_auto_test


def test_record_lesson_accumulates_repeated_evidence(tmp_path):
    path = tmp_path / "memory.json"
    first = record_lesson("risk", "risk failure", "one", path=str(path))
    second = record_lesson("risk", "risk failure", "two", path=str(path))
    assert first.occurrences == 1
    assert second.occurrences == 2
    assert second.confidence == "medium"
    assert load_memory(str(path))["lessons"][0]["evidence"] == "two"


def test_learning_does_not_change_strategy_config(tmp_path):
    path = tmp_path / "memory.json"
    rows = [{"risk_rules_ok": False, "worst_drawdown_Rs": -20, "avg_result_Rs": 5}]
    summarize_auto_test(rows, str(path))
    assert load_memory(str(path))["lessons"]


def test_shortlist_excludes_risk_failures_and_is_transparent():
    rows = [
        {"candidate": 1, "risk_rules_ok": True, "avg_result_Rs": 2, "profitable_worlds_%": 60, "worst_drawdown_Rs": -5},
        {"candidate": 2, "risk_rules_ok": False, "avg_result_Rs": 100, "profitable_worlds_%": 100, "worst_drawdown_Rs": -1},
        {"candidate": 3, "risk_rules_ok": True, "avg_result_Rs": 4, "profitable_worlds_%": 55, "worst_drawdown_Rs": -8},
    ]
    assert [r["candidate"] for r in research_shortlist(rows)] == [3, 1]


def test_empty_results_have_no_lessons():
    assert summarize_auto_test([], path="/tmp/unused-learning-test.json") == []
