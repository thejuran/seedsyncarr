# Phase 101: Webhook + Log-Injection Security Cluster - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden the webhook endpoint and the backend log surface. Four scoped changes, all additive and opt-in where behavior could change:

1. **BUG-02** — opt-in webhook fail-closed (new config flag, default off) that rejects unauthenticated webhook calls with 503 when no secret is configured.
2. **SEC-01** — sanitize every remote-/user-supplied string before it reaches a log line (CWE-117 log injection).
3. **SEC-03** — rate-limit the webhook routes with the existing v1.2.0 middleware.
4. **SEC-02** — normalize the config GET response so secret-set vs secret-unset is indistinguishable beyond the existing explicit boolean flag.

Scope anchor from ROADMAP.md (Phase 101) — fixed. Phases 102 (controller concurrency + test infra) and 103 (Angular defects) are out of scope here.

**Cross-cutting (locked by REQUIREMENTS.md):** no breaking change on upgrade — existing config files load unchanged, no new *required* fields, status codes/response shapes for already-supported paths unchanged; CI green amd64+arm64; Python `fail_under` ≥ 88 holds or rises; security fixes log no sensitive data and return generic client errors with detail logged server-side; **no release/tag/version work**.
</domain>

<decisions>
## Implementation Decisions

### SEC-01 — Log-injection sanitizer (CWE-117)
- **D-01:** Extract a single shared helper (e.g. `sanitize_log_value()`) that strips/escapes CR/LF/control characters. Replace the 3 existing inline `.replace("\n","\\n").replace("\r","\\r")` copies (`webhook_manager.py:37`, `webhook_manager.py:76`, `controller.py:790`) with calls to it — one definition, no copy-paste drift. **Home for the helper: `src/python/common/types.py`** (research-confirmed: zero circular-import risk, already imported transitively by web/handler, controller, and lftp). Helper preserves the existing inline behavior (CR/LF escaping).
- **D-02:** Apply the helper to log sites whose interpolated value is **provably remote-/webhook-/user-supplied** (filenames/titles from *arr callbacks, scanned remote names) — NOT to internal-only strings. Targeted to the CWE-117 threat model, not a blanket wrap.
- **D-03 (RESOLVED post-research; ⚠️ RE-DERIVED during planning; ⚠️⚠️ FINALIZED via Option-C in adversarial round 3 — see notes):** Taint-reachable site set is locked: the **3 confirmed webhook-tainted sites** (the inline-escape consolidation targets) PLUS **`controller.py:760` (webhook root-name mapping lookup) and `controller.py:975` (auto-deleted local file name)** — both log remote-/seedbox-derived names a crafted filename could exploit. **`controller.py:229` (canceled pending auto-delete) is DEFERRED** — it logs an internal dict key validated upstream, lower risk; record as a deferred-item note. delete/extract/dispatch debug logs are out of scope this slice.
  > **⚠️ SUPERSEDED by 101-04-PLAN.md / 101-05-PLAN.md (BLOCKER-4 re-derivation).** Adversarial review found the research mis-classified `controller.py:1075` (command-dispatch log) as internal — it is in fact user-supplied via the `/server/command/<file_name>` URL path (unquoted) and the bulk `/server/command/bulk` JSON `files[]` array, unauthenticated when `api_token` is empty — so `1075` is now **in scope** (Plan 04). The auto-delete-timer + model-layer cluster (`controller.py:229,820,841,848,866,876,897,926,948` + `model/model.py:81,97,112`) is **NOT dropped**: it moved to **Plan 05 (Wave 3, same slice)** because it shares controller.py with Plan 04 and must sequence rather than parallelize. The authoritative, final site set is the union specified in **101-04-PLAN.md (`D-03 re-derived`) and 101-05-PLAN.md** — follow those, not the "deferred / out of scope this slice" wording above. 101-VALIDATION.md likewise predates this split.
  > **⚠️⚠️ OPTION-C FINALIZATION (adversarial round 3, user-approved).** A 3rd codex pass flagged additional SEC-01 taint clusters. The user reviewed the scope tension (REQUIREMENTS.md "ALL sites" vs this D-02/D-03 "provably remote-supplied; delete/extract/dispatch out of scope this slice") and chose **Option C**: fold in ONLY the two highest-risk, clearly attacker-facing sites that are hard to defend as "debug logs," and FORMALLY DEFER the rest:
  > - **IN (this slice):** `controller.py:1069` (`_notify_failure` "Command failed." warning) — added to **Plan 04**. `_msg` is built by callers from the user-supplied `command.filename` (`controller.py:1080` and sibling failure messages), then logged raw at 1069. Only the LOG is sanitized; the `_callback.on_failure(_msg,_code)` at line 1071 keeps the RAW `_msg` (log-output-only).
  > - **IN (this slice):** `controller/scan/remote_scanner.py:118` (JSON-decode-error log of the raw SSH scan output) — added to **Plan 06** (the "raw remote process output" cluster; disjoint file from controller.py/lftp, Wave 2, no collision). BOTH `str(err)` and the raw `out` are sanitized; the except is made NameError-safe (it does NOT reference `out_str`, which is defined inside the try at line 114 and may be undefined when the decode itself raised — a locally-derived `safe_out` is used instead).
  > - **DEFERRED (later v1.3.0 slice):** the remaining codex-flagged clusters — see the `<deferred>` "Deferred SEC-01 sites (later slice)" subsection below for the per-cluster rationale. This is a documented deferral, not a silent drop; it satisfies SEC-01's per-site-justification expectation for the not-yet-covered sites.
  > The authoritative, final round-3 site set is the union specified in **101-04-PLAN.md (`D-03` incl. 1069), 101-05-PLAN.md, and 101-06-PLAN.md (incl. remote_scanner.py:118)**.

