---
phase: 127-readme-accuracy
verified: 2026-11-18T23:23:33Z
status: passed
score: 8/8 must-haves verified
has_blocking_gaps: false
overrides_applied: 0
known_deviations:
  - claim: "README says Post-Import Pruning applies only to releases SeedSyncarr itself downloaded (How It Works, and the forged-import sentence in Security)"
    reality: "The code treats an item as downloaded when a local entry has the same name as a seedbox entry and is at least as large; it does not record which files SeedSyncarr transferred. A copy placed in the downloads folder by hand or by another tool can be pruned after a real or forged import webhook."
    source: "Code review WR-02 / SA-01 (127-REVIEW.md)"
    ruling: "Owner ruled 2026-11-18 to keep the README wording and change the code later"
    tracked_in: "ROADMAP.md backlog 999.9 (Prune only files SeedSyncarr transferred)"
    blocking: false
---

# Phase 127: README Accuracy Verification Report

**Phase Goal:** A reader following the README reaches every existing guide and sees setup, security and cleanup claims stated as they actually behave.
**Verified:** 2026-11-18T23:23:33Z
**Status:** passed
**Re-verification:** No — initial verification

## Known, owner-accepted deviation (not a gap)

One README claim is ahead of the code. The README says pruning applies "only to releases SeedSyncarr itself downloaded" (README.md line 86, and the forged-import sentence at lines 224-226). The code matches by name and size only (`src/python/controller/model_builder.py:510-525`, `model_pipeline.py:205-227`, `controller.py:828-970`), so a file put in the downloads folder by hand or by another tool, with the same name as a seedbox entry and at least its size, can be pruned after an import webhook.

The owner ruled on 2026-11-18 to keep the wording and make the code true instead. That work is backlog 999.9 in `.planning/ROADMAP.md`. Until it lands, this one sentence does not describe actual behavior. It is recorded here plainly and is not counted as a blocking gap for this phase.

## Goal Achievement

### Observable Truths

Roadmap success criteria 1-4 map onto plan truths 1-6; all are covered below.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DOC-01: Documentation section directly after Quick Start links all six guides in two groups, each with a blurb (roadmap SC1) | VERIFIED | README.md lines 56-68. `## Documentation` is the heading immediately after `## Quick Start`. "Using SeedSyncarr": Getting Started, Configuration, Security. "Contributing / internals": Architecture, Development, Testing. All six target files exist and are non-empty. |
| 2 | DOC-01: Installation links the repository guides, website not referenced, every relative link, image and anchor resolves (roadmap SC1) | VERIFIED | Line 136 links `docs/GETTING-STARTED.md` and `docs/CONFIGURATION.md`. The pre-phase `thejuran.github.io/seedsyncarr` link is gone. All 9 relative targets and 3 image paths exist; `#security` and `#how-it-works` match real headings. |
| 3 | DOC-04: Quick Start keeps 8800:8800 in both examples and carries the Network exposure note (roadmap SC4) | VERIFIED | Lines 36 and 102 keep `8800:8800`. Lines 49-54: published on all host interfaces; untrusted networks need an authenticating reverse proxy and restricted network access; `api_token` protects the API but not the UI, which contains the token. Token-in-UI confirmed in `web_app.py:219-223` (meta tag injected into index.html). |
| 4 | DOC-02: "Security by default" gone; always-on controls separated from off-until-configured settings; defaults match code (roadmap SC2) | VERIFIED | Phrase absent. Line 80 lists always-on controls only. Lines 205-216 list the four off-by-default settings. Code: `seedsyncarr.py:387` `webhook_secret = ""`, `:388` `api_token = ""`, `:390` `webhook_require_secret = False`, `:435` `encryption.enabled = False`. |
| 5 | DOC-03: tagline conditioned; cleanup explained once in How It Works; no unconditional delete claim remains (roadmap SC3) | VERIFIED (with the accepted deviation above) | Line 13 tagline says "optional auto-delete waits for Sonarr/Radarr to confirm the import". Line 86 covers import webhook, pruning off by default, 60 second delay, safeguards, deferral, dry-run, local copy only. About This Fork and Features point to it. "never delete", "safely reclaim" and "then deletes" are gone. Code: `autodelete.enabled = False` (`:431`), `delay_seconds = 60` (`:433`), `dry_run = False` (`:432`). |
| 6 | DOC-02 / DOC-03: webhook signing conditions stated as fact, no recommendation to set a secret for Sonarr/Radarr | VERIFIED | Lines 212-226. Matches `webhook.py`: 503 when require-secret is on with no secret (`:53-58`), 401 on missing or invalid `X-Webhook-Signature` (`:94-102`), HMAC-SHA256 of the body (`:91`), verification skipped when the secret is empty. Webhook routes are exempt from the Bearer check (`web_app.py:63-65`). |
| 7 | D-08 (widened to three approved spots): SECURITY.md differs from the pre-phase version only in the intro sentence, the webhook bullet and the Bearer auth bullet | VERIFIED | `git diff --numstat 091f51f2 HEAD -- SECURITY.md` shows 3 lines replaced, 3 added: line 40 (intro), line 43 (webhook bullet), line 44 (Bearer auth bullet). No other line changed. Bearer bullet names all three exempt routes, matching `web_app.py:59-65`. |
| 8 | D-14: Usage Examples sits above Contributing, Security and License; only the three approved wording corrections inside it | VERIFIED | Heading order confirmed (line 149 before 199, 203, 230). Section diff against the pre-phase file shows exactly three changes: "safely reclaim" clause, the HMAC-when-configured sentence, the "then deletes" clause. |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `README.md` | Documentation section, exposure note, conditioned wording | VERIFIED | 232 lines, contains `## Documentation` |
| `SECURITY.md` | Corrected intro, webhook bullet and Bearer auth bullet | VERIFIED | Contains `X-Webhook-Signature`; three approved spots only |
| `.planning/phases/127-readme-accuracy/127-check.py` | Mechanical checks | VERIFIED | Changed since 33c50bfc by commit fbc954ec only: accepts the third SECURITY.md spot and adds a requirement that the Bearer bullet names the three routes. The change tightens the check; no existing check was removed. Selftest passes. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| README Documentation | six guides | relative links | WIRED | All six present and resolving |
| Quick Start note, Features, How It Works, Usage Examples | README Security | `#security` | WIRED | Lines 54, 80, 88, 177 |
| About This Fork, Features | README How It Works | `#how-it-works` | WIRED | Lines 22, 76 |
| README stated defaults | `seedsyncarr.py` default config | check script claims group plus manual read | WIRED | Defaults read directly from source, lines 387-435 |

