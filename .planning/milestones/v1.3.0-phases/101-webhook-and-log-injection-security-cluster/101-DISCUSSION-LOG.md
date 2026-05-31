# Phase 101: Webhook + Log-Injection Security Cluster - Discussion Log

> **Audit trail only.** Not consumed by downstream agents (researcher, planner, executor).
> Decisions captured in `101-CONTEXT.md` — this log preserves the discussion.

**Date:** 2026-05-31
**Phase:** 101-webhook-and-log-injection-security-cluster
**Mode:** discuss (standard)
**Areas discussed:** SEC-01 sanitizer scope, BUG-02 flag design, SEC-02 GET normalization, SEC-03 rate-limit tuning

## Pre-flight notes

- `init.phase-op 101` initially returned `phase_found: false` — root cause: GSD's `new-milestone` updated ROADMAP.md slice-2 text but never scaffolded the per-phase directories, and `init.phase-op` resolves phases by on-disk directory presence (not roadmap text). The roadmap parser (`roadmap.get-phase`) returns `found:false` for both slice-1 (100) and slice-2 (101) phases due to the project's `<details>`-wrapped milestone layout; `init.phase-op` masks this for slice-1 because those directories already exist.
- **Resolution:** created `.planning/milestones/v1.3.0-phases/101-webhook-and-log-injection-security-cluster/` (slug confirmed with user — matches STATE.md's recorded focus). `init.phase-op 101` then resolved cleanly. Same scaffold step will be needed for phases 102/103.
- No `.continue-here.md`, no SPEC.md, no prior CONTEXT.md for this phase. 2 pending todos, 0 matched phase 101.

## Questions asked & decisions

### SEC-01 — sanitizer sweep breadth
- **Options presented:** (a) shared helper + remote-tainted sites only [recommended]; (b) shared helper applied to ALL filename log sites; (c) shared helper, sweep decided by researcher.
- **User selection:** "take your recommendations on all" → **(a)** shared helper + remote-tainted sites only.
- **Captured as:** D-01, D-02, D-03.

### BUG-02 — fail-closed flag location/naming
- **Options presented:** (a) `general.webhook_require_secret` bool default false [recommended]; (b) auto-require when sonarr/radarr enabled; (c) new `[webhook]` config section.
- **User selection:** **(a)** `general.webhook_require_secret`.
- **Captured as:** D-04, D-05, D-06, D-07.
- **Note:** Option (b) explicitly rejected as a COMPAT break (would change behavior for existing *arr-enabled installs with no secret).

### SEC-02 — config GET secret normalization
- **Options presented:** (a) always emit empty string + existing `_is_set` boolean [recommended]; (b) fixed-mask placeholder when set; (c) let researcher confirm current GET shape first.
- **User selection:** **(a)** always empty string + existing boolean.
- **Captured as:** D-10, D-11.

### SEC-03 — webhook rate-limit value
- **Options presented:** (a) 60 req/60s per route [recommended]; (b) 120 req/60s per route; (c) let researcher derive from *arr docs.
- **User selection:** **(a)** 60 req/60s per route.
- **Captured as:** D-08, D-09.

## Claude's discretion items

- `sanitize_log_value()` helper name/signature/module location.
- Whether BUG-02's 503 raises in `_verify_hmac` vs top of `_handle_webhook` (must precede body parse).
- Test structure — reuse slice-1 regression tests where they pin current behavior.

## Deferred ideas raised

- DNS-rebind hardening, mandatory-secret (vs opt-in), settings audit log, other out-of-scope known bugs — all logged in CONTEXT.md `<deferred>` per REQUIREMENTS.md Out-of-Scope table.

## Scope creep redirected

None — discussion stayed within the four scoped requirements.
