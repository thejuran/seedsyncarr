# Phase 128: Arr Key Normalization - Context

**Gathered:** 2026-11-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A Sonarr/Radarr API key behaves the same whether it is being saved, tested with Test Connection, or used for a live queue completion check, regardless of incidental leading/trailing whitespace (ARR-01..03). One normalization rule — the one Test Connection already applies (`strip()`, then printable ASCII without space, `_API_KEY_CHARS = [\x21-\x7e]+`) — is shared by all three paths. Owner-approved addition (D-07): the config save confirmation stops echoing secret values.

Out of scope (REQUIREMENTS.md): URL normalization beyond API keys, UI redesign/UI changes, any change to completion/import/deletion safeguards.

</domain>

<decisions>
## Implementation Decisions

### Shared rule
- **D-01:** One normalization rule for save, Test Connection and queue checks: trim leading/trailing whitespace, then the trimmed key must fully match the existing Test Connection character rule (printable ASCII, no whitespace/control/non-ASCII). Define it once and reuse it everywhere; Test Connection behavior and its error wording stay unchanged.

### Bad keys on save (ARR-01)
- **D-02:** A Sonarr/Radarr key with leading/trailing whitespace is saved trimmed.
- **D-03:** A key that is still invalid after trimming (inner space, line break, control or non-ASCII character) is **refused** by Save with a 400 and the same wording Test Connection uses ("… API key contains invalid characters"). The previously stored key is unchanged. Uses the existing settings-page save-error path; no UI changes.
- **D-04:** A whitespace-only key is refused exactly like an empty value today (400 "Invalid request body"); the stored key is unchanged. Whitespace is not a way to clear a key.

### Bad key at queue check (ARR-02, ARR-03)
- **D-05:** Queue checks normalize the stored key on read, so a previously saved padded key works without resaving (regression test must fail before the fix and pass after; note configparser already strips values on restart, so the realistic failure is a live in-session config — test the in-memory path).
- **D-06:** If the stored key is empty or still invalid after trimming, the queue check **skips the request** (no outbound call) and is treated as unavailable — completions stay held exactly as for any other unavailable arr; no import or deletion decision changes. Log a reason without the key, e.g. "Sonarr queue check skipped: API key is missing or invalid", mirroring the existing "URL must use http or https" skip. Warn **once per key value** (again only after the key changes, e.g. via the existing opaque key token); subsequent skips log at debug. The key value never appears in any log line.

### Key in save response (owner-approved scope addition)
- **D-07:** For any config property marked `secret=True` (remote password, `api_token`, `webhook_secret`, both Arr keys, etc.), the save confirmation no longer echoes the value — e.g. "sonarr.sonarr_api_key updated". Non-secret properties keep today's "set to <value>" text. Refusal/error responses for secrets must not echo the value either. Frontend does not parse this text (checked); tests asserting the old text must be updated.

### Claude's Discretion
- Where normalization lives (config layer vs. call sites), the shared helper's location/name, and how the save path recognizes Arr key properties.
- Exact log/response wording within the constraints above.
- Test structure, provided ARR-02's regression is shown fail-before/pass-after and the CI gate (full pytest, whole-tree `ruff check src/python/`, `fail_under` ≥ 88) holds.

</decisions>

<specifics>
## Specific Ideas

- The failure being fixed is a false all-clear: Test Connection passes on a padded key while every real queue check fails and completions sit as "Sonarr unavailable" (fail-safe, never a wrong delete).
- Phase 130's release smoke test runs a queue completion check with a whitespace-padded key, so the fix must work on a key entered through the normal settings save path, not just a hand-edited config.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and origin
- `.planning/REQUIREMENTS.md` §Arr key handling (ARR-01..03) and §Out of Scope
- `.planning/ROADMAP.md` §Phase 128 — success criteria
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-REVIEW.md` §WR-04 — original finding and suggested fix
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-CONTEXT.md` D-14 — no secrets in logs; exception-type-only logging at the Test Connection boundary
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-14-PLAN.md` — how Test Connection's strip/validate was introduced

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/python/web/handler/config.py` `_API_KEY_CHARS` (line ~20) and `_test_arr_connection` (lines ~346-431): the rule to share.
- `src/python/controller/arr_queue.py` `_key_token` / `ArrTarget.identity`: opaque per-process key tokens — usable for "warn once per key value" without holding or logging the raw key.

### Established Patterns
- `ArrQueueClient.start_fetch` returns None and logs a warning when the URL scheme is not http/https — the model for the D-06 skip.
- Exception logging at network boundaries logs `type(e).__name__` only (122-14 CR-01).
- Config props declare `secret=True` (`src/python/common/config.py` ~363, ~374); `common/context.py` `_REDACTED_KEYS` redacts them in startup logs.

### Integration Points
- Save: `ConfigHandler.__handle_set_config` → `inner_config.set_property(key, value_str)`, then response "{section}.{key} set to {value}" (`config.py` ~304-344).
- Queue: `ArrQueueClient.enabled_targets` (`arr_queue.py` ~165-176) reads the raw key; `__fetch_worker` sends it as `X-Api-Key` (~278). Downstream consumer: `controller/completion_gate.py`.
- Persistence: `Config.from_str`/`to_str` use configparser, which strips values on read.
- Tests: `src/python/tests/unittests/test_controller/test_arr_queue.py`, `src/python/tests/unittests/test_web/test_handler/test_config_handler.py`, `src/python/tests/unittests/test_seedsyncarr.py` (asserts "set to" text).

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (D-07 was folded in by owner choice).

</deferred>

---

*Phase: 128-arr-key-normalization*
*Context gathered: 2026-11-18*