### Independent Code Re-check

| README / SECURITY.md statement | Source | Result |
|-------------------------------|--------|--------|
| `api_token` empty by default, API open when empty | `seedsyncarr.py:388`, `web_app.py:123-125` | Matches |
| Three routes exempt from Bearer check | `web_app.py:59-65` (`/server/stream`, `/server/status`, `/server/webhook/` prefix) | Matches |
| UI contains the token | `web_app.py:219-223` | Matches |
| `webhook_secret` empty, verification skipped | `seedsyncarr.py:387`, `webhook.py:74-81` | Matches |
| `webhook_require_secret` False; 503 only when on with no secret | `seedsyncarr.py:390`, `webhook.py:53-58` | Matches |
| 401 on missing or invalid signature, header `X-Webhook-Signature`, HMAC-SHA256 | `webhook.py:91-102` | Matches |
| Encryption off by default | `seedsyncarr.py:435` | Matches |
| Pruning off by default, 60 second delay, dry-run available | `seedsyncarr.py:431-433` | Matches |
| Rate limiting on webhook, config-set, test-connection, bulk-command, status | `webhook.py:38-39`, `config.py:154-162`, `controller.py:71`, `status.py:17` | Matches |
| CSP header always sent | `web_app.py:152-160` | Matches |
| Pruning applies only to releases SeedSyncarr downloaded | `model_builder.py`, `model_pipeline.py`, `controller.py` | Does NOT match — owner-accepted, backlog 999.9 |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| Phase check, all groups | `python3 .planning/phases/127-readme-accuracy/127-check.py all` | `all: OK`, exit 0 | PASS |
| Each group separately | `structure`, `claims`, `security`, `scope`, `selftest` | each `OK`, exit 0 | PASS |
| Scope | `git diff --name-only 091f51f2 HEAD` outside `.planning/` | README.md, SECURITY.md only | PASS |
| Lint gate | `ruff check src/python/` | `All checks passed!`, exit 0 | PASS |
| Check-script integrity | `git diff 33c50bfc -- 127-check.py` | 33 insertions, 8 deletions, all from fbc954ec | PASS (see note) |

Note on check-script integrity: the plan's path (ii) asks for the script diff to be reproduced and justified in the SUMMARY. The SUMMARY was written before fbc954ec and still says the script is unchanged. The justification exists in the fbc954ec commit message and the Resolution section of 127-REVIEW.md instead. The diff was read in full here and only adds the approved third spot and a stricter requirement. Record-keeping inconsistency only.

### Behavioral Spot-Checks

Step 7b: SKIPPED (docs-only phase; no runnable code changed).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DOC-01 | 127-01 | Six guides reachable from a Documentation section; installation links repository guides; links resolve | SATISFIED | Truths 1, 2 |
| DOC-02 | 127-01 | Accurate default security posture replaces "Security by default" | SATISFIED | Truths 4, 6 |
| DOC-03 | 127-01 | HMAC and cleanup claims stated with conditions; README reviewed for unconditional claims | SATISFIED, with the owner-accepted deviation (backlog 999.9) | Truths 5, 6 |
| DOC-04 | 127-01 | Quick Start exposure note | SATISFIED | Truth 3 |

All four IDs in the plan frontmatter appear in REQUIREMENTS.md mapped to Phase 127. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| README.md | 86, 224-226 | Claim ahead of code ("only releases SeedSyncarr itself downloaded") | Info (owner-accepted) | Tracked as backlog 999.9 |
| README.md | 223 | "pruning stops, so nothing is deleted" is absolute; a delete timer armed by an import confirmed before the secret was set can still fire (review IN-01) | Info | Narrow window; those deletions follow a genuinely confirmed import |
| 127-01-SUMMARY.md | 22, 74 | Says check script unchanged; stale after fbc954ec | Info | Planning record only |

No TBD, FIXME, XXX or TODO markers in README.md or SECURITY.md.

### Human Verification Required

None. The plan defers no human checks, and every claim was checkable against files and source.

### Gaps Summary

No blocking gaps. The four roadmap success criteria and all eight plan must-haves hold in the files as committed. One README claim (pruning limited to releases SeedSyncarr downloaded) does not yet match the code; the owner chose to keep the wording and fix the code under backlog 999.9.

---

_Verified: 2026-11-18T23:23:33Z_
_Verifier: Claude (bm-verifier)_
