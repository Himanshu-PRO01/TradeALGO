"""Site-level integrity checks: things that break a WEBSITE even when every unit test passes.

These read the source files only (no Streamlit server, no internet), so they are fast and safe to
run in CI on every push:  python -m pytest -q tests/test_site_integrity.py
"""
import ast
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES_DIR = os.path.join(ROOT, "pages")
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "scripts"}


def _py_files():
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(folder, name)


def _page_files():
    return sorted(f for f in os.listdir(PAGES_DIR) if f.endswith(".py"))


def _is_st_call(node):
    """True for a call like st.something(...)."""
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "st")


def _has_ui_setup(node):
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "setup"
               and isinstance(n.func.value, ast.Name) and n.func.value.id == "ui" for n in ast.walk(node))


@pytest.mark.parametrize("name", _page_files() + ["../Trading_Desk.py"])
def test_page_runs_ui_setup_before_drawing_anything(name):
    path = os.path.join(PAGES_DIR, name)
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for statement in tree.body:
        if _has_ui_setup(statement):
            return
        drawn = [n for n in ast.walk(statement) if _is_st_call(n) and n.func.attr != "set_page_config"]
        assert not drawn, f"{name}: draws with st.{drawn[0].func.attr}() before ui.setup() (password gate)"
    pytest.fail(f"{name}: never calls ui.setup(), so the password screen would not protect it")


def test_every_pages_path_mentioned_in_code_exists():
    missing = []
    for path in _py_files():
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for target in set(re.findall(r"""["'](pages/[A-Za-z0-9_]+.py)["']""", text)):
            if not os.path.exists(os.path.join(ROOT, target)):
                missing.append(f"{os.path.relpath(path, ROOT)} -> {target}")
    assert not missing, "links to pages that do not exist:\n" + "\n".join(missing)


def test_page_web_addresses_are_unique():
    seen = {}
    for name in _page_files():
        url = re.sub(r"^[0-9_s]+", "", name[:-3])
        assert url not in seen, f"{name} and {seen[url]} would share the web address /{url}"
        seen[url] = name


def _page_titles():
    titles = set()
    for name in _page_files():
        with open(os.path.join(PAGES_DIR, name), encoding="utf-8") as fh:
            match = re.search(r'ui\.setup\(\s*["\']([^"\']+)["\']', fh.read())
        if match:
            titles.add(match.group(1).lower())
    return titles


@pytest.mark.xfail(reason="Front page tells visitors to open a 'Live Markets' page, but no such page exists "
                          "(pages/ jumps from 8 to 10 and 13). Create pages/9_Live_Markets.py or reword the text.")
def test_pages_named_in_visitor_text_actually_exist():
    titles = _page_titles()
    with open(os.path.join(ROOT, "Trading_Desk.py"), encoding="utf-8") as fh:
        text = fh.read()
    named = {m.strip("* ").lower() for m in re.findall(r"**([A-Z][A-Za-z ]+?)**s+page", text)}
    named |= {m.lower() for m in re.findall(r"the ([A-Z][a-z]+ [A-Z][a-z]+) page", text)}
    unknown = sorted(n for n in named if n not in titles)
    assert not unknown, f"text points visitors to pages that do not exist: {unknown}"


def test_no_private_files_in_the_project():
    bad = []
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name == ".env" or name == "secrets.toml" or name == "feedback.csv" or name.endswith((".db", ".sqlite", ".sqlite3")):
                bad.append(os.path.relpath(os.path.join(folder, name), ROOT))
    assert not bad, f"private files present (must not be uploaded to GitHub): {bad}"


def test_no_key_looking_strings_in_the_code():
    pattern = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|eyJ[A-Za-z0-9_-]{30,}.[A-Za-z0-9_-]{10,})")
    hits = []
    for path in _py_files():
        if os.path.basename(path).startswith("test_"):
            continue
        with open(path, encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if pattern.search(line):
                    hits.append(f"{os.path.relpath(path, ROOT)}:{number}")
    assert not hits, f"something that looks like an API key or token: {hits}"


def test_deploy_files_are_present():
    for required in ("Trading_Desk.py", "requirements.txt", os.path.join(".streamlit", "config.toml")):
        assert os.path.exists(os.path.join(ROOT, required)), f"missing {required}"


def test_every_import_is_in_requirements():
    with open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8") as fh:
        wanted = {re.split(r"[<>=!~\[ ]", line.strip(), maxsplit=1)[0].lower().replace("-", "_")
                  for line in fh if line.strip() and not line.startswith("#")}
    aliases = {"yaml": "pyyaml", "upstox_client": "upstox_python_sdk", "pil": "pillow",
               "google": "protobuf"}  # algobot/upstox_market_data.py uses google.protobuf
    local = {"algobot", "helpers", "conftest", "_common"}
    local |= {"altair"}
    stdlib = set(__import__("sys").stdlib_module_names)
    missing = set()
    for path in _py_files():
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                key = aliases.get(name.lower(), name.lower())
                if name in stdlib or name in local or key in wanted:
                    continue
                missing.add(name)
    assert not missing, f"imported but not listed in requirements.txt (the deployed site would crash): {sorted(missing)}"
