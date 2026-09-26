import streamlit as st

from algobot.dom_fixups import fix_password_autocomplete


def test_fix_password_autocomplete_runs_without_error(monkeypatch):
    """Can't execute real JS/DOM in pytest, but this confirms the helper
    builds valid HTML/JS and calls st.iframe without raising -- the kind of
    import/syntax regression that would otherwise only show up live in a
    browser. st.iframe replaced the deprecated components.v1.html (see
    dom_fixups.py); st.iframe also rejects height=0, so this pins height=1."""
    calls = []
    monkeypatch.setattr(st, "iframe", lambda markup, height=0: calls.append((markup, height)))

    fix_password_autocomplete()

    assert len(calls) == 1
    markup, height = calls[0]
    assert "autocomplete" in markup
    assert 'input[type="password"]' in markup
    assert height == 1
