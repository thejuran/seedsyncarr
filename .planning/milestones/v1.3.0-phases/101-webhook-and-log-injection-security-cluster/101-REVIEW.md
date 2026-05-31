---
phase: 101-webhook-and-log-injection-security-cluster
reviewed: 2026-05-31T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - src/python/common/__init__.py
  - src/python/common/config.py
  - src/python/common/types.py
  - src/python/controller/controller.py
  - src/python/controller/scan/remote_scanner.py
  - src/python/controller/webhook_manager.py
  - src/python/lftp/job_status_parser.py
  - src/python/lftp/lftp.py
  - src/python/seedsyncarr.py
  - src/python/web/handler/webhook.py
  - src/python/web/serialize/serialize_config.py
  - src/python/model/model.py
findings:
  critical: 0
  blocker: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 101: Code Review Report

**Reviewed:** 2026-05-31T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the Phase 101 security cluster (BUG-02 opt-in `webhook_require_secret` 503 fail-closed guard, SEC-03 webhook rate-limiting, SEC-02 always-blank secret fields on config GET, SEC-01 shared `sanitize_log_value()` CWE-117 helper).

The four focus areas hold up under adversarial inspection:

- **Fail-closed guard ordering (BUG-02) is correct.** `_make_require_secret_guard(...)` wraps the `rate_limit(...)`-decorated handler, so the 503 check executes outermost — before the rate-limit counter is consulted (429 cannot mask 503) and before any request body is read. The `if require_secret and not secret` short-circuit delegates to the inner handler unchanged when the flag is off or a secret is present, preserving back-compat.
- **`sanitize_log_value()` is sound** and is applied log-output-only at every site touched by the diff; raw values are preserved for control flow, matching, and returns (verified in `webhook_manager.process`, `controller.__process_commands`, `remote_scanner.scan`). The `remote_scanner.py` except-branch NameError risk is genuinely fixed — `safe_out` is derived locally with `errors='replace'` instead of referencing the possibly-undefined `out_str`.
- **COMPAT holds.** `webhook_require_secret` defaults to the string `"False"` via `general_dict.get(...) is None` (covers both absent key and explicit-None), round-trips cleanly through `Converters.bool`/`_strtobool`/`str(bool)`, and `_create_default_config` sets it `False`. The SEC-02 SET path is untouched — `_ALWAYS_BLANK_FIELDS` only affects the GET serializer, never `to_str`/on-disk format.
- **No bare `except`, no sensitive data logged, generic client error bodies** (503 "Service unavailable", 429 JSON, 401 generic).

No BLOCKER/Critical defects found. The findings below are residual log-injection sinks the SEC-01 sweep missed, plus minor robustness/consistency items.

## Warnings

### WR-01: Residual CWE-117 log-injection sink in `is_file_downloaded` (SEC-01 coverage gap)

**File:** `src/python/controller/controller.py:266-275`
**Issue:** The SEC-01 phase objective is to sanitize attacker-influenceable file names at all log sites, but `is_file_downloaded()` still interpolates `filename` raw:
```python
self.logger.debug(
    "File '{}' not in downloaded list (size={}, evictions={})".format(
        filename, ...
    )
)
```
`filename` flows from `AutoQueue` (`auto_queue.py:261/270`), where it is `file.name` — a model file name ultimately sourced from the remote scanner. Remote filenames are attacker-influenceable (a crafted name on the seedbox with embedded CR/LF/ANSI escapes reaches this log line unescaped). This pre-dates the base commit and was not in the diff, but it is squarely within the SEC-01 sink inventory and defeats the "sanitize across ~30 sites" goal for this code path.
**Fix:**
```python
"File '{}' not in downloaded list (size={}, evictions={})".format(
    sanitize_log_value(filename), ...
)
```

### WR-02: Residual CWE-117 log-injection sink in `_prune_extracted_files`

**File:** `src/python/controller/controller.py:541`
**Issue:** `remove_extracted_file_names` is a `set` of model file names (remote-scanner sourced) interpolated raw:
```python
self.logger.info("Removing from extracted list: {}".format(remove_extracted_file_names))
```
A `repr`/`str` of a set still embeds the raw filename characters; a name containing `\n` forges a log line. Same SEC-01 sink class as WR-01. Not in the diff, but in scope for the log-injection hardening objective.
**Fix:** Sanitize each element before logging, e.g.
```python
safe = [sanitize_log_value(n) for n in remove_extracted_file_names]
self.logger.info("Removing from extracted list: {}".format(safe))
```
(`sanitize_log_value` of each list element; the surrounding list brackets are not attacker-controlled.)

### WR-03: 503 fail-closed guard fails OPEN if `webhook_require_secret` is None

