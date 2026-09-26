from algobot.dom_fixups import fix_password_autocomplete


def test_fix_password_autocomplete_runs_without_error(monkeypatch):
    """Verify the current Streamlit iframe-based DOM fixup is invoked."""
    calls = []

    import streamlit as st

    def fake_iframe(markup, height=0):
        calls.append((markup, height))

    monkeypatch.setattr(st, "iframe", fake_iframe)

    fix_password_autocomplete()

    assert len(calls) == 1
    markup, height = calls[0]
    assert "autocomplete" in markup
    assert 'input[type="password"]' in markup
    assert height == 1
