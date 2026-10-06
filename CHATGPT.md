# TradeALGO — AI Agent Handoff / ChatGPT.md

## Purpose

This file is the current handoff for Antigravity/Ponytail and other coding agents working on the TradeALGO repository.

**Repository:** `Himanshu-PRO01/TradeALGO`  
**Primary branch:** `main`  
**App:** Streamlit Indian-market trading research platform  
**Deployment:** `https://tradingalgov2.streamlit.app`

---

## 1. Current Product Direction

TradeALGO is an **India-first trading research and paper-trading application**.

Important safety rule:

> **Never enable, trigger, or test real/live trading.**

Live/OpenAlgo execution code exists as a guarded boundary, but live execution must remain disabled. All testing should use synthetic data, historical/research data, backtests, paper trading, or Streamlit AppTest.

Indian-market assumptions currently used:
- NSE equity
- IST / Asia-Kolkata
- Regular equity session: 09:15–15:30
- INR
- Equity lot size default: 1
- India-specific transaction-cost model exists in `algobot/india_market.py`

---

## 2. Major Work Already Completed

### Production audit
Production-readiness audit was completed and merged.

- Python 3.10/3.11/3.12 CI
- duplicate workflow removed
- README updated for Python 3.10+
- 453 tests passed during the audit
- Main audit commit: `773a76427df65edd815d84c49be9cc8971041803`

### Guarded live-execution boundary
A guarded OpenAlgo live-execution implementation exists.

- `algobot/live_execution.py`
- `tests/test_live_execution.py`
- Live execution is **disabled by default**
- Explicit confirmation / kill-switch / execution-policy checks exist
- Never enable it for QA

Relevant implementation commit:
`01b0a7e7315a0fd9b0ce6ab5383e411d807c09dd`

### Synthetic agent simulation
- `algobot/agent_research.py`
- `algobot/synthetic_swarm.py`
- `pages/27_Agent_Simulation_Lab.py`
- `pages/28_Swarm_Simulation_Lab.py`

The app contains synthetic strategy research agents and swarm simulations.

### MiroFish-style research system

The repository contains an **independent MiroFish-inspired implementation**. It is not a copy of MiroFish.

Core files:
- `algobot/mirofish_sim.py`
- `algobot/mirofish_qa.py`
- `tests/test_mirofish_sim.py`
- `tests/test_mirofish_qa.py`
- `pages/28_Swarm_Simulation_Lab.py`

Architecture:

```
synthetic market/news reality
        ↓
agent personas
        ↓
memory / lightweight knowledge graph
        ↓
agent-to-agent interaction / debate
        ↓
consensus + failure modes
        ↓
research report
```

The implementation is safety-bounded and research-only.

### MiroFish QA

`algobot/mirofish_qa.py` contains two important systems:

1. **Strategy evidence**
   - independent synthetic regimes:
     - trend
     - chop
     - mean reversion
     - volatile
     - shocks
     - noise
   - deterministic seeds
   - backtest evidence
   - profit factor / P&L / drawdown
   - adversarial failure detection
   - consensus and lightweight graph statistics

2. **Synthetic website swarm**
   - uses Streamlit `AppTest`
   - synthetic website personas:
     - beginner
     - risk manager
     - momentum trader
     - contrarian
     - optimizer
     - impatient
     - power user
     - adversarial tester
   - only allowlisted research pages are tested
   - safe action words are allowlisted
   - live/order/broker/OpenAlgo/buy/sell/credentials/API-key actions are blocked
   - captures exceptions, visible errors, repeated failures and action completion

Safe page allowlist currently contains:
- `5_Backtest.py`
- `6_Reality_check.py`
- `7_Test_lab.py`
- `15_Strategy_Scanner.py`
- `27_Agent_Simulation_Lab.py`
- `28_Swarm_Simulation_Lab.py`

### MiroFish tests

`tests/test_mirofish_qa.py` currently verifies:
- deterministic 6-round / 2-day strategy evidence
- non-empty graph evidence
- a non-empty verdict
- website swarm allowlist excludes execution pages

The deterministic MiroFish QA tests have passed CI.

---

## 3. Important Reality: Strategy Is NOT Proven Profitable

Do not describe TradeALGO's strategy as profitable without fresh evidence.

The current default backtest previously produced approximately:
- 231 trades
- net P&L around **-₹3,429**
- win rate around **20%**
- max drawdown around **-₹3,444**

Reality Check previously returned:
- net P&L: approximately **-₹3,429**
- 1.5× cost stress: approximately **-₹5,063**
- 2× cost stress: approximately **-₹6,700**
- random-entry comparison: failed
- later-period performance: negative
- verdict: **NOT READY**

Therefore MiroFish is a research/attack framework, not proof of profitability.

---

## 4. Current Trading Desk UI

The product is being standardized around the **Trading Desk home page**.

Recent UI work:
- desktop hover-expandable sidebar
- sidebar labels fixed after CSS regression
- custom sidebar toggle button removed
- native Streamlit sidebar collapse controls hidden/locked
- sidebar overlay behavior fixed so expanded sidebar reserves workspace width
- all pages are being given a shared dark Trading Desk visual system

