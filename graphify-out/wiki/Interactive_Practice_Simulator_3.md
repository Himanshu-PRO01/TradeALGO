# Interactive Practice Simulator (3)

> 20 nodes

## Key Concepts

- **test_practice_room_live_feed.py** (18 connections) — `tests/test_practice_room_live_feed.py`
- **_start_live()** (6 connections) — `tests/test_practice_room_live_feed.py`
- **test_no_ticks_yet_shows_a_connecting_message_and_still_resolves()** (6 connections) — `tests/test_practice_room_live_feed.py`
- **test_live_tick_price_wins_over_a_stale_official_candle()** (5 connections) — `tests/test_practice_room_live_feed.py`
- **_bars()** (4 connections) — `tests/test_practice_room_live_feed.py`
- **fake_hub()** (4 connections) — `tests/test_practice_room_live_feed.py`
- **test_trading_works_before_the_official_ohlc_backfill_has_landed()** (4 connections) — `tests/test_practice_room_live_feed.py`
- **test_starting_a_live_session_streams_the_hubs_price_not_a_stale_one()** (3 connections) — `tests/test_practice_room_live_feed.py`
- **test_the_autorefresh_loop_does_not_hang_the_test_suite()** (3 connections) — `tests/test_practice_room_live_feed.py`
- **st_session_source()** (2 connections) — `tests/test_practice_room_live_feed.py`
- **latest()** (1 connections) — `tests/test_practice_room_live_feed.py`
- **snapshot()** (1 connections) — `tests/test_practice_room_live_feed.py`
- **status()** (1 connections) — `tests/test_practice_room_live_feed.py`
- **test_no_token_falls_back_to_yahoo_and_offers_no_upstox_choice()** (1 connections) — `tests/test_practice_room_live_feed.py`
- **test_upstox_is_offered_and_selected_by_default_when_a_token_is_configured()** (1 connections) — `tests/test_practice_room_live_feed.py`
- **fixture** (1 connections)
- **Practice Room's Live mode can stream real ticks from the shared Upstox market-…** (1 connections) — `tests/test_practice_room_live_feed.py`
- **Right after Start, a live tick can arrive before the one-time official-OHLC…** (1 connections) — `tests/test_practice_room_live_feed.py`
- **The single most important regression check here: an earlier version of this…** (1 connections) — `tests/test_practice_room_live_feed.py`
- **algobot.live_market.LiveMarketHub.snapshot() returns only the official, REST-…** (1 connections) — `tests/test_practice_room_live_feed.py`

## Relationships

- [Interactive Practice Simulator (5)](Interactive_Practice_Simulator_5.md) (4 shared connections)
- [Conftest Synthetic User Module](Conftest_Synthetic_User_Module.md) (2 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (1 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (1 shared connections)
- [Market Live Livemarkethub Module](Market_Live_Livemarkethub_Module.md) (1 shared connections)

## Source Files

- `tests/test_practice_room_live_feed.py`

## Audit Trail

- EXTRACTED: 37 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*