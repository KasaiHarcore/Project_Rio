# Security Triage Backlog

## pip-audit findings (updated 2026-04-28)

`pip-audit -l` baseline drained from **50 → 25 vulns** (-50%) on 2026-04-28
via `uv lock --upgrade-package` for 12 patch-friendly deps. Audit step in
`.github/workflows/ci.yml` is still `continue-on-error: true` because the
residual cluster needs coordinated work, not point-bumps.

### Triage workflow per finding

1. Read advisory (CVE / GHSA link)
2. Decide: **upgrade** (cheapest), **replace**, or **accept-with-rationale**
3. If accepted, add the ID to the per-job `--ignore-vuln <ID>` arguments in
   `.github/workflows/ci.yml` with a one-line comment naming the exception's
   expiry condition
4. If upgraded, run `uv lock --upgrade-package <pkg>` and retest

### Cleared on 2026-04-28 (12 packages, 25 advisories)

```
aiohttp           3.13.3 → 3.13.5    (10 CVEs)
authlib           1.6.9  → 1.7.0     (1 GHSA)
cryptography      46.0.5 → 47.0.0    (2 CVEs, major bump — verified clean)
nltk              3.9.3  → 3.9.4     (3 advisories)
orjson            3.11.5 → 3.11.8    (1 CVE)
protobuf          6.33.4 → 6.33.6    (1 CVE)
pygments          2.19.2 → 2.20.0    (1 CVE)
pyjwt             2.11.0 → 2.12.1    (1 CVE)
pytest            9.0.2  → 9.0.3     (1 CVE)
python-dotenv     1.2.1  → 1.2.2     (1 CVE)
python-multipart  0.0.21 → 0.0.27    (2 CVEs)
requests          2.32.5 → 2.33.1    (1 CVE)
```

Verification: `uv run pytest -m "not e2e"` → 249/249 green after bumps.

### Residual findings (25 across 8 packages)

```
langchain-core           1.2.7   CVE-2026-26013      1.2.11
langchain-core           1.2.7   CVE-2026-40087      0.3.84,1.2.28
langchain-openai         1.1.7   GHSA-r7w7-9xr2-qq2r 1.1.14
langchain-text-splitters 1.1.0   GHSA-fv5p-p927-qmxr 1.1.2
langgraph                1.0.6   CVE-2026-28277      1.0.10
langsmith                0.6.3   GHSA-rr7j-v2q5-chgv 0.7.31
pillow                   11.3.0  CVE-2026-25990      12.1.1
pillow                   11.3.0  CVE-2026-40192      12.2.0
pypdf                    6.6.0   (15 advisories, fix range 6.6.2 → 6.10.2)
transformers             4.57.3  CVE-2026-1839       5.0.0rc3
```

### Why each residual is deferred

- **langchain cluster (4 pkgs, 6 advisories)** — Tried bumping
  langchain-core 1.2→1.3 + langgraph 1.0.6→1.0.10 in tandem on 2026-04-28;
  uv pulled `langgraph-prebuilt 1.0.12` which imports `ExecutionInfo` not
  exported by `langgraph 1.0.10` → 15 pytest collection errors. Rolled back.
  Need explicit version-skew check across langchain-* + langgraph + the
  langgraph-prebuilt transitive before retrying. Coordinated bump, not a
  point upgrade.
- **pillow 11.3 → 12.x** — Major version bump. Touches all OCR + image
  pipelines (`infrastructure/ocr/`, screenshot handling in
  `os_control/browser_controller.py` + `os_control/gui_controller.py`).
  Needs an integration-test pass before flipping.
- **pypdf 6.6 → 6.10.2** — 4-minor jump, 15 CVEs. PDF ingestion is in
  `infrastructure/rag/ingestion.py` + chunker; needs RAG smoke test.
- **transformers 4.57 → 5.0.0rc3** — Only fix is a release candidate.
  Wait for 5.0.0 final.

### Path to strict pip-audit gate

Once the four residual clusters above are resolved (or each given an
`--ignore-vuln <ID>` flag with explicit rationale), flip
`continue-on-error: false` on the audit step in `ci.yml`.

## bandit findings (current state, 2026-04-28)

`bandit -r src -c pyproject.toml -ll -ii` → **0 Medium, 0 High** (CI gate green).

Run metrics on full sweep:
- Severity: 0 Undefined / 42 Low / 1 Medium / 0 High
- Confidence: 0 Undefined / 1 Low / 5 Medium / 37 High
- Code scanned: 34,120 lines

Suppressions:
- B306 mktemp findings (browser_controller.py, gui_controller.py) → fixed via `mkstemp`
- B602 shell=True findings (pty_session.py:134, 216) → annotated `# nosec B602`
  (PTY-style command runner is a deliberate user-driven shell; risk-tier
  policy enforces gating upstream)
- 42 Low + 1 Medium-with-Low-confidence findings remain unsuppressed for
  transparency; CI gates only on Medium+/High-confidence.

## Other CI gate state (2026-04-28)

- **pytest** — STRICT. 249 passed / 2 deselected (e2e). New `--cov-fail-under=37`
  blocks coverage regressions below current floor. Global rule is 80%; raise
  the floor as coverage grows.
- **ruff lint + format** — INFORMATIONAL. 6248 lint findings, 213 unformatted
  files in legacy backlog. Flip per-rule once cleaned.
- **bandit** — STRICT (Medium+/High-confidence only).
