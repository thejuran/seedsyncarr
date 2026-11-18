---
phase: 127
slug: readme-accuracy
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-11-18
---

# Phase 127 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None for prose. Mechanical python3/grep/awk/git checks (see 127-RESEARCH.md "Validation Architecture"). Existing CI (pytest, `ruff check src/python/`, Angular, e2e) unaffected |
| **Config file** | none |
| **Quick run command** | The current task's group: `python3 .planning/phases/127-readme-accuracy/127-check.py structure` (Task 1), `... claims` (Task 2), `... all` (Task 3). Replaces the verification block in 127-RESEARCH.md |
| **Full suite command** | `python3 .planning/phases/127-readme-accuracy/127-check.py all && ruff check src/python/ && if git diff --quiet 33c50bfc -- .planning/phases/127-readme-accuracy/127-check.py; then echo "check script: unchanged (path i)"; else echo "check script: CHANGED (path ii)"; fi` (groups: structure, claims, security, scope, selftest; ruff expected clean, unchanged; the last part reports check-script integrity) |
| **Check-script integrity** | Baseline commit `33c50bfc`. Path (i): the script is unchanged since the baseline. Path (ii): it was changed to fix a detector that rejected accurate text; the full diff is reproduced and justified hunk by hunk in the SUMMARY, no reject fixture is removed, and `selftest` (part of `all`) passes. The verifier confirms path (ii) by reading the SUMMARY against `git diff 33c50bfc -- .planning/phases/127-readme-accuracy/127-check.py` |
| **What the script proves** | Mostly presence checks (a required term appears in the right section) plus a narrow set of contradiction detectors pinned by its `selftest` fixtures. A green run does not prove the prose is true; the Manual-Only Verifications below are mandatory |
| **Baseline** | One baseline for the security and scope groups: commit `091f51f2` (pre-phase README.md and SECURITY.md). For a re-run after the phase PR merged and unrelated work landed on main, set `BASE_REF` to the parent of the phase's first commit |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run that task's group only (Task 1 `structure`; Task 2 `claims` then `structure`; Task 3 `all`). Do not run `all` after Tasks 1 or 2: later groups stay red until their task is done, by design
- **After every plan wave:** Run the full command (single plan, single wave: this is the Task 3 gate)
- **Before `/bm:verify-work`:** Full command green and every row of Manual-Only Verifications read and recorded in the SUMMARY claims ledger
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 127-01-T1 | 01 | 1 | DOC-01, DOC-04 | T-127-02 | Guides linked; Quick Start states port exposure and that `api_token` does not protect the UI | mechanical | `python3 .planning/phases/127-readme-accuracy/127-check.py structure` | yes | ⬜ pending |
| 127-01-T2 | 01 | 1 | DOC-02, DOC-03 | T-127-01, T-127-03, T-127-04 | Defaults and cleanup conditions stated as the code behaves; no webhook-secret recommendation | mechanical | `python3 .planning/phases/127-readme-accuracy/127-check.py claims` | yes | ⬜ pending |
| 127-01-T3 | 01 | 1 | DOC-02, DOC-03 (D-08) | T-127-03, T-127-06 | SECURITY.md changed only in the two approved spots (intro sentence and webhook bullet); scope limited to README.md and SECURITY.md; check script unmodified since `33c50bfc` (path i) or changed with a justified diff and passing selftest (path ii) | mechanical | `python3 .planning/phases/127-readme-accuracy/127-check.py all && ruff check src/python/ && if git diff --quiet 33c50bfc -- .planning/phases/127-readme-accuracy/127-check.py; then echo "check script: unchanged (path i)"; else echo "check script: CHANGED (path ii)"; fi` | yes | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No remaining unconditional claims in README | DOC-03 / D-04 | Judgment of prose | Read the full README against the claims table in 127-RESEARCH.md (Finding 4); confirm each row is qualified, removed or kept as accurate; one ledger row each |
| Every stated security default is true as written | DOC-02 / D-06, D-07 | The script checks that terms appear together, not that the sentence is true | For each README Security list item, read the sentence and the code: `api_token` empty means API authentication off; `webhook_secret` empty means verification skipped; `webhook_require_secret` is `False`; `[Encryption] enabled` is `False` and secrets are plaintext (`src/python/seedsyncarr.py` `_create_default_config`, `src/python/common/config.py` backfills) |
| `api_token` scope is stated correctly | DOC-02, DOC-04 | Relationship between terms | Confirm the README says `api_token` protects the API, does NOT protect the UI (the UI contains the token), and does NOT authenticate the webhook endpoints (`src/python/web/web_app.py` auth exemptions and meta-tag injection) |
| Always-on controls have their true scope | DOC-02 / D-05 | Scope wording | Confirm the Security controls bullet names rate limiting on the webhook, POST config-set, test-connection, bulk-command and status endpoints only, the IP guard only when testing a connection, and lists no opt-in item |
| Quick Start exposure note is true as written | DOC-04 / D-09, D-10 | Meaning of the sentences | Confirm it says port 8800 is published on all host interfaces, names an authenticating reverse proxy plus restricted network access for untrusted networks, and does not suggest the token or `allowed_hostname` is network protection |
| Signing conditions are precise and consistent in both files | DOC-02/03, revised D-03, widened D-08 | Prose meaning | Read README Security and the SECURITY.md webhook bullet side by side: a configured secret rejects a missing or invalid signature (401); `webhook_require_secret = true` with no secret rejects every call (503); Sonarr and Radarr do not sign; the incompatibility is scoped to direct, unsigned Sonarr/Radarr webhooks; neither file recommends, suggests or instructs turning on `webhook_secret` or `webhook_require_secret` |
| Cleanup wording matches the controller | DOC-03 / D-02 | Sequence and conditions | Confirm How It Works and the Usage Examples cleanup example say: off by default; only releases SeedSyncarr downloaded; deletion is attempted after the delay and is subject to completion and import safeguards (may be deferred or given up), not automatic on timer expiry; dry-run logs instead of deleting; only the local copy is deleted and the remote copy is untouched (`src/python/controller/controller.py` `__execute_auto_delete`, `docs/CONFIGURATION.md` AutoDelete table) |
| Guide blurbs describe the guides | DOC-01 / D-13 | Content match | Confirm each of the six Documentation blurbs matches what that guide actually contains |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none: the check script already exists)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending (plan-time boxes ticked 2026-11-18; status stays draft until execution)
