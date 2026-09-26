"""Tiny, dependency-free DOM fixups for things Streamlit's widgets don't expose
directly. Kept in its own module (no imports from ui.py or appstate.py) so it
can be called from either without creating an import cycle.
"""
from __future__ import annotations


def fix_password_autocomplete() -> None:
    """Chrome/Lighthouse flags "Incorrect use of autocomplete attribute" on any
    <input type="password"> with no autocomplete attribute -- and
    st.text_input(type="password") doesn't expose that attribute, so this sets
    it directly on the rendered DOM node.

    A field whose label/placeholder mentions "token" gets autocomplete="off"
    (it's a pasted API token, not a login password -- we don't want the
    browser offering a saved site password here). Anything else typed as a
    password gets autocomplete="current-password" (a real login field).

    Call this once, right after rendering the password field(s) on a page.
    Harmless no-op if the browser can't reach the parent document.
    """
    import streamlit as st

    st.iframe(
        """
        <script>
        (function () {
          try {
            const doc = window.parent.document;
            doc.querySelectorAll('input[type="password"]').forEach((el) => {
              if (el.getAttribute('autocomplete')) return;
              const label = (el.getAttribute('aria-label') || el.placeholder || '').toLowerCase();
              el.setAttribute('autocomplete', label.includes('token') ? 'off' : 'current-password');
            });
          } catch (e) { /* cross-origin sandbox: nothing we can do, and nothing broken */ }
        })();
        </script>
        """,
        height=0,
    )
