# TradeALGO Production Deployment Audit

This document is the repeatable release gate for future TradeALGO deployments.

## Audit modes

### 1. Static audit

Run from the repository root:

```bash
python scripts/production_audit.py
```

Outputs:

- `production-audit.md`
- `production-audit.json`

The audit is intentionally report-first. It records evidence from source/configuration and does not claim to prove runtime behavior.

### 2. Automated test audit

Run:

```bash
pytest -q
```

The repository already contains unit, integration, page, UI-hosting, strategy, backtest, sandbox, and data-provider tests. Streamlit's AppTest framework is suitable for headless page interaction tests and can be executed in CI. See the official Streamlit AppTest documentation for the supported multipage testing model.

### 3. Deployment smoke audit

After a deployment, manually verify:

- landing page loads without exception
- authentication gate behaves as configured
- every sidebar/workflow destination opens
- page Back/Next controls work
- small-screen layout is usable
- external-data failures show a recoverable message
- slow AI/data operations show visible progress
- sandbox actions remain sandbox-only
- kill switch state is visible and understandable
- no credentials appear in rendered errors
- browser refresh does not create an unsafe duplicate action

## Release checklist

### Security and identity

- [ ] Authentication requirement is explicitly documented.
- [ ] Multi-user deployments have per-user identity and state isolation.
- [ ] Session expiry/logout requirements are defined.
- [ ] Secrets are stored only in environment variables or platform secrets.
- [ ] API tokens are never rendered in full.
- [ ] Production logs do not contain credentials.

### Network and external services

- [ ] Every external request has a bounded timeout.
- [ ] Network failures have a user-visible recovery path.
- [ ] Retry behavior is bounded and does not duplicate financial/sandbox actions.
- [ ] Provider outages do not leave buttons looking permanently active.
- [ ] Slow operations expose progress/pending state.
- [ ] Service degradation is distinguishable from an empty/no-results state.

### Trading/safety

- [ ] Live execution remains explicitly locked until intentionally enabled.
- [ ] Sandbox and paper-trading boundaries are tested.
- [ ] Destructive/reset actions have appropriate confirmation.
- [ ] Duplicate order submission is prevented.
- [ ] Kill switch behavior is tested.
- [ ] Position/risk limits are tested.
- [ ] Look-ahead and backtest integrity tests pass.

### UX

- [ ] Every major page has loading, empty, error, and recovery states where applicable.
- [ ] Forms validate before expensive/network actions.
- [ ] Error text explains what the user can do next.
- [ ] Navigation references only existing pages.
- [ ] Mobile layout is checked at narrow widths.
- [ ] Touch targets and text remain usable when browser text is enlarged.
- [ ] Keyboard navigation and focus visibility are checked.
- [ ] Color is not the only carrier of status.
- [ ] Dark-theme contrast is checked.

### Data and persistence

- [ ] Session-only versus persistent data is documented.
- [ ] Global/shared stores are intentionally scoped.
- [ ] Reset/delete operations have clear consequences.
- [ ] Database files have appropriate locking/backup behavior.
- [ ] Migration/versioning behavior is defined before schema changes.

### Release engineering

- [ ] Static production audit passes required threshold.
- [ ] Full test suite passes.
- [ ] CI runs on pull requests and main-branch pushes.
- [ ] A deployment smoke test has been completed.
- [ ] The deployed commit matches the audited commit.
- [ ] Rollback procedure is known and tested.
- [ ] Production configuration/secrets are verified separately from source.

## Severity policy

- **Critical:** security/data-loss/order-execution blocker. Do not deploy.
- **High:** production reliability, state isolation, or security risk. Resolve before broad production release.
- **Medium:** meaningful UX/reliability/accessibility gap. Resolve before broad public launch or document an explicit exception.
- **Low:** polish or non-blocking enhancement.
- **Info:** evidence/context that is not itself a defect.

## Evidence rule

An audit finding must include:

1. exact file or configuration area,
2. concrete source evidence,
3. the affected user/operational flow,
4. severity,
5. remediation requirement.

Do not mark a runtime behavior as verified from static code alone.

## Future deployment gate

The static audit supports a strict mode:

```bash
python scripts/production_audit.py --gate
```

Strict mode exits non-zero for Critical or High findings. It should be enabled as the final deployment gate after the currently documented High findings are remediated.

## What this audit does not replace

Static checks cannot replace:

- real browser/mobile testing,
- provider outage testing,
- authentication/session testing against the deployed environment,
- accessibility tooling,
- performance/load testing,
- payment testing if payments are introduced,
- final production smoke testing.
