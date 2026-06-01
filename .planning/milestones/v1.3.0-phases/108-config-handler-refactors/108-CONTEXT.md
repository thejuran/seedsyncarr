# Phase 108: Config + Handler Refactors - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Two independent, behavior-preserving backend refactors from the v1.3.0 slice-4 architecture set:

- **ARCH-02** — Make `Config` secret-field discovery declarative. Push a `secret=True` marker into each secret field's `PROP` declaration so the encrypt-at-rest / decrypt / redaction loops discover secret fields dynamically from property metadata instead of from the hand-maintained `_SECRET_FIELD_PATHS` tuple.
- **ARCH-03** — Deduplicate the five per-action HTTP handler scaffolds in `web/handler/controller.py` into a shared `_dispatch_command(...)` helper.

Both are internal restructurings: no change to user-observable behavior, HTTP request/response contract, on-disk config/persist format, or any public API the web layer or tests depend on. The existing Python suite is the regression net and must stay green. **No release/tag/version work** — that is a milestone-end action after Phase 109 + the batched pre-release walkthrough.

The exact same set of secret fields must be encrypted/redacted before and after (`api_token`, `webhook_secret`, `sonarr_api_key`, `radarr_api_key`, `remote_password`); the exact same single-action and bulk-action HTTP response shapes/status codes must hold.

</domain>

<decisions>
## Implementation Decisions

### ARCH-02 — Declarative secret discovery API
- **D-01:** Add **only** `secret=True` to the relevant `PROP` declarations (no per-field section string). Recover the ini-section mapping that `_SECRET_FIELD_PATHS` currently carries (the 3-tuple `(key, field_name, ini_section)`) by **deriving the section structurally from the owning `InnerConfig` subclass** (e.g. `General`, `Sonarr`, `Radarr`, `AutoDelete`) at discovery time. Rationale: matches the CONCERNS.md intent — "declare it `secret=True`, nothing else" — and keeps section info structural rather than re-duplicated in a string literal.
  - Mechanism: extend `InnerConfig.PropMetadata` (currently `checker`, `converter`) with a `secret: bool` field, and thread a `secret=False` kwarg through `InnerConfig._create_property` / the `PROP` alias. The encrypt/decrypt/redact paths iterate property metadata, filtering on `secret is True`.
- **D-02:** **Fully remove** the `_SECRET_FIELD_PATHS` module-level tuple. Expose a dynamic discovery API (e.g. a `Config.secret_fields()` classmethod, or equivalent on `InnerConfig`, returning the same `(key/attr, field_name, ini_section)` shape the current consumers expect) and **repoint the second consumer, `seedsyncarr.py`** (`src/python/seedsyncarr.py:18` import + `:413` `for attr, field, _ in _SECRET_FIELD_PATHS`). No backward-compat shim/alias is kept — the requirement is to remove the hand-maintained tuple, and a same-named derived alias would invite future readers to mistake it for the old hand-maintained list.

### ARCH-03 — Shared dispatch helper
- **D-03:** Extract `_dispatch_command(action, file_name, success_msg, *, guard=False)` (or equivalent signature) and use it from the **five `__handle_action_*` methods only** (`queue`, `stop`, `extract`, `delete_local`, `delete_remote`). The duplicated ~15-line scaffold (unquote → optional `_check_path_safe` guard → build `Controller.Command` → `WebResponseActionCallback` → `queue_command` → `wait(timeout=_ACTION_TIMEOUT)` → 504-on-timeout / success-body / `callback.error`+`error_code`) collapses into the helper. The `guard=True` cases are `extract`, `delete_local`, `delete_remote`; `queue` and `stop` pass `guard=False`.
  - **Leave `_process_bulk_commands` as-is.** The bulk loop has materially different semantics (parallel queuing, per-file timeout, result aggregation, partial-failure reporting) that the success criteria require to stay byte-identical. CONCERNS.md lists bulk sharing the helper as optional ("can share it"), not required — out of scope for this phase to avoid risking bulk timeout/partial-failure behavior.

### Plan / commit structure
- **D-04:** **Two separate plans** — `108-01` = ARCH-02 (config secret discovery, touches `common/config.py` + `seedsyncarr.py`), `108-02` = ARCH-03 (handler dedup, touches `web/handler/controller.py`). They have no interdependency and touch disjoint files, so they can run as one parallel wave or sequentially; either way each lands with its own focused test run for cleaner review and git-bisect. Matches how slice 4 already structures independent items.

