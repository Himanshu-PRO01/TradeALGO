# Ai Provider Get Module

> 20 nodes

## Key Concepts

- **test_ai_provider.py** (29 connections) — `tests/test_ai_provider.py`
- **get_provider()** (22 connections) — `algobot/ai_provider.py`
- **GroqProvider** (12 connections) — `algobot/ai_provider.py`
- **_find_gemini_key()** (12 connections) — `algobot/ai_provider.py`
- **get_ai_status()** (8 connections) — `algobot/ai_provider.py`
- **test_dual_provider_fallback_when_both_configured()** (8 connections) — `tests/test_ai_provider.py`
- **test_cross_key_collision_protection()** (3 connections) — `tests/test_ai_provider.py`
- **test_gemini_is_preferred_when_configured()** (3 connections) — `tests/test_ai_provider.py`
- **test_grok_is_preferred_when_configured()** (3 connections) — `tests/test_ai_provider.py`
- **test_groq_is_preferred_when_configured()** (3 connections) — `tests/test_ai_provider.py`
- **test_groq_uses_default_model()** (3 connections) — `tests/test_ai_provider.py`
- **gemini_fail()** (2 connections) — `tests/test_ai_provider.py`
- **test_find_gemini_key_discovers_from_secret_yml()** (2 connections) — `tests/test_ai_provider.py`
- **test_gemini_key_discovered_from_toml_and_raw_regex()** (2 connections) — `tests/test_ai_provider.py`
- **test_get_ai_status_and_aliases()** (2 connections) — `tests/test_ai_provider.py`
- **.__init__()** (1 connections) — `algobot/ai_provider.py`
- **groq_ok()** (1 connections) — `tests/test_ai_provider.py`
- **Any** (1 connections)
- **Inspects credentials and returns active AI engine connection state.** (1 connections) — `algobot/ai_provider.py`
- **Groq's OpenAI-compatible Chat Completions provider.** (1 connections) — `algobot/ai_provider.py`

## Relationships

- [Ai Provider Match Module](Ai_Provider_Match_Module.md) (22 shared connections)
- [Ai Provider Generate Module](Ai_Provider_Generate_Module.md) (17 shared connections)
- [Ai Provider Generate Module (2)](Ai_Provider_Generate_Module_2.md) (7 shared connections)
- [Backtesting & Historical Execution (3)](Backtesting_&_Historical_Execution_3.md) (2 shared connections)
- [Strategy Rule Engine](Strategy_Rule_Engine.md) (1 shared connections)
- [Market Data Validation & Feed](Market_Data_Validation_&_Feed.md) (1 shared connections)
- [Conftest Synthetic User Module](Conftest_Synthetic_User_Module.md) (1 shared connections)

## Source Files

- `algobot/ai_provider.py`
- `tests/test_ai_provider.py`

## Audit Trail

- EXTRACTED: 75 (88%)
- INFERRED: 10 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*