import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # project root, so `import algobot` works
sys.path.insert(0, HERE)                    # so tests can `import helpers`


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path, monkeypatch):
    """No test may touch the real journal or experiment log."""
    monkeypatch.setenv("ALGOBOT_EXPERIMENTS", str(tmp_path / "experiments.db"))
    monkeypatch.setenv("ALGOBOT_JOURNAL", str(tmp_path / "journal.db"))
    monkeypatch.setenv("ALGOBOT_NO_ENV", "1")     # never read a real .env file
