import io
import os
import yaml
import pytest

from streamlit.testing.v1 import AppTest

from algobot.ai_provider import AIProvider, read_strategy_image
from algobot.config import validate_config
from algobot.mirofish_qa import build_strategy_evidence
from algobot.mirofish_sim import run_mirofish

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "pages", "5_Backtest.py")


def test_10k_pullback_config_exists_and_is_valid():
    cfg_path = os.path.join(ROOT, "configs", "conservative_10k.yaml")
    assert os.path.exists(cfg_path), "configs/conservative_10k.yaml must exist"
    with open(cfg_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    assert raw["name"] == "conservative_10k"
    assert raw["capital"] == 10000
    assert raw["risk"]["max_daily_loss"] == 300
    cfg = validate_config(raw)
    assert cfg["capital"] == 10000


def test_10k_pullback_can_be_selected_and_run_in_backtest():
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    assert not at.exception
    at.radio(key="strategy_kind").set_value("Conservative 10k Pullback (₹10,000 Capital — Tested)").run()
    assert not at.exception
    assert at.number_input(key="capital").value == 10000
    assert at.number_input(key="quantity").value == 25
    assert not at.button(key="btn_run").disabled
    at.button(key="btn_run").click().run()
    assert not at.exception


def test_configs_yaml_option_loads_repository_configs():
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    assert not at.exception
    at.radio(key="strategy_mode").set_value("📁 Load from configs/ YAML").run()
    assert not at.exception
    assert at.selectbox(key="bt_yaml_select") is not None
    at.button(key="btn_run").click().run()
    assert not at.exception


def test_vision_upload_mode_can_be_selected_in_backtest():
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    assert not at.exception
    at.radio(key="strategy_mode").set_value("📸 AI Photo-to-Strategy (Upload Image)").run()
    assert not at.exception
    assert at.file_uploader(key="bt_photo_file") is not None



def test_read_strategy_image_parses_rules_cleanly(monkeypatch):
    class FakeVisionProvider(AIProvider):
        name = "fake_vision"

        def generate_vision(self, system_prompt, user_prompt, image_bytes, mime_type="image/png"):
            return """```yaml
indicators:
  - {name: rsi5, type: rsi, period: 5}
  - {name: e50, type: ema, period: 50}
entry_long: "rsi5 < 25 and close > e50"
exit_long: "rsi5 > 65"
entry_short: "rsi5 > 75 and close < e50"
exit_short: "rsi5 < 35"
```
Detected RSI-5 pullback rule with 50 EMA regime filter."""

    monkeypatch.setattr("algobot.ai_provider.get_provider", lambda **kwargs: FakeVisionProvider())

    res = read_strategy_image(b"fake_image_bytes", mime_type="image/png")
    assert "rsi5 < 25" in res["yaml"]
    assert "RSI-5 pullback" in res["explanation"]
    parsed = yaml.safe_load(res["yaml"])
    assert isinstance(parsed["indicators"], list)
    assert parsed["indicators"][0]["name"] == "rsi5"


def test_mirofish_agent_swarm_audit_runs_on_strategy_config():
    cfg_path = os.path.join(ROOT, "configs", "conservative_10k.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = validate_config(raw)
    ev = build_strategy_evidence(cfg, rounds=6, days=4, seed=123)
    assert len(ev.evidence) == 6
    assert ev.verdict in ("PROMISING — REQUIRES REAL OOS AND COST ROBUSTNESS",
                          "UNSTABLE — KEEP RESEARCHING",
                          "FAILED — ADVERSARIAL SWARM FOUND WEAKNESS")

    rep, cohort, msgs, g, events = run_mirofish(agents=8, ticks=12, seed=456)
    assert len(cohort) == 8
    roles = {a.persona.name for a in cohort}
    assert "risk_manager" in roles
    assert "adversarial" in roles
    assert "optimizer" in roles
