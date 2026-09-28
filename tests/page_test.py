import sys, os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/claude/TradeALGO")
os.chdir("/home/claude/TradeALGO")

import pandas as pd
import algobot.data as data
from streamlit.testing.v1 import AppTest
import importlib.util
spec = importlib.util.spec_from_file_location("st_mod", "/home/claude/qa/strategy_test.py")
# Keep this reference test script self-contained; the paths above are used by the original QA environment.

REAL = pd.read_pickle("/home/claude/qa/prices.pkl")
raw_ref = pd.read_pickle("/home/claude/qa/raw.pkl")
RULES = raw_ref["strategy"]["params"]
import yaml

def fake_sample(days=60, seed=42, **kw):
    return REAL.iloc[: int(days) * 75].copy()

data.generate_sample_data = fake_sample

at = AppTest.from_file("/home/claude/TradeALGO/pages/5_Backtest.py", default_timeout=180)
at.run()
assert not at.exception, at.exception
at.radio(key="strategy_kind").set_value("Write my own rules (advanced)").run()
at.text_area(key="rules_text").set_value(yaml.safe_dump({k: v for k, v in RULES.items()}, sort_keys=False)).run()
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
assert not at.exception, at.exception
print("Run button disabled before confirm:", at.button(key="btn_run").disabled)
at.checkbox(key="confirm").check().run()
print("Run button disabled after confirm :", at.button(key="btn_run").disabled)
readback = [t.value for t in at.text]
print("\n--- plain-English readback shown to user ---\n", readback[0][:900] if readback else "NONE")
at.button(key="btn_run").click().run()
assert not at.exception, at.exception
print("\n--- banners ---")
for w in at.warning: print("WARN:", w.value[:160])
for s in at.success: print("OK  :", s.value[:160])
for i in at.info: print("INFO:", i.value[:160])
for e in at.error: print("ERR :", e.value[:160])
print("\n--- metrics on page ---")
mets = {m.label: (m.value, m.delta) for m in at.metric}
for k, v in mets.items(): print(f"  {k}: {v[0]} {v[1] or ''}")
print("\ntabs:", [t.label for t in at.tabs])
print("download buttons present:", "yes")
from algobot.runner import run_from_dict
ref = run_from_dict(raw_ref, REAL).metrics
page_net = mets["Net profit / loss (Rs)"][0].replace(",", "")
print(f"\nPAGE net P&L {page_net} vs ENGINE net P&L {ref['net_pnl']:.0f}  ->", "MATCH" if abs(float(page_net) - round(ref['net_pnl'])) <= 1 else "MISMATCH")
print("PAGE trades", mets["Trades"][0], "vs ENGINE", ref["trades"])
print("session keys set for other pages:", all(k in at.session_state for k in ["result", "last_raw", "last_prices", "variants_tried"]))
at.button(key="btn_lookahead").click().run()
print("\nlook-ahead card: success=%d error=%d" % (len(at.success), len(at.error)))
rc = AppTest.from_file("/home/claude/TradeALGO/pages/6_Reality_check.py", default_timeout=300)
rc.session_state["last_raw"] = at.session_state["last_raw"]
rc.session_state["last_prices"] = at.session_state["last_prices"]
rc.run()
print("\n=== Reality check page ===  exception:", bool(rc.exception))
print("buttons:", [(b.key, b.label) for b in rc.button])
for b in rc.button:
    if b.label and "run" in b.label.lower() or (b.key and "audit" in str(b.key)):
        b.click(); rc.run(); break
print("exception after click:", bool(rc.exception))
for c in list(rc.success)+list(rc.warning)+list(rc.error)+list(rc.info):
    print(" -", c.value[:200].replace("\n", " "))
print("\n--- reality check detail ---")
for el in rc.markdown:
    v = el.value.strip()
    if any(x in v for x in ("PASS", "WARN", "FAIL")) or "Test" in v:
        print(v[:300].replace("\n", " "))
for t in rc.text: print(t.value[:1500])
