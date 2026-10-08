# TradeALGO

> **Deterministic algorithmic trading research, backtesting, and safety audit platform for Indian equities and derivatives (NSE/BSE).**

TradeALGO is a local and hosted trading-desk platform built to turn trading ideas into verifiable, cost-honest algorithmic strategies without risking real capital. It includes a deterministic backtesting engine, multimodal AI strategy ingestion, adversarial synthetic agent swarm audits, and automated paper-trading ledgers.

---

## ⚡ Key Capabilities

### 1. 📊 Deterministic Backtester & Cost Modeling
- **Zero Look-Ahead Guarantee:** Signal at bar close, fill at next bar open. Enforced by look-ahead test suites.
- **Realistic Indian Market Costs:** STT, GST (18%), exchange turnover fees, SEBI turnover fees, stamp duty, broker caps (e.g. ₹20/order), and configurable slippage (bps).
- **Tested Strategy Presets:**
  - **Conservative 10k Pullback:** Calibrated for ₹10,000 retail capital, RSI(5) dip-buy with 50 EMA filter, ₹300 daily stop-loss limit (`configs/conservative_10k.yaml`).
  - **Stock Pullback:** High-expectancy mean-reversion on high-liquidity bluechips (`configs/stock_pullback.yaml`).
  - **Bank Nifty Momentum:** 9/21 EMA trend following with RSI momentum filter (`configs/banknifty_momentum.yaml`).
  - **Nifty Floor Pivot Bounce:** S1/R1 floor reversal on Nifty 50 (`configs/nifty_pivot_bounce.yaml`).
  - **New Era Strategy 1.0:** Stateful formation breakout engine.

### 2. 📸 AI Photo-to-Strategy Vision Reader
- Upload screenshots of TradingView charts, Pine Script snippets, or photos of handwritten rules (`PNG`, `JPG`, `WEBP`).
- Multimodal AI (Gemini 2.5 Flash, OpenAI GPT-4o-mini, or Claude) transcribes visual text into strict, validated TradeALGO YAML rules (`indicators`, `entry_long`, `exit_long`, etc.).
- One-click transfer directly into the Backtest engine.

### 3. 🐟 MiroFish Multi-Agent Swarm Strategy Audit
- Stress-tests strategies against 6 independent synthetic regimes (*trend, chop, mean reversion, volatile, shocks, noise*).
- 8 specialized synthetic agent jobs critique and debate every rule:
  - 🛡️ **Risk Manager Job:** Evaluates drawdown depth and capital preservation limits.
  - ⚔️ **Adversarial Attacker Job:** Actively probes shock and extreme-volatility failure modes.
  - 📊 **Optimizer & Stats Job:** Verifies profit factor consistency and trade frequency.
  - 🌊 **Momentum Specialist Job:** Tests trend continuation persistence.
  - 🔄 **Contrarian Auditor Job:** Audits false breakouts and mean-reversion stability.
  - 🚸 **Beginner Auditor Job:** Audits fee drag and small-account survivability.
  - ⚡ **Rapid Execution Job:** Checks latency sensitivity and trade churn.
  - 🛠️ **Power User Job:** Stress-tests position sizing and session constraints.

### 4. 📝 90-Day Paper Trading Daemon & Daily Audit Ledger
- Autonomous paper-trading daemon (`run_90day_logger.py`, `algobot/paper_trading_daemon.py`).
- Automated GitHub Actions workflow (`deploy/workflows/paper-trading-audit.yml`) executing daily after NSE market close (15:45 IST) and recording immutable audit ledgers (`audit_logs/90_day_audit_ledger.csv`).

### 5. 🛡️ Safety & Execution Boundary (OpenAlgo Integration)
- Connects to [OpenAlgo](https://openalgo.in) over local HTTP API for quotes and sandbox rehearsal.
- Live execution is **locked by default** (`TRADEALGO_EXECUTION_ENABLED=false`). No automated real-money orders without manual gate confirmation.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ (tested up to 3.14)
- Git

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Himanshu-PRO01/TradeALGO.git
cd TradeALGO

# 2. Create virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Launch the Trading Desk Web App

```bash
streamlit run Trading_Desk.py
```
Or run `run_windows.bat` on Windows.

---

## 🧪 Testing

Run the full automated test suite (500+ tests):

```bash
python -m pytest tests/test_dashboard.py tests/test_vision_and_mirofish_backtest.py
```

---

## 📁 Repository Structure

```text
├── algobot/                  # Core engine package
│   ├── ai_provider.py        # LLM & Vision provider (Gemini, OpenAI, Anthropic, Groq)
│   ├── engine.py             # Bar-by-bar backtest simulation engine
│   ├── risk.py               # Risk rules & daily loss kill switches
│   ├── costs.py              # Brokerage, STT, GST, SEBI fee calculator
│   ├── mirofish_sim.py       # MiroFish synthetic agent swarm simulation
│   ├── mirofish_qa.py        # Adversarial regime stress testing
│   ├── openalgo_bridge.py    # OpenAlgo execution boundary
│   └── paper_trading_daemon.py # Automated paper-trading runner
├── configs/                  # Strategy YAML definitions (conservative_10k.yaml, etc.)
├── pages/                    # Streamlit Trading Desk multi-page interface
│   ├── 5_Backtest.py         # Backtest runner, Vision reader, and MiroFish swarm
│   ├── 10_Strategy_Builder.py# Visual rule builder & library
│   └── ...
├── audit_logs/               # Immutable paper-trading ledgers
├── tests/                    # Automated pytest test suites
└── Trading_Desk.py           # Streamlit application entry point
```

---

## ⚠️ Disclaimer

TradeALGO is for research, education, and paper testing. No backtest guarantees future results. Never trade capital you cannot afford to lose.
