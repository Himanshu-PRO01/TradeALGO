"""Manual QA: drive the real Backtest page, then the Reality check page, with the realistic strategy.

Run from anywhere:   python qa/run_page_qa.py
Not part of the pytest suite (file name is not test_*.py / *_test.py)."""
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import yaml

from _common import RAW, ROOT, load_prices
import algobot.data as data
from algobot.runner import run_from_dict
from streamlit.testing.v1 import AppTest


def main() -> int:
    os.chdir(ROOT)
    real = load_prices()
    data.generate_sample_data = lambda days=60, seed=42, **kw: real.iloc[: int(days) * 75].copy()

    at = AppTest.from_file(os.path.join(ROOT, "pages", "5_Backtest.py"), default_timeout=180)
    at.run()
    at.radio(key="strategy_kind").set_value("Write my own rules (advanced)").run()
    at.text_area(key="rules_text").set_value(yaml.safe_dump(RAW["strategy"]["params"], sort_keys=False)).run()
    at.slider(key="sample_days").set_value(90).run()
    at.number_input(key="capital").set_value(500000)
    at.number_input(key="quantity").set_value(75)
    at.checkbox(key="allow_short").set_value(True)
    at.number_input(key="stop_pct").set_value(0.35)
    at.number_input(key="target_pct").set_value(0.7)
    at.number_input(key="max_loss").set_value(6000)
    at.number_input(key="max_trades").set_value(3)
    at.number_input(key="max_position").set_value(2500000)
    at.text_input(key="t_start").set_value("09:30")
    at.run()
    at.checkbox(key="confirm").check().run()
    at.button(key="btn_run").click().run()
    assert not at.exception, at.exception

    mets = {m.label: m.value for m in at.metric}
    ref = run_from_dict(RAW, real).metrics
    page_net = float(mets["Net profit / loss (Rs)"].replace(",", ""))
    print("page trades", mets["Trades"], "| engine trades", ref["trades"])
    print("page net", page_net, "| engine net", round(ref["net_pnl"]))
    ok = abs(page_net - round(ref["net_pnl"])) <= 1 and int(mets["Trades"]) == ref["trades"]

    rc = AppTest.from_file(os.path.join(ROOT, "pages", "6_Reality_check.py"), default_timeout=300)
    rc.session_state["last_raw"] = at.session_state["last_raw"]
    rc.session_state["last_prices"] = at.session_state["last_prices"]
    rc.run()
    rc.button(key="au_run").click().run()
    assert not rc.exception, rc.exception
    print("Reality check verdict:", [e.value for e in list(rc.error) + list(rc.success) + list(rc.warning)][:1])
    print("PAGE MATCHES ENGINE" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
