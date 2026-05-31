# Requirements: SeedSyncarr — v1.3.0 Slice 2 of 4: Known Bugs + Security

**Defined:** 2026-05-31
**Core Value:** Reliable file sync from seedbox to local with automated media library integration.
**Milestone:** v1.3.0 — Slice 2 of 4: Known Bugs + Security (GSD internal label `v1.3.0-s2`; one user-facing `v1.3.0` tag cut after slice 4)
**Source:** `.planning/codebase/CONCERNS.md` buckets 2 (Known Bugs) + 3 (Security Considerations), audited 2026-05-26; plus two rolled-forward v1.3.0 deferred items.

> **Release note:** This milestone cuts **no** git tag. The entire 4-milestone program ships under a single combined `v1.3.0` tag, cut only after the final program milestone completes.

## v1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Known Bugs

- [ ] **BUG-01**: A user-facing confirmation modal renders without any raw `innerHTML` sink — `ConfirmModalService` builds content via `Renderer2` (or a structural Angular component) so escaping is structural, not string-concatenation dependent. Folds in the deferred skipCount type-erasure hardening (coerce/escape `skipCount`).
- [ ] **BUG-02**: An operator can **opt in** to webhook fail-closed behavior via a new config flag (default **off**, so existing installs are unchanged). When the flag is on and no secret is configured, the webhook endpoint rejects requests with 503 before parsing the body. When the flag is off (default), the existing behavior is preserved exactly: no secret → HMAC skipped + loud startup warning (the current `Empty webhook_secret skips HMAC` backward-compat contract). The required-secret expectation and the new flag are surfaced to the operator (startup warning / docs). **No breaking change on upgrade.**
- [ ] **BUG-03**: Auto-delete `threading.Timer` callbacks are tracked and cancelled on controller shutdown, and a fired callback no-ops if shutdown is in progress — no deletion runs against a half-torn-down model.
- [ ] **BUG-04**: The SSE stream-service registry never leaves an orphaned subscription when a reconnect fires in the same tick as a timeout — the prior EventSource/subscription is torn down before its replacement, leaving exactly one active subscription.

### Security

- [ ] **SEC-01**: All log sites that interpolate remote-/webhook-/user-supplied strings pass through a sanitizer that strips or escapes CR/LF/control characters (CWE-117), closing the log-injection gap beyond the already-mitigated `webhook_manager` sites.
- [ ] **SEC-02**: The config GET response does not leak whether a secret is set vs unset beyond the existing explicit boolean flag — secret-present and secret-absent responses are otherwise indistinguishable in shape.
- [ ] **SEC-03**: The webhook endpoint is rate-limited with the same middleware applied to other mutable endpoints in v1.2.0, with a limit tuned to legitimate *arr callback frequency.

### Test Infra (rolled forward from v1.3.0 deferred)

- [ ] **INFRA-01**: The three MultiprocessingLogger analog tests that fail under macOS `spawn` pass on both `fork` and `spawn` start methods (fix = promote the `process_1` target to module scope). Lowest priority; include only if it does not expand the milestone.

## Cross-Cutting Constraints

These apply to **every** phase in this slice; each phase's success criteria must hold them:

- **COMPAT — no breaking changes on upgrade.** Existing config files must load unchanged (no new *required* fields; any new flag defaults to current behavior). No change to existing public API contracts (request/response shapes, status codes for already-supported paths), webhook/HTTP behavior for existing configs, or on-disk persist formats. New behavior is additive and opt-in. (Anchors the project's `Empty webhook_secret skips HMAC` backward-compat decision — BUG-02 must not break it.)
- **CI green** on amd64 + arm64 (Python + Angular + E2E).
- **No coverage regression** — slice-1 ratchet floors hold or rise: Python `fail_under` 88; Karma global stmts/branches/fns/lines 83/68/79/83.
- **Safe observability** — security fixes never log sensitive data; return generic client errors while logging detail server-side.
- **No release/tag/version-bump work** in any phase (single `v1.3.0` tag cut only after slice 4).

## v2 Requirements (deferred to later program milestones)

### Frontend Deps + Dead Code (next program milestone)

- **DEPS-01**: Drop jQuery 4, Font Awesome 4.7, css-element-queries.
- **DEPS-02**: Move mock-model fixtures out of the production bundle via environment `fileReplacements`.

### Backend Architecture Refactor (final program milestone)

- **ARCH-01**: Extract the `Controller` god-class.
- **ARCH-02**: Refactor `Config` property machinery; auto-discover secret fields.
- **ARCH-03**: Dedup the per-action bulk handler scaffold.

## Out of Scope

| Feature | Reason |
|---------|--------|
| DNS-rebind hardening for `_validate_url` | Accepted risk per existing inline code comment ("out of scope for a homelab tool"); v1.3.0 test documents the limitation. |
| Session-cookie auth / dropping api-token meta tag | Homelab single-user threat model accepted; larger redesign, not a bug fix. |
| TLS termination in-product | Deployment concern (reverse proxy); documented expectation, not a code change here. |
| Settings audit log | Missing-feature (CONCERNS bucket 9), not a known bug or actionable security item. |
| Other known-bugs not in the approved set (e.g. `set_property` non-string coercion, ServiceExit broad-except, bulk-command queue-after-timeout) | Deferred — either lower risk or larger behavior change than this milestone's scope; revisit in a later milestone. |
| Performance / scaling items (CONCERNS buckets 6 + 8) | Out of theme for a bug-fix + security milestone. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-02 | Phase 101 | Pending |
| SEC-01 | Phase 101 | Pending |
| SEC-03 | Phase 101 | Pending |
| SEC-02 | Phase 101 | Pending |
| BUG-03 | Phase 102 | Pending |
| INFRA-01 | Phase 102 | Pending |
| BUG-01 | Phase 103 | Pending |
| BUG-04 | Phase 103 | Pending |

**Coverage:**
- v1 requirements: 8 total
- Mapped to phases: 8 ✓
- Unmapped: 0 ✓

Phase distribution:
- Phase 101 (Webhook + Log-Injection Security Cluster): BUG-02, SEC-01, SEC-03, SEC-02
- Phase 102 (Controller Concurrency + Test Infra): BUG-03, INFRA-01
- Phase 103 (Angular Defects): BUG-01, BUG-04

---
*Requirements defined: 2026-05-31*
*Last updated: 2026-05-31 after roadmap creation — all 8 requirements mapped to phases 101-103 (0 unmapped)*
