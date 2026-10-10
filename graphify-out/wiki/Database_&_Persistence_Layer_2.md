# Database & Persistence Layer (2)

> 15 nodes

## Key Concepts

- **feedback.py** (13 connections) — `algobot/feedback.py`
- **FeedbackStore** (8 connections) — `algobot/feedback.py`
- **FeedbackError** (6 connections) — `algobot/feedback.py`
- **.add()** (4 connections) — `algobot/feedback.py`
- **_safe_cell()** (4 connections) — `algobot/feedback.py`
- **FeedbackItem** (3 connections) — `algobot/feedback.py`
- **test_feedback_is_saved_shared_and_defused_for_spreadsheets()** (3 connections) — `tests/test_ui_hosting.py`
- **.__init__()** (2 connections) — `algobot/feedback.py`
- **.to_csv()** (2 connections) — `algobot/feedback.py`
- **.to_text()** (2 connections) — `algobot/feedback.py`
- **csv** (2 connections)
- **ValueError** (1 connections)
- **Suggestions from the brother (or anyone) about what to change. Feedback is…** (1 connections) — `algobot/feedback.py`
- **A spreadsheet treats a cell starting with = + - @ as a formula. Defuse that.** (1 connections) — `algobot/feedback.py`
- **A message that reads well on WhatsApp.** (1 connections) — `algobot/feedback.py`

## Relationships

- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (4 shared connections)
- [Streamlit UI Components (3)](Streamlit_UI_Components_3.md) (4 shared connections)
- [Backtesting & Historical Execution](Backtesting_&_Historical_Execution.md) (1 shared connections)
- [Execution Live Policy Module](Execution_Live_Policy_Module.md) (1 shared connections)
- [Market Data Validation & Feed (4)](Market_Data_Validation_&_Feed_4.md) (1 shared connections)
- [Database & Persistence Layer](Database_&_Persistence_Layer.md) (1 shared connections)
- [Paper Trading Daemon Module](Paper_Trading_Daemon_Module.md) (1 shared connections)

## Source Files

- `algobot/feedback.py`
- `tests/test_ui_hosting.py`

## Audit Trail

- EXTRACTED: 32 (97%)
- INFERRED: 1 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*