### BUG-02 — Opt-in webhook fail-closed (highest priority; MUST NOT break back-compat)
- **D-04:** New config flag **`general.webhook_require_secret`**, type bool, **default `false`**. Lives in the existing General config section next to `webhook_secret`.
- **D-05:** Flag **on** + no secret configured → webhook endpoint rejects with **503 before the body is parsed**. Flag **off** (default) → existing behavior preserved exactly: no secret → HMAC skipped + loud startup warning (honors the locked `Empty webhook_secret skips HMAC` contract). Secret configured → valid-HMAC requests succeed unchanged.
- **D-06:** Old config files load with no new required field — wire the default via the existing `Config.from_dict` back-compat fallback pattern (`config.py:515-569`, the same shape used for webhook_secret/api_token/rate_limit). No new *required* field.
- **D-07:** The flag + required-secret expectation are surfaced to the operator — extend the existing empty-secret startup warning (`seedsyncarr.py:372-378`) and document the flag.

### SEC-03 — Webhook rate-limiting
- **D-08:** Reuse the existing `rate_limit(max_requests, window_seconds)` decorator (`src/python/web/rate_limit.py`) — the same middleware applied to bulk/config/status handlers. No new mechanism.
- **D-09:** Limit = **60 requests / 60 seconds, per route** (matches config/status endpoints). Applied independently to `/server/webhook/sonarr` and `/server/webhook/radarr` so the two don't share a budget. Over-limit → generic **429**.

### SEC-02 — Config GET response normalization
- **D-10 (CORRECTED post-research):** The `*_is_set` boolean assumed in the original wording **does not exist** in the codebase. Reality (research-confirmed): `serialize_config.py` emits `**REDACTED**` for unauthenticated requests and the **real secret value** for authenticated ones. **New decision:** `general.webhook_secret` and `general.api_token` always serialize as **`""`** in the config GET response on **both** the authenticated and unauthenticated paths — replacing both the `**REDACTED**` mask and the real-value emission. No new `*_is_set` keys are added (no current consumer; research confirmed no Angular code reads these values from the GET response).
- **D-11:** Result: the GET response shape is **identical whether a given secret is set or unset** — no value, length, or key-presence difference distinguishes the two. The SET path and on-disk persist format are **untouched** (COMPAT). Surface: `serialize_config.py` / `__handle_get_config` (`config.py:~87`).

