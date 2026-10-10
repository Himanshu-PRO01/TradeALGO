# Streamlit UI Components (3)

> 17 nodes

## Key Concepts

- **test_ui_hosting.py** (50 connections) — `tests/test_ui_hosting.py`
- **app()** (9 connections) — `tests/test_ui_hosting.py`
- **journal_rows_from_csv()** (7 connections) — `algobot/journal.py`
- **journal_to_csv()** (6 connections) — `algobot/journal.py`
- **test_bad_journal_files_are_refused_with_a_reason()** (4 connections) — `tests/test_ui_hosting.py`
- **test_journal_csv_round_trip_keeps_everything_including_awkward_text()** (4 connections) — `tests/test_ui_hosting.py`
- **test_local_mode_still_saves_to_the_journal_file()** (3 connections) — `tests/test_ui_hosting.py`
- **test_every_page_in_the_menu_loads_with_no_exception()** (2 connections) — `tests/test_ui_hosting.py`
- **test_feedback_page_saves_and_offers_the_text_to_send()** (2 connections) — `tests/test_ui_hosting.py`
- **test_front_page_loads_with_links_and_the_safety_strip()** (2 connections) — `tests/test_ui_hosting.py`
- **test_hosted_mode_keeps_each_visitors_journal_in_memory_only()** (2 connections) — `tests/test_ui_hosting.py`
- **test_password_screen_blocks_every_page_until_the_right_password()** (2 connections) — `tests/test_ui_hosting.py`
- **test_the_old_entry_point_still_starts_the_same_page()** (2 connections) — `tests/test_ui_hosting.py`
- **test_too_many_wrong_passwords_lock_the_session()** (2 connections) — `tests/test_ui_hosting.py`
- **test_launchers_and_the_start_here_guide_ship_with_the_project()** (1 connections) — `tests/test_ui_hosting.py`
- **Every trade as CSV text, for backup or to send to someone.** (1 connections) — `algobot/journal.py`
- **Parse CSV text made by journal_to_csv into rows for Journal.import_rows.** (1 connections) — `algobot/journal.py`

## Relationships

- [Trade Journal & Reporting](Trade_Journal_&_Reporting.md) (10 shared connections)
- [Streamlit UI Components (2)](Streamlit_UI_Components_2.md) (9 shared connections)
- [Database & Persistence Layer (2)](Database_&_Persistence_Layer_2.md) (4 shared connections)
- [Options Pricing & Greeks](Options_Pricing_&_Greeks.md) (4 shared connections)
- [Trade Journal & Reporting (3)](Trade_Journal_&_Reporting_3.md) (3 shared connections)
- [Strategy Lab & Research](Strategy_Lab_&_Research.md) (3 shared connections)
- [Streamlit UI Components](Streamlit_UI_Components.md) (3 shared connections)
- [Interactive Practice Simulator](Interactive_Practice_Simulator.md) (2 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (2 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (2 shared connections)
- [Conftest Synthetic User Module](Conftest_Synthetic_User_Module.md) (2 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (1 shared connections)

## Source Files

- `algobot/journal.py`
- `tests/test_ui_hosting.py`

## Audit Trail

- EXTRACTED: 72 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*