Current shared styling is in:
- `algobot/ui.py`

The latest shared skin makes research pages visually consistent with Trading Desk:
- dark background
- common cards/panels
- common buttons
- dark inputs/selects
- dark tables
- common tabs/alerts
- wide desktop layout
- shared page styling

Do not redesign individual pages into unrelated visual styles. Preserve the Trading Desk design language.

---

## 5. Latest Relevant Commits

Recent main-branch work includes:

- `263b3322f714481e068499fbbb4a21bb192c4c1b`
  - `fix: lock native sidebar controls`

- `845051d89b7dacca0c3d0415de5369df471a3665`
  - `fix: prevent sidebar from overlaying workspace`

- `8266408c6dba8c5effc5a5b1d1112746a9b0c8b5`
  - `feat: unify all pages with Trading Desk dark skin`

Earlier MiroFish-related commits:
- `0eaabdf607b67db0352e3d16ae67e5a2c8fee5c6`
- `f27c3d8f759baaf7744953871595de5835fa9eb7`
- `ebc8df8064318d74ed3b786ed00cfa2e2b7d2e46`

---

## 6. Live Browser Test Status

The deployed Streamlit app has been reachable and visually inspected.

However:

**The full external browser MiroFish run has NOT been confirmed successful.**

Attempts to remotely interact with the deployed Streamlit app timed out while trying to:
1. open Swarm Simulation Lab
2. run the Full MiroFish adversarial run
3. run the synthetic website swarm

This timeout must **not** be interpreted as a MiroFish failure.

The recommended next step is local execution through:
- Streamlit `AppTest`
- pytest
- Antigravity/Ponytail browser testing

Use the external browser only as a small deployment smoke test.

---

## 7. Recommended MiroFish QA Procedure

Run the repository tests first:

```bash
pytest -q
```

Then specifically run:

```bash
pytest -q tests/test_mirofish_qa.py tests/test_mirofish_sim.py
```

Then execute the Streamlit website swarm locally with conservative settings:
- agents: 2
- pages per agent: 2
- action rounds: 1

Then execute strategy evidence:
- rounds: 6
- days: 2
- deterministic seed

Inspect:
- exceptions
- visible Streamlit errors
- repeated failures
- action completion rate
- safety violations
- strategy P&L
- profit factor
- drawdown
- regime failures
- final verdict

Do not click any live trading/execution controls.

---

## 8. Key Engineering Files

Useful starting points:

```
algobot/
  engine.py
  strategy.py
  indicators.py
  levels.py
  india_market.py
  profitability_engine.py
  agent_research.py
  synthetic_swarm.py
  mirofish_sim.py
  mirofish_qa.py
  live_execution.py
  ui.py

pages/
  5_Backtest.py
  6_Reality_check.py
  7_Test_lab.py
  15_Strategy_Scanner.py
  27_Agent_Simulation_Lab.py
  28_Swarm_Simulation_Lab.py

tests/
  test_mirofish_qa.py
  test_mirofish_sim.py
  test_india_market.py
  test_live_execution.py
```

---

## 9. Existing Strategy Configuration

`configs/demo_rules.yaml` currently defines the demo EMA/RSI strategy:

- EMA fast: 9
- EMA slow: 21
- RSI: 14
- long entry: EMA crossover + RSI > 50
- short entry: EMA crossunder + RSI < 50
- quantity: 10
- shorting allowed
- stop loss: 0.5%
- target: 1.0%

Risk controls include:
- max daily loss: ₹2,000
- max trades/day: 6
- max position value: ₹50,000
- trading start: 09:20
- no new entries after: 14:45
- square-off: 15:15

---

## 10. Rules for Future Agents

1. **Do not enable live trading.**
2. Do not use broker credentials or API keys during QA.
3. Do not place real orders.
4. Do not claim a profitable strategy without real out-of-sample and cost-robust evidence.
5. Do not replace real test results with guessed/fabricated results.
6. Run tests after meaningful code changes.
7. Prefer local Streamlit AppTest over fragile remote browser interaction for exhaustive QA.
8. Keep the Trading Desk visual system consistent across pages.
9. Preserve the hover sidebar behavior and prevent sidebar/workspace overlap.
10. When fixing a bug, inspect the actual implementation rather than guessing.
11. If a remote browser times out, report it as a browser/test infrastructure timeout unless local evidence proves an application failure.
12. Keep research/paper trading clearly separated from live execution.

---

## 11. Current Handoff Goal

The next agent should:

1. Run the MiroFish QA locally.
2. Run the complete test suite.
3. Investigate and fix any actual MiroFish/AppTest failures.
4. Verify the shared Trading Desk UI across pages.
5. Verify sidebar hover/overlay behavior.
6. Run a small deployed-site smoke test only after local tests pass.
7. Report exact results and commit fixes to `main`.

This document is an engineering handoff, not a statement that every item above is currently passing. Always verify the current repository state before making claims.