### Claude's Discretion
- Exact helper name/signature and module location for `sanitize_log_value()`.
- Whether BUG-02's 503 is raised in `_verify_hmac` vs at the top of `_handle_webhook` (must be before body parse either way).
- Test structure — but reuse slice-1 regression tests where they already pin current behavior (REQUIREMENTS.md notes several slice-1 tests cover these paths).
</decisions>

<specifics>
## Specific Ideas

- The `Empty webhook_secret skips HMAC` backward-compat decision is a **hard constraint** — BUG-02's default-off flag exists specifically to preserve it. Any path where an existing install's webhook behavior changes on upgrade is a defect, not a feature.
- CONCERNS.md line 99 suggests auto-requiring the secret when `sonarr.enabled`/`radarr.enabled` — explicitly **rejected** here because it would change behavior for existing *arr-enabled installs (COMPAT violation). The opt-in flag is the chosen path instead.
- Land fixes test-first where a slice-1 regression test already pins the current behavior of the touched path.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & concerns (source of truth)
- `.planning/REQUIREMENTS.md` — BUG-02, SEC-01, SEC-02, SEC-03 full statements + Cross-Cutting Constraints (COMPAT, CI green, coverage floors, safe observability, no-release). MUST read.
- `.planning/codebase/CONCERNS.md` §"Security Considerations" — original audit detail: webhook trust-of-json-parse (lines 95-99), file-rename/log-injection partial mitigation + audit recommendation (lines 101-105), `from_dict` back-compat branches (line 38).
- `.planning/ROADMAP.md` §"Phase 101" (lines 426-439) — phase goal + 5 success criteria + COMPAT cross-cutting criterion.

### Code surfaces (read before implementing)
- `src/python/web/handler/webhook.py` §`_verify_hmac` (lines 43-77) + `_handle_webhook` (lines 79+) + `add_routes` (lines 30-34) — BUG-02 fail-closed hook point and SEC-03 route registration.
- `src/python/web/rate_limit.py` — the `rate_limit` decorator to reuse for SEC-03; see usage in `web/handler/{controller,status,config}.py`.
- `src/python/web/handler/config.py` §`__handle_get_config` (line 87) + `__handle_set_config` — SEC-02 GET response serialization surface.
- `src/python/common/config.py` §`from_dict` back-compat branches (lines 515-569) — BUG-02 flag default wiring (D-06); `_SECRET_FIELD_PATHS` (lines 19-25) — secret-field inventory for SEC-02.
- `src/python/controller/webhook_manager.py:37,76` + `src/python/controller/controller.py:790` — the 3 inline CWE-117 replacements to consolidate (SEC-01 D-01).
- `src/python/controller/controller.py:1069` (`_notify_failure` warning) — SEC-01 round-3 Option-C addition (Plan 04); `_msg` built from `command.filename`.
- `src/python/controller/scan/remote_scanner.py:118` (JSON-decode-error log of raw SSH scan `out`) — SEC-01 round-3 Option-C addition (Plan 06); NameError-safe (do not reference `out_str`).
- `seedsyncarr.py:372-378` — existing empty-secret startup warning to extend (BUG-02 D-07).

### Backward-compat anchor
- The `Empty webhook_secret skips HMAC` decision is recorded in PROJECT.md Key Decisions — BUG-02 must not break it.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `rate_limit(max_requests, window_seconds)` decorator (`web/rate_limit.py`) — drop-in for SEC-03; already wraps bulk (10/60), config/status (60/60), test-connection (5/60) handlers.
- Inline CWE-117 escape pattern `.replace("\n","\\n").replace("\r","\\r")` already proven in `webhook_manager.py` — promote to the shared `sanitize_log_value()` helper (SEC-01 D-01).
- `Config.from_dict` back-compat fallback pattern (`config.py:515-569`) — established mechanism for adding an optional config field that loads unchanged on old files (BUG-02 D-06).
- Existing `*_is_set` boolean convention in the config GET response — SEC-02 keeps it and zeroes the value field around it.

