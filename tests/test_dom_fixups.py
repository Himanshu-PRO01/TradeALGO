from algobot.dom_fixups import fix_password_autocomplete


def test_fix_password_autocomplete_runs_without_error(monkeypatch):
    """Can't execute real JS/DOM in pytest, but this confirms the helper
    builds valid HTML/JS and calls components.html without raising -- the
    kind of import/syntax regression that would otherwise only show up
    live in a browser."""
    calls = []

    class FakeComponents:
        def html(self, markup, height=0):
            calls.append((markup, height))

    import algobot.dom_fixups as mod
    monkeypatch.setattr(mod, "__name__", mod.__name__)  # no-op, keeps module identity clear

    import sys
    fake_module = FakeComponents()
    sys.modules["streamlit.components.v1"] = fake_module  # type: ignore
    try:
        fix_password_autocomplete()
    finally:
        del sys.modules["streamlit.components.v1"]

    assert len(calls) == 1
    markup, height = calls[0]
    assert "autocomplete" in markup
    assert "input[type=\"password\"]" in markup
    assert height == 0
