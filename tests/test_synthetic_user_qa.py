"""Synthetic-user website smoke tests.

These are deterministic fake users, not real accounts. They exercise safe
research/practice pages only and never enable broker execution.
"""
import os

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PERSONAS = (
    ("new_researcher", "5_Backtest.py"),
    ("risk_averse", "6_Reality_check.py"),
    ("paper_trader", "16_Paper_Trading.py"),
    ("sandbox_user", "17_Sandbox_Rehearsal.py"),
    ("market_observer", "23_Live_Markets.py"),
)


@pytest.mark.parametrize("persona,page_name", PERSONAS)
def test_synthetic_user_can_open_safe_workflow(persona, page_name):
    at = AppTest.from_file(
        os.path.join(ROOT, "pages", page_name),
        default_timeout=90,
    )
    at.run()
    assert not at.exception, f"{persona} crashed {page_name}: {at.exception}"
