# Requirements: SeedSyncarr — v1.3.0 Slice 4 of 4: Backend Architecture Refactor + Test Infra

**Defined:** 2026-06-01
**Core Value:** Reliable file sync from seedbox to local with automated media library integration.
**Milestone:** v1.3.0 — Slice 4 of 4: Backend Architecture Refactor + Test Infra (GSD internal label `v1.3.0-s4`)
**Source:** `.planning/codebase/CONCERNS.md` — "Architecture / Maintainability" (Controller god-class, Config secret-field machinery, bulk-handler duplication) + the rolled-forward INFRA-01 (MP-logger spawn-safety), carried as v2 requirements (ARCH-01..03, INFRA-01) in the slice-3 REQUIREMENTS.md.

> **Release note:** This is the **final** slice of the 4-slice v1.3.0 program. The entire program ships under a single combined `v1.3.0` tag, and that tag is cut when **this** slice completes (preceded by one batched pre-release walkthrough across all four slices). Earlier slices (1-3) intentionally cut no tag.

## v1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Backend Architecture Refactor

- [ ] **ARCH-01**: The `Controller` god-class (`python/controller/controller.py`, ~1115 lines) is decomposed into cohesive collaborators with single responsibilities (e.g. command dispatch, auto-delete lifecycle, model/scan pipeline). The public surface the rest of the app depends on (constructor, `start`/`exit`, command entry points, the model the web layer reads) is preserved — no caller outside the controller package changes. This is a behavior-preserving refactor: the existing Python suite is the regression net and stays green; no user-observable behavior or HTTP-contract change.
- [ ] **ARCH-02**: `Config` secret-field discovery is declarative. The `secret=True` marker is pushed into each secret field's `PROP` declaration so the encrypt-at-rest / decrypt loops discover secret fields dynamically from the property metadata instead of from a hand-maintained list. Adding a new secret field requires only declaring it `secret=True`; the encrypt/decrypt paths pick it up automatically. The current set of encrypted fields (`api_token`, `webhook_secret`, `sonarr_api_key`, `radarr_api_key`, `remote_password`) is unchanged in behavior — same fields encrypted, existing plaintext and Fernet-encrypted configs load unchanged. *(Scope amendment 2026-06-01, user-approved during Phase 108 plan review: the API-response **redaction** path (`web/serialize/serialize_config.py` `_SENSITIVE_FIELDS`) is descoped — it is an independent, intentional superset of the encrypt set (also redacts the non-secret Lftp connection fields `remote_address`/`remote_username`/`remote_path`) and stays as-is. Redaction and encryption-at-rest are kept as separate concerns.)*
- [ ] **ARCH-03**: The per-action handler scaffold is deduplicated. A shared `_dispatch_command(...)` helper is extracted and used by the five `__handle_action_*` methods, removing the repeated per-action boilerplate (unquote, optional path guard, command build, callback wait, response mapping) while preserving the exact observable behavior of every single-action path — same success/error semantics, same response shapes, same status codes. *(Scope amendment 2026-06-01, user-approved during Phase 108 plan review: the **bulk-action loop** is explicitly deferred per CONTEXT D-03 — `_process_bulk_commands` keeps its distinct parallel-queue / per-file-timeout / partial-failure semantics byte-identical and does NOT route through the helper. CONCERNS.md lists bulk sharing the helper as optional.)*

### Test Infra

- [ ] **INFRA-01**: The three `MultiprocessingLogger` analog tests pass on **both** `fork` and `spawn` start methods. The fix is a targeted **production change** to `python/common/multiprocessing_logger.py`: the logger's queue is created from a shared `spawn`-compatible multiprocessing context so a queue handed to a `spawn` child no longer raises `RuntimeError: A SemLock created in a fork context is being shared with a process in a spawn context`. Existing `fork`-based logging behavior is unchanged (no regression on Linux default-fork installs); the three previously-skipped/failing spawn-context analog tests now run and pass on macOS (`spawn`) and Linux (`fork`).

## Cross-Cutting Constraints

These apply to **every** phase in this slice; each phase's success criteria must hold them:

- **Behavior-preserving (COMPAT).** ARCH-01/02/03 are internal restructurings — no change to any user-observable UI/CLI behavior, HTTP request/response contract, on-disk config/persist format, or any public API the web layer or tests depend on. INFRA-01 changes only the MP-logger queue's multiprocessing context, not its logging behavior. Existing config files (plaintext and Fernet-encrypted) load unchanged.
- **The existing test suite is the regression net.** Refactors land test-first where a characterization gap exists, but the primary safety guarantee is that the full pre-refactor suite stays green throughout. No test is deleted to make a refactor pass.
- **CI green** on amd64 + arm64 (Python primary; Angular + E2E unaffected but must stay green).
- **No coverage regression** — slice-1 ratchet floors hold or rise: Python `fail_under` 88; Karma global stmts/branches/fns/lines 83/68/79/83 (untouched this slice). INFRA-01 brings 3 previously-uncounted tests into the suite — coverage holds or rises.
- **Release gate (this slice only).** This slice cuts the single user-facing `v1.3.0` tag at completion, after the batched pre-release walkthrough. No per-phase tag/version work — the tag is a milestone-end action.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Behavior changes bundled into the ARCH refactors | ARCH-01/02/03 are behavior-preserving by definition. Any genuine behavior change discovered mid-refactor becomes a scoped finding (its own decision), not a silent rider on the refactor. |
| Replacing `paste` / `bottle` Python HTTP server | Backend dependency risk noted in CONCERNS.md, but a server swap is a large behavior-test-heavy effort outside an architecture-refactor slice; revisit in a future milestone. |
| Replacing `pexpect`-driven LFTP/SSH | No Python SFTP library matches lftp's parallel-mirror feature set; treated as an external runtime requirement, documented not removed. |
| Pinning `patoolib` / upper-bound hygiene on Python deps | Backend dep hardening, distinct from the architecture refactor; can fold into a later dependency-maintenance pass. |
| Migrate `/server/config/set` from GET-path to POST-body | Backend API contract change, tracked separately (deferred item in STATE.md); not an internal refactor. |
| Frontend / Angular refactors | This slice is backend-Python only; the frontend deps + dead-code work was slice 3. |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 109 | Pending |
| ARCH-02 | Phase 108 | Pending |
| ARCH-03 | Phase 108 | Pending |
| INFRA-01 | Phase 107 | Pending |

**Coverage:**
- v1 requirements: 4 total
- Mapped to phases: 4 of 4 ✓
- Unmapped: 0

---
*Requirements defined: 2026-06-01*
*Last updated: 2026-06-01 — traceability populated by roadmapper: INFRA-01 → Phase 107, ARCH-02+ARCH-03 → Phase 108, ARCH-01 → Phase 109*
