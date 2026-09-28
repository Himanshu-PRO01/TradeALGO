# TradeALGO: how to check the website works

**Goal:** find out within minutes, and before your users do, that the site is up, every page opens,
the tools give the right numbers, and nothing private is exposed.

No single check can prove that. So the strategy has five layers, cheapest first.

## The five layers

| # | Layer | What it proves | How | When |
|---|-------|----------------|-----|------|
| 1 | **Automated tests** (already in the project, over 300; the activity log last recorded 369 passing) | Each page loads without error; calculators give known answers; password screen and hosted mode work | `python -m pytest -q` | Before every push. GitHub already runs it. |
| 2 | **Site integrity tests** (new) | Every page is behind the password screen; no broken page links; no secrets or `.db` files in the project; every imported package is in `requirements.txt` | `python -m pytest -q tests/test_site_integrity.py` | Same as layer 1 (runs automatically with it) |
| 3 | **Live site check** (new) | The *deployed* site is up, wakes from sleep, accepts the password, and every page shows no Python error and no JavaScript crash | `python scripts/check_live_site.py URL --password PW` | After every deploy, and automatically every 6 hours |
| 4 | **10-minute manual walk-through** | Things a machine cannot judge: numbers match Upstox, the chart is readable, the phone layout is usable | Checklist below | After every deploy, and weekly |
| 5 | **Outside-world watch** | Failures that are not your bug (Yahoo, TradingView, OpenAlgo, Upstox) | Table below | When layer 3 or 4 shows a data problem |

**Why layers 1 and 2 are not enough:** they run each page in a simulator on your computer. They cannot see a
sleeping app, the wrong "main file" on Streamlit Cloud, a package missing on the server, a different Streamlit
version on the server, or the browser-only parts (TradingView chart, swipe menu, password autofill fix).
Layer 3 exists for exactly those.

## Routine

- **Before you push:** `python -m pytest -q`. All green (one expected "xfail", see Known issues).
- **After you deploy:** `python scripts/check_live_site.py URL --password PW --quick` (about 20 s), then the full run (a few minutes), then the manual checklist.
- **Automatically:** `.github/workflows/site-health.yml` runs layer 3 every 6 hours. If it fails, GitHub emails you.
- **Weekly:** manual checklist.

### One-time setup for the automatic check
1. `pip install playwright` and `python -m playwright install chromium` (only needed to run layer 3 on your own computer).
2. GitHub repo, *Settings, Secrets and variables, Actions*: add `SITE_URL` (your app link) and `SITE_PASSWORD`.
3. Actions tab, *Site health check*, *Run workflow*, to confirm it goes green once.

## 10-minute manual checklist

| Do this | Expect this |
|---------|-------------|
| Open the link in a private window | Password screen, nothing else usable |
| Type a wrong password | "That password is not right." |
| Type the right one | Front page and chart |
| Click **every** item in the menu once | No "page not found", no red traceback box |
| Position size, default numbers | 1 lot fits; warning about 10% of capital |
| Journal: `NIFTY 24500 CE`, entry 100, stop 85, then exit 112, charges 60 | "Net Rs 720.00" (a known answer from the test suite) |
| Backtest on sample data | Runs, shows the "random sample data" warning |
| Practice room: start, buy, run clock, sell, Finish and review | Review splits market move vs time decay, spread, charges |
| Live Trading page | Says orders are LOCKED; no button that places an order |
| Hosted mode: open the site in a second private window | The journal from window 1 is **not** visible |
| Phone (or narrow window) | Menu opens; no sideways scrolling |
| Language toggle | Page still works |

## Expected failures vs real failures

| You see | Meaning |
|---------|---------|
| Chart or price page says "No data returned" (market closed, Yahoo slow or rate-limited) | Expected. The page should show a friendly message, not a traceback. |
| TradingView "permission denied" on NIFTY1! or BANKNIFTY1! | Expected. Documented in the code. Equity symbols should load. |
| OpenAlgo or Upstox pages say "not connected" when you have not set keys | Expected. |
| First load after inactivity takes up to about 2 minutes | Expected on free hosting. The live check waits for it. |
| **A red Python traceback box on any page** | Real bug. |
| **A page that loads without asking for the password** | Real problem. Fix before sharing the link. |

## Known issues found while reading the code

1. **The front page tells visitors to open a "Live Markets" page that does not exist.** The `pages/` folder
   goes 8, 10, 13 (no 9 or 12) and the menu has no such entry. Either add the page (`live_data.py` is already
   there for it) or reword the two sentences in `Trading_Desk.py`. A test for this is marked `xfail`, so it
   reports quietly now and will show "XPASS" once fixed. Context: the activity log records a
   `pages/12_Market_Charts.py` (added 2026-09-25) that is not in this snapshot, and no entry says it was removed.
   The front page now has its own chart, so that page was probably folded in and the wording left behind. Check
   GitHub `main` before deciding which fix to make.
2. **Which file is the "main file"?** `HOSTING.md` says `Trading_Desk.py`, but a comment in `algobot/ui.py` says
   `dashboard.py` is the registered entry point and the menu's "Trading Desk" link points at it. Click that
   menu item on the live site. If it fails, change the Streamlit Cloud main file to `dashboard.py`.
3. **The menu is drawn before the password screen** (`ui.setup()` calls `_menu()` before `password_gate()`), so
   a visitor sees the page names and "HOSTED, LIVE OFF" without logging in. No data is exposed and every page is
   still gated (layer 2 checks that), but you may prefer to swap those two lines.
4. **`requirements.txt` says `streamlit>=1.40`, but the code uses `st.iframe`,** which I believe is a newer
   Streamlit feature (I could not confirm the version). Run `pip show streamlit` where your tests pass and
   raise the minimum to that version so a server cannot install one that is too old.

## What was and was not verified when this was written

- **Verified:** the new integrity tests were run against your real code (all 19 pages and the front page pass
  the password-gate check; two deliberately broken fake pages were caught). The live-site script was run in a
  real headless browser against a fake Streamlit-shaped site: correct, wrong and missing password; an app
  asleep behind a wake button inside an iframe; a Python error box; a JavaScript crash; an unreachable site.
- **Not verified:** your existing test suite (Streamlit could not be installed in the environment used to
  write this), and the live script against a real Streamlit Cloud app. Its element selectors are in one block
  at the top of `scripts/check_live_site.py`; if the first real run misbehaves, run it with `--headed` to watch.