### Established Patterns
- Webhook auth flow: `_handle_webhook` → body-size cap (413) → `_verify_hmac` (401) → JSON parse (400). BUG-02's 503 must slot in **before** body parse.
- Per-route POST handler registration via `web_app.add_post_handler(path, fn)` — decorate the bound method exactly like other handlers do (`status.py:16`, `config.py:28`).
- Generic client error + server-side detail logging is the house style for security responses (honors safe-observability constraint).

### Integration Points
- BUG-02 flag flows: `config.py` (declare + from_dict default) → `webhook.py` (read `self.__config.general.webhook_require_secret`) → `seedsyncarr.py` startup warning.
- SEC-02 touches only the GET serialization in `config.py` — set path and on-disk format unchanged (COMPAT).
- SEC-01 helper is shared infra — pick a module importable by controller, lftp, and webhook_manager without a circular import.
</code_context>

<deferred>
## Deferred Ideas

- DNS-rebind hardening for `_validate_url` — out of scope (accepted homelab risk per REQUIREMENTS.md Out-of-Scope table).
- Making `webhook_secret` *mandatory* (vs opt-in flag) — rejected as a COMPAT break; the opt-in flag is the in-scope alternative.
- Settings audit log (who/when/what changed config) — CONCERNS bucket 9 missing-feature, not in this slice.
- `set_property` non-string coercion, ServiceExit broad-except, bulk-command queue-after-timeout — other known bugs deferred per REQUIREMENTS.md Out-of-Scope.

### Deferred SEC-01 sites (later v1.3.0 slice) — Option-C deferral (adversarial round 3)
The round-3 codex pass flagged additional SEC-01 taint clusters. Per the user's Option-C decision, the two highest-risk attacker-facing sites (`controller.py:1069` and `remote_scanner.py:118`) are folded into THIS slice (Plans 04/06); the clusters below are **formally deferred** to a later v1.3.0 slice. This is a documented, justified deferral (not a silent drop) — each carries the same one-line `sanitize_log_value(...)` fix when picked up. Per-cluster rationale:

**Delete / extract / dispatch operation logs** (remote-/model-derived names; lower-frequency, not the primary webhook attack path):
- `delete_process.py:17,19,45,48` — remote/model-derived name; deferred to a later v1.3.0 slice — same `sanitize_log_value` one-line fix when picked up.
- `extract/dispatch.py:106,152,183` — remote/model-derived name; deferred to a later v1.3.0 slice — same `sanitize_log_value` one-line fix when picked up.
- `extract/extract_process.py:32,39,79` — remote/model-derived name; deferred to a later v1.3.0 slice — same `sanitize_log_value` one-line fix when picked up.

**AutoQueue / model-builder / controller bookkeeping logs** (remote-/model-derived names; internal bookkeeping/debug surface, not the primary webhook attack path):
- `auto_queue.py:180,262-265,307-318` — remote/model-derived name; deferred to a later v1.3.0 slice — same `sanitize_log_value` one-line fix when picked up.
- `controller.py:268-270,541` — remote/model-derived name; deferred to a later v1.3.0 slice — same `sanitize_log_value` one-line fix when picked up.
- `model_builder.py:559-565` — remote/model-derived name; deferred to a later v1.3.0 slice — same `sanitize_log_value` one-line fix when picked up.

This deferral keeps SEC-01's per-site-justification expectation satisfied: every codex-flagged site is either covered (Plans 04/05/06) or explicitly recorded here with a defer rationale. See D-03 Option-C finalization note above for the IN/DEFERRED split.

### Reviewed Todos (not folded)
- 2 pending todos exist (webob-cgi-upstream-unblock, migrate-config-set-to-post-body) — neither matched phase 101 (todo.match-phase returned 0 matches). The config-set-to-POST-body item is a separate-milestone API contract change per STATE.md deferred items.

</deferred>

---

*Phase: 101-webhook-and-log-injection-security-cluster*
*Context gathered: 2026-05-31*
</content>