**File:** `src/python/web/handler/webhook.py:55`
**Issue:** The guard condition is `if self.__config.general.webhook_require_secret and not self.__config.general.webhook_secret:`. If `webhook_require_secret` is ever `None` (the field's uninitialized default in `Config.General.__init__`, before `from_dict` populates it), `None and ...` short-circuits to falsy and the request is **allowed through** — a fail-OPEN for a security guard whose entire purpose is to fail closed. In normal operation the config always passes through `from_dict` or `_create_default_config`, so `None` is not reachable at runtime today; but the guard's safety depends on an invariant enforced elsewhere rather than being self-contained. A future Config construction path (or a test harness building `Config()` directly and wiring it to the handler) would silently disable the guard.
**Fix:** Make the guard self-defending by treating a non-True flag conservatively only when intended. Since `False`/`None` should both mean "not required", the current behavior is acceptable for the default-off semantic — but the dependency should be made explicit. Either assert the field is a bool at handler construction, or normalize:
```python
require = bool(self.__config.general.webhook_require_secret)
if require and not self.__config.general.webhook_secret:
    ...
```
At minimum, document that `from_dict` is a required precondition for the security invariant.

### WR-04: `lftp.py` queue `escape()` does not neutralize backtick / `$()` shell-style metacharacters

**File:** `src/python/lftp/lftp.py:326-341`
**Issue:** `escape()` rejects `\n`/`\r`/`\x00` and escapes `'` and `"`, then the filename is embedded inside a double-quoted lftp argument: `"\"{remote_dir}/{filename}\""`. Inside lftp's own double-quoted parsing, backslash-escaping of `"` prevents quote-breakout, which is the primary injection vector — so this is defense-in-depth, not a proven break. However, lftp passes commands like `pget`/`mirror` through its own shell-ish tokenizer, and a filename containing a literal backslash (`\`) is NOT escaped by `escape()`; a trailing `\` before the closing `\"` could consume the escape and re-open quote context. This is webhook-adjacent only via model names (not the webhook title directly), so impact is bounded, but the escaping is allowlist-incomplete relative to the `repr`-style rejection used for control chars.
**Fix:** Prefer rejecting backslash as well, or build the command with structured argument quoting (`shlex`-equivalent for lftp) rather than manual string interpolation. At minimum add `\\` handling:
```python
return s.replace("\\", "\\\\").replace("'", "\\'").replace("\"", "\\\"")
```
(Verify ordering: escape backslash first so subsequent escapes are not double-counted.)

## Info

### IN-01: `functools.wraps(handler)` on the guard wrapper is cosmetic and slightly misleading

**File:** `src/python/web/handler/webhook.py:53-62`
**Issue:** `@functools.wraps(handler)` copies `handler`'s metadata onto `wrapper`, but `handler` is itself the `rate_limit` wrapper (already `functools.wraps`-ed to `__handle_sonarr_webhook`). The `wrapper()` signature takes no args while the wrapped chain is invoked with none — fine for these wildcard-free routes — but `wraps` here provides no functional benefit and obscures that two layers of wrapping exist. Harmless.
**Fix:** Optional. Either drop `@functools.wraps` or add a comment that it is purely for log/introspection naming.

### IN-02: Response body format inconsistency between 503, 429, and 401

**File:** `src/python/web/handler/webhook.py:60` (503 plain text), `src/python/web/rate_limit.py:39-44` (429 JSON)
**Issue:** The 503 guard returns `body="Service unavailable"` (plain text, no content-type), while the rate-limit 429 returns a JSON object with `content_type="application/json"`, and HMAC failures return plain text 401. A webhook client (Sonarr/Radarr) parsing responses sees inconsistent shapes across rejection codes. Not a correctness bug — these are all error paths the sender typically only logs — but inconsistent.
**Fix:** Optional. Standardize webhook rejection bodies (all plain text, or all JSON `{"error": ...}`).

### IN-03: `sanitize_log_value` has no type guard for non-`str` input

**File:** `src/python/common/types.py:17,45`
**Issue:** The signature is `sanitize_log_value(value: str) -> str` and immediately calls `value.replace(...)`. Every current call site passes `str(...)`-coerced values (e.g. `sanitize_log_value(str(err))`), so this is safe today. But the helper is now public API (re-exported from `common/__init__.py`) and a future caller passing `None` or an `int` would raise `AttributeError` inside a logging path — masking the real log message. Defensive coercion would make the shared helper robust against its own call sites.
**Fix:** Optional. `value = value if isinstance(value, str) else str(value)` as the first line, or document that callers must pre-coerce.

### IN-04: C1 control-character pass-through is a deliberate, documented tradeoff — flagged for visibility only

**File:** `src/python/common/types.py:30-31,54`
**Issue:** `sanitize_log_value` intentionally leaves C1 controls (0x80–0x9F) unescaped to avoid corrupting multibyte UTF-8 filename bytes. The docstring justifies this and notes CWE-117's CRLF/ANSI surface is fully covered by C0+DEL. This is a reasonable decision; some terminal emulators interpret a raw 0x9B (CSI) as an escape introducer, so a hostile filename could in principle drive cursor manipulation in a C1-aware terminal viewing the raw log. Bounded, accepted-risk; logged here so the tradeoff is on record for the reviewer.
**Fix:** None required. If C1-aware terminals are a concern in the deployment environment, extend the escape range to `0x80 <= cp <= 0x9F` — but only operate on `str` codepoints (never on raw bytes) to preserve UTF-8 integrity.

---

_Reviewed: 2026-05-31T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