### Claude's Discretion
- Exact name/return shape of the secret-discovery API (`secret_fields()` vs property-metadata iterator) — planner/researcher choose, provided the encrypt/decrypt/redact loops and `seedsyncarr.py` consume the same data the tuple provided.
- Exact `_dispatch_command` signature details (positional vs keyword, return type annotations) so long as the five handlers' observable responses are unchanged.
- Whether the two plans run as one wave (parallel) or sequential — both are acceptable.
- New test shape proving "a new `secret=True` field is auto-discovered without touching other files" (ARCH-02 success criterion #2).

</decisions>

<specifics>
## Specific Ideas

- The declarative goal is explicitly: adding a future secret field should require **only** declaring it `secret=True` in its `PROP`, with the encrypt/decrypt/redact paths picking it up automatically (ARCH-02 success criterion #2). The design must make that true, not just remove the tuple.
- `_dispatch_command`'s `guard` parameter maps to the existing `_check_path_safe(file_name)` call that currently appears in `extract` / `delete_local` / `delete_remote` but not `queue` / `stop`.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — ARCH-02 (line 17), ARCH-03 (line 18), cross-cutting COMPAT + coverage constraints (lines 28, 31, 40); traceability ARCH-02/03 → Phase 108.
- `.planning/ROADMAP.md` §"Phase 108: Config + Handler Refactors" — Goal + 5 success criteria (the locked acceptance contract).
- `.planning/codebase/CONCERNS.md` — "Duplicate-by-five secret-field walk in `Config`" (lines 31–35, fix approach = push `secret=True` into `PROP`); `_dispatch_command` extraction approach (line 29); fragile property-addon pattern note (line 155).

### Target source files
- `src/python/common/config.py` — `InnerConfig.PropMetadata`/`_create_property`/`PROP` (lines 130–222), `_SECRET_FIELD_PATHS` tuple (lines 19–42), encrypt loop (`to_str`, ~483–499), decrypt loop (`from_dict`, ~437–474). ARCH-02 primary target.
- `src/python/seedsyncarr.py` — `_SECRET_FIELD_PATHS` import (line 18) + startup decrypt-error reporting loop (line 413). ARCH-02 second consumer to repoint (D-02).
- `src/python/web/handler/controller.py` — five `__handle_action_*` methods (lines 76–185) + route registration (lines 66–74); `_process_bulk_commands` (line 334, **left untouched**). ARCH-03 primary target.

### Regression net
- `tests/integration/test_web/test_handler/test_controller.py` — covers bulk + single action paths (per CONCERNS.md line 193); the behavior-preserving guarantee for ARCH-03.
- Existing `Config` encrypt/decrypt/redact tests (Phase 81 Fernet-at-rest suite) — the behavior-preserving guarantee for ARCH-02.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `InnerConfig.PropMetadata` already exists as the per-property metadata carrier (`checker`, `converter`) — `secret` is a natural third field; `__prop_addon_map` already maps property → metadata, giving a ready iteration surface for dynamic discovery.
- `_check_path_safe(file_name)` is the existing guard reused by 3 of the 5 handlers — becomes the `guard=True` branch of `_dispatch_command`.
- `WebResponseActionCallback` + `Controller.Command` + `queue_command` + `_ACTION_TIMEOUT` are the shared dispatch primitives already used identically across all five handlers.

### Established Patterns
- `PROP = InnerConfig._create_property` module-level alias is the single declaration point for all config properties — extending its signature is the declarative lever for ARCH-02.
- Secret fields live across multiple `InnerConfig` subclasses (`General`: `webhook_secret`, `api_token`; plus `Sonarr`/`Radarr` API keys and `remote_password`), so section derivation must work per-owning-class, not just for `General`.
- Each `__handle_action_*` returns `HTTPResponse` with status 504 on timeout, 200-with-body on success, or `callback.error_code` on failure — the invariant the helper must preserve exactly.

### Integration Points
- `Config.from_dict` (decrypt path) and `Config.to_str`/`to_file` (encrypt path) both walk `_SECRET_FIELD_PATHS` today — both must switch to the new dynamic discovery in lockstep so the exact same five fields are covered.
- `seedsyncarr.py` startup hook is the only consumer outside `config.py`; the web layer never touches `_SECRET_FIELD_PATHS` directly.

</code_context>

<deferred>
## Deferred Ideas

- Folding the bulk per-file dispatch into the shared `_dispatch_command` helper — explicitly out of scope (D-03); revisit only if a future phase wants full single+bulk unification and is willing to re-verify bulk timeout/partial-failure semantics.
- The "no structured cancellation for queued bulk commands" and "bulk timeout leaves command in queue" concerns (CONCERNS.md lines 70, 273) are separate bugs, not part of this behavior-preserving refactor.
- ARCH-01 (Controller god-class decomposition) is Phase 109, not here.

### Reviewed Todos (not folded)
None — no pending todos matched this phase's scope.

</deferred>

---

*Phase: 108-config-handler-refactors*
*Context gathered: 2026-06-01*
