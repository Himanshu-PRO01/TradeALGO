#!/usr/bin/env python3
"""Static production-readiness audit for TradeALGO.

This is intentionally report-first: it does not modify application code and
does not pretend static analysis can verify runtime behavior. Use --gate to
turn selected blocking findings into a non-zero exit once the project is
ready to enforce them in CI.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
TEXT_EXTS = {".py", ".toml", ".txt", ".md", ".yml", ".yaml", ".json", ".ini", ".cfg"}

def files() -> Iterable[Path]:
    for p in ROOT.rglob("*"):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.parts):
            yield p

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""

def finding(severity: str, area: str, title: str, evidence: str, action: str) -> dict:
    return {"severity": severity, "area": area, "title": title, "evidence": evidence, "action": action}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default="production-audit.json")
    parser.add_argument("--markdown", dest="md_path", default="production-audit.md")
    parser.add_argument("--gate", action="store_true", help="fail on Critical/High findings")
    args = parser.parse_args()

    findings: list[dict] = []
    page_dir = ROOT / "pages"
    pages = sorted(page_dir.glob("*.py")) if page_dir.exists() else []

    required = ["requirements.txt", "README.md", "algobot/ui.py", "algobot/appstate.py"]
    missing = [p for p in required if not (ROOT / p).exists()]
    if missing:
        findings.append(finding("High", "Repository", "Required production files are missing",
                                ", ".join(missing), "Restore the required project files before deployment."))

    if not pages:
        findings.append(finding("Critical", "Navigation", "No Streamlit pages were discovered",
                                "pages/*.py is empty or missing", "Verify the application entrypoint and page directory."))

    # Every page should initialize the shared UI/security layer before rendering.
    for page in pages:
        src = read_text(page)
        if "ui.setup(" not in src:
            findings.append(finding(
                "High", "Authentication/UI", f"{page.relative_to(ROOT)} does not call ui.setup()",
                "No ui.setup( call found in the page source.",
                "Route the page through the shared UI/security initialization."
            ))

    # Validate page references embedded in Python source.
    known_pages = {p.as_posix() for p in pages}
    for path in files():
        if path.suffix != ".py":
            continue
        src = read_text(path)
        for ref in re.findall(r"""pages/[A-Za-z0-9_ .-]+\.py""", src):
            if ref not in known_pages:
                findings.append(finding(
                    "Medium", "Navigation", f"Broken page reference: {ref}",
                    f"Referenced by {path.relative_to(ROOT)}.",
                    "Update the reference or create the missing page."
                ))

    # CI coverage is a deployment-control requirement.
    workflows = list((ROOT / ".github" / "workflows").glob("*")) if (ROOT / ".github" / "workflows").exists() else []
    if not workflows:
        findings.append(finding(
            "High", "CI", "No GitHub Actions workflow is present",
            ".github/workflows contains no workflow files.",
            "Enable automated audit/test execution before production deployment."
        ))

    # Secret-like material in source. This is deliberately conservative: it reports
    # suspicious literals but does not claim every match is a real credential.
    secret_patterns = [
        r"(?i)(api[_-]?key|access[_-]?token|secret|password)\s*=\s*[\"'][^\"']{12,}[\"']",
        r"sk-[A-Za-z0-9_-]{20,}",
        r"(?i)bearer\s+[A-Za-z0-9._-]{20,}",
    ]
    for path in files():
        if path.suffix not in TEXT_EXTS or "tests" in path.parts:
            continue
        src = read_text(path)
        for pattern in secret_patterns:
            if re.search(pattern, src):
                findings.append(finding(
                    "High", "Secrets", f"Possible hard-coded secret in {path.relative_to(ROOT)}",
                    f"Matched a conservative credential-like pattern: {pattern}",
                    "Move real credentials to environment variables/Streamlit secrets and rotate any exposed credential."
                ))
                break

    # Network resilience checks: report integrations that exist without obvious
    # timeout/error handling nearby. Static checks are not runtime verification.
    network_files = {
        "algobot/live_data.py": "Yahoo/live market data",
        "algobot/openalgo_bridge.py": "OpenAlgo",
        "algobot/upstox_sandbox.py": "Upstox Sandbox",
        "algobot/ai_provider.py": "AI provider",
    }
    for rel, label in network_files.items():
        path = ROOT / rel
        if not path.exists():
            continue
        src = read_text(path)
        if "timeout" not in src.lower():
            findings.append(finding(
                "High", "Network", f"No explicit timeout marker found for {label}",
                rel,
                "Add a bounded timeout and user-visible recovery path, then verify it with tests."
            ))
        if not re.search(r"except\s+(Exception|TimeoutError|OSError|.*Error)", src):
            findings.append(finding(
                "Medium", "Network", f"No obvious exception handling found for {label}",
                rel,
                "Ensure provider failures become recoverable user-facing states."
            ))

    # UX resilience markers.
    all_source = "\n".join(read_text(p) for p in files() if p.suffix == ".py")
    if "st.spinner(" not in all_source and "st.status(" not in all_source:
        findings.append(finding("Medium", "Loading", "No loading/status primitive detected",
                                "No st.spinner/st.status usage found.", "Provide explicit feedback for slow operations."))

    if not re.search(r"retry|try again|refresh", all_source, re.I):
        findings.append(finding("Medium", "Recovery", "No retry/recovery marker detected",
                                "No retry/try-again/refresh text found in Python source.", "Provide recoverable failure states."))

    if not re.search(r"payment|stripe|razorpay|checkout|subscription", all_source, re.I):
        findings.append(finding("Info", "Payments", "No payment flow detected",
                                "No payment/subscription implementation was found.", "Treat as not applicable unless monetization is required."))

    # Accessibility and visual QA are hard to prove statically.
    test_text = "\n".join(read_text(p) for p in files() if "tests" in p.parts)
    if not re.search(r"accessib|axe|lighthouse|contrast|keyboard", test_text, re.I):
        findings.append(finding("Medium", "Accessibility", "No automated accessibility test markers found",
                                "Test sources contain no obvious accessibility/keyboard/contrast tooling.",
                                "Add an accessibility smoke suite before broad public launch."))

    if "Live Markets" in all_source and not (ROOT / "pages" / "Live_Markets.py").exists():
        findings.append(finding("Medium", "Navigation", "Text references a Live Markets page that is absent",
                                "Live Markets appears in source while pages/Live_Markets.py is absent.",
                                "Remove the dead reference or add the intended page."))

    # Global-state warning: useful for future multi-user deployments.
    appstate = read_text(ROOT / "algobot" / "appstate.py")
    if re.search(r"global|shared|kill_switch|rehearsal|alert", appstate, re.I) and "session_state" in appstate:
        findings.append(finding(
            "High", "State isolation", "Shared/global state exists alongside session state",
            "appstate.py contains both session-state and global/shared-state concepts.",
            "Before multi-user production, document and test tenant/user isolation for every persistent store."
        ))

    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in ["Critical", "High", "Medium", "Low", "Info"]}
    report = {
        "project": "TradeALGO",
        "mode": "static-source-audit",
        "note": "Static findings are evidence from repository contents; runtime behavior requires execution against a deployment.",
        "counts": counts,
        "findings": findings,
    }

    json_path = ROOT / args.json_path
    md_path = ROOT / args.md_path
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# TradeALGO Production Audit",
        "",
        "> Static source audit. This report does not claim to verify live runtime behavior.",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "|---|---:|",
    ]
    for sev in ["Critical", "High", "Medium", "Low", "Info"]:
        lines.append(f"| {sev} | {counts[sev]} |")
    lines += ["", "## Findings", ""]
    if not findings:
        lines.append("No static findings.")
    else:
        for i, f in enumerate(findings, 1):
            lines += [
                f"### {i}. [{f['severity']}] {f['title']}",
                f"**Area:** {f['area']}",
                f"**Evidence:** {f['evidence']}",
                f"**Action:** {f['action']}",
                "",
            ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Production audit written to {md_path} and {json_path}")
    print("Counts:", counts)
    if args.gate and (counts["Critical"] or counts["High"]):
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
