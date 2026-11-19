# Phase 128: Arr Key Normalization - Research

**Researched:** 2026-11-18
**Domain:** Python backend: config save handler (bottle), Sonarr/Radarr queue client, log/response hygiene for secrets
**Confidence:** HIGH (all findings verified against the codebase in this session; no new packages)

## Summary

This is a small, codebase-internal change. No new dependencies. Three code paths handle a Sonarr/Radarr API key today, and only one of them normalizes it:

1. **Test Connection** (`web/handler/config.py:346-364`) strips the key, then requires `_API_KEY_CHARS = [\x21-\x7e]+` (printable ASCII without space). [VERIFIED: codebase]
2. **Save** (`ConfigHandler.__handle_set_config`, `config.py:304-344`) stores `str(value)` verbatim through `set_property`. The Arr key props use `Checkers.null` / `Converters.null` (`common/config.py:363,374`). It echoes the value back as `"{section}.{key} set to {value}"` (line 342). [VERIFIED: codebase]
3. **Queue check** (`ArrQueueClient.enabled_targets`, `controller/arr_queue.py:164-176`) passes `config.sonarr.sonarr_api_key or ""` raw into `ArrTarget`. `__fetch_worker` sends it as `X-Api-Key` (line 278). [VERIFIED: codebase]

I probed the installed `requests` 2.33.1 in this session. A key with **leading** whitespace or an embedded CR/LF raises `InvalidHeader`, which the worker logs as `"Sonarr queue check failed: InvalidHeader"` (type name only, so the key does not leak). A key with **trailing** space or tab passes header validation and is sent as-is. A blank key `""` is also sent. [VERIFIED: local probe of `requests.utils.check_header_validity`] All of these fail closed: the gate's `start_fetch -> None / records None -> _record_failure -> HOLD("sonarr_unavailable")` path never authorizes an import or deletion (`completion_gate.py:216-221, 268-280`). [VERIFIED: codebase]

**Primary recommendation:** Add one tiny shared module `common/arr_api_key.py` holding the regex plus `normalize_arr_api_key()` and `is_valid_arr_api_key()`. Use it in three places:
- **Test Connection:** a behaviour-preserving refactor.
- **Save handler:** for the two Arr key `(section, key)` pairs only, trim the key, refuse whitespace-only with "Invalid request body", and refuse invalid keys with "{Svc} API key contains invalid characters".
- **`ArrQueueClient`:** normalize in `enabled_targets()`, and validate in `start_fetch()`. A bad key skips the request with a warn-once-per-key-token log line.

Separately, in `__handle_set_config`, replace "set to {value}" with "{section}.{key} updated" for every `(attr, field)` in `Config.secret_fields()`. Do **not** put normalization in a PROP checker/converter (see Pitfall 1).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Normalization rule (trim + charset) | Shared library (`common/`) | — | Imported by both `web` and `controller`. `common` is the existing shared layer, and both already import from it. |
| Normalize/refuse on save (ARR-01, D-02..D-04) | API / Backend (`web/handler/config.py`) | — | The HTTP boundary owns request validation and the 400 wording. No UI changes (out of scope). |
| Secret-free save confirmation (D-07) | API / Backend (`web/handler/config.py`) | — | The response body is built there. `Config.secret_fields()` is the source of truth for which props are secret. |
| Normalize-on-read for live queue checks (ARR-02) | Backend controller (`controller/arr_queue.py`) | — | `enabled_targets()` reads config on every call, so normalizing there fixes in-memory padded keys without resaving. |
| Fail-safe skip for empty/invalid key (ARR-03) | Backend controller (`ArrQueueClient.start_fetch`) | `completion_gate.py` (unchanged consumer) | `start_fetch` returning `None` already makes the gate record unavailability and hold. No gate change is needed. |
| Persistence | Database/Storage (`Config.to_str/from_str`, configparser) | — | Unchanged. configparser already strips values on read. |

## Project Constraints (from CLAUDE.md)

There is no project `./CLAUDE.md`. These directives come from the user's global `~/.claude/CLAUDE.md`, `CLAUDE.local.md` and memory:

- **Security (absolute):** never log sensitive data (tokens, API keys). Never expose internal error details to end users. This phase directly enforces both.
- **Correctness:** guard nullable returns (`sonarr_api_key` may be `None`). Don't swallow exceptions silently. Don't `as`-cast untrusted data (the Python analogue is to validate `value` at the boundary).
- **Follow existing conventions:** reuse the existing patterns: `start_fetch` URL-scheme skip, `type(e).__name__`-only logging, the `_key_token` opaque tokens, and `Config.secret_fields()`.
- **CI lint gap (memory):** CI runs whole-tree `ruff check src/python/` as a separate gate. Run it on the whole tree, not just changed files. Baseline is clean ("All checks passed!" verified locally with ruff 0.15.9; CI pins 0.15.22).
- **One PR per phase (memory).**
- **Plan review (CLAUDE.local.md):** Codex review runs in parallel with the plan checker. This affects the orchestrator, not the research.
- **Badge labels / e2e** memories: not applicable. This phase has no UI text change.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope (D-07 was folded in by owner choice).

Also out of scope (REQUIREMENTS.md): URL normalization beyond API keys, UI redesign/UI changes, any change to completion/import/deletion safeguards.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARR-01 | A Sonarr/Radarr API key entered with leading/trailing whitespace is saved normalized, using the same rule as Test Connection. | Shared helper in `common/arr_api_key.py`. Save-handler branch for `("sonarr","sonarr_api_key")` / `("radarr","radarr_api_key")` (Pattern 2). Test Connection refactored onto the same helper (Pattern 1). Integration test via `test_app.post_json` on a real `Config`. |
| ARR-02 | A previously saved whitespace-padded key works for queue requests without resaving (normalized on read); one consistent rule across save, Test Connection and queue. | `enabled_targets()` normalizes with the shared helper (Pattern 3). Fail-before/pass-after test: in-memory padded key, then `enabled_targets()`, then `start_fetch`, then assert the header carries the stripped key. A "same rule" parity test drives one padded key through all three paths. |
| ARR-03 | An empty or invalid key fails safely in queue checks (no unsafe import/deletion decision), and no key value appears in logs. | `start_fetch` validation skip returns `None`, so the gate's existing `_record_failure` produces `HOLD("<code>_unavailable")` (Pattern 4). Warn once per `_key_token`. Log-content tests over all logger levels. Gate-level test with the real client. |
</phase_requirements>

## Standard Stack

No new libraries. Everything uses what the repo already ships. [VERIFIED: codebase, pyproject.toml]

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `re` (stdlib) | 3.11/3.12 | `fullmatch` on the charset regex | Already used for `_API_KEY_CHARS`. |
| `requests` | 2.33.x (locked `^2.33.0`; 2.33.1 in local test venv) | Outbound queue/status calls | Existing. Its header validation is *why* the charset rule exists (CR-01). |
| `bottle` | 0.13.4 | Config set handler | Existing. |

### Supporting (tests)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.0.3 | Runner | All tests. |
| `unittest.mock` | stdlib | `@patch("controller.arr_queue.requests")`, MagicMock loggers | Existing pattern in `test_arr_queue.py`. |
| `WebTest` | 3.0.7 | `self.test_app.post_json("/server/config/set", ...)` integration tests against a real `Config` | `tests/integration/test_web/test_handler/test_config.py`. |

**Installation:** none.

## Package Legitimacy Audit

Not applicable. This phase installs no external packages. Packages removed: none. Packages flagged: none.

## Architecture Patterns

### System Architecture Diagram

```
 Settings page / e2e / curl
        │  POST /server/config/set {section,key,value}
        ▼
 ConfigHandler.__handle_set_config
   ├─ body/section/key/value guards (existing)
   ├─ has_section / has_property (existing 404s)
   ├─ [NEW] (section,key) is an Arr key? ──► normalize_arr_api_key(value)
   │        ├─ "" after trim ─────────────► 400 "Invalid request body"           (D-04)
   │        ├─ !is_valid_arr_api_key ─────► 400 "<Svc> API key contains invalid characters" (D-03)
   │        └─ value_str = trimmed                                               (D-02)
   ├─ inner_config.set_property(key, value_str)  ──► in-memory Config ──► (periodic/exit) to_file
   └─ response: secret prop? "<s>.<k> updated" : "<s>.<k> set to <v>"            (D-07)

 GET /server/config/test/sonarr (Test Connection)
   └─ _test_arr_connection(svc, saved url, saved key)
        ├─ empty/whitespace ──► "<Svc> API key is required"   (unchanged)
        ├─ normalize + !valid ─► "<Svc> API key contains invalid characters" (unchanged)
        └─ requests.get(... X-Api-Key: normalized)

 Controller loop ──► CompletionGate._run
   ├─ client.enabled_targets()  ──[NEW] ArrTarget(api_key=normalize_arr_api_key(raw))
   │        └─ identity = (code, url, _key_token(normalized key))  ← padded/unpadded = same identity
   └─ client.start_fetch(target)
        ├─ URL scheme not http/https ──► warn, return None   (existing)
        ├─ [NEW] !is_valid_arr_api_key(target.api_key)
        │        ├─ token != last warned for code ──► WARNING "<Label> queue check skipped: API key is missing or invalid"
        │        └─ else ─────────────────────────► DEBUG (same text)
        │        └─ return None  (no thread, no request)
        └─ spawn worker ──► requests.get(X-Api-Key: target.api_key)
   None ──► gate._record_failure ──► snapshot None ──► HOLD("<code>_unavailable") (unchanged)
```

### Recommended Project Structure
```
src/python/
├── common/
│   ├── arr_api_key.py        # NEW: ARR_API_KEY_CHARS, normalize_arr_api_key, is_valid_arr_api_key
│   └── __init__.py           # re-export (follow the "X as X" style already used)
├── web/handler/config.py     # drop local _API_KEY_CHARS; use helper in Test Connection + save; D-07 response
├── controller/arr_queue.py   # enabled_targets normalizes; start_fetch validates + warn-once
└── tests/
    ├── unittests/test_common/test_arr_api_key.py                       # NEW: rule table
    ├── unittests/test_controller/test_arr_queue.py                     # ARR-02/03 tests
    ├── unittests/test_controller/test_completion_gate.py               # ARR-03 gate-level hold test
    ├── unittests/test_web/test_handler/test_config_handler.py          # ARR-01/D-07 unit tests
    └── integration/test_web/test_handler/test_config.py                # ARR-01/D-07 against real Config
```

### Pattern 1: Shared rule module
**What:** One definition of the rule, imported everywhere.
```python
# src/python/common/arr_api_key.py
import re
from typing import Any

# Printable ASCII without space -- the only characters `requests` accepts in
# a header value without raising InvalidHeader, whose message would embed
# the raw key (122-14, CR-01). Shared by Save, Test Connection and the
# queue client so the three can never disagree (Phase 128, D-01).
ARR_API_KEY_CHARS = re.compile(r"[\x21-\x7e]+")


def normalize_arr_api_key(raw: Any) -> str:
    """Trim leading/trailing whitespace. None or a non-string becomes ''."""
    if not isinstance(raw, str):
        return ""
    return raw.strip()


def is_valid_arr_api_key(key: str) -> bool:
    """True for a non-empty, already-normalized key of printable ASCII without space."""
    return ARR_API_KEY_CHARS.fullmatch(key) is not None
```
- `fullmatch` with `+` rejects `""`, so a single predicate covers both "missing" and "invalid". [VERIFIED: regex semantics]
- Treating non-`str` as `""` is the fail-safe choice. A missing key then holds instead of crashing. It also keeps MagicMock-config tests from hitting `TypeError` in `fullmatch`.

**Test Connection refactor (behaviour-preserving):**
```python
if not api_key or not api_key.strip():
    ... "{} API key is required"            # unchanged
api_key = normalize_arr_api_key(api_key)
if not is_valid_arr_api_key(api_key):
    ... "{} API key contains invalid characters"   # unchanged wording
```
The existing tests pin this behaviour: `test_config_key_whitespace_stripped_before_header` (`test_config_handler.py:705`) and `test_config_key_with_newline_never_reaches_requests_or_log` (`test_web_app_builder_logging.py:127`). They must stay green unchanged.

### Pattern 2: Save-path normalization keyed by (section, key)
```python
# module level in web/handler/config.py
_ARR_KEY_PROPS = {
    ("sonarr", "sonarr_api_key"): "Sonarr",
    ("radarr", "radarr_api_key"): "Radarr",
}

# inside __handle_set_config, AFTER has_section/has_property (keeps 404 semantics), BEFORE set_property
service = _ARR_KEY_PROPS.get((section, key))
if service is not None:
    value_str = normalize_arr_api_key(value_str)
    if not value_str:
        return HTTPResponse(body="Invalid request body", status=400)            # D-04
    if not is_valid_arr_api_key(value_str):
        return HTTPResponse(
            body="{} API key contains invalid characters".format(service), status=400)  # D-03

secret = (section, key) in {(attr, field) for (attr, field, _ini) in Config.secret_fields()}
try:
    inner_config.set_property(key, value_str)
    if secret:
        return HTTPResponse(body="{}.{} updated".format(section, key))         # D-07
    return HTTPResponse(body="{}.{} set to {}".format(section, key, value_str))
except ConfigError as e:
    return HTTPResponse(body=str(e), status=400)
```
- **Why section names match:** the request's `section` is the lowercase attribute name (`has_section` does `getattr(self, name)`, `common/config.py:667`). `Config.secret_fields()` returns `(attr_lowercase, field_name, ini_section_TitleCase)` (`common/config.py:677-700`). Compare against `attr`, not `ini_section`. [VERIFIED: codebase]
- **Why `Config` here is the real class:** `Config` is already imported into `web/handler/config.py`, and `secret_fields()` is a classmethod. That keeps it working in unit tests where `self.__config` is a MagicMock. [VERIFIED: codebase]
- **How the refusal stays non-leaking:** the refusal string echoes only the service label, never the value.
- **Existing ConfigError path:** no secret prop today uses a converter or checker whose message echoes the value. `Converters.null` and `Checkers.null` / `string_nonempty` produce "Bad config: Lftp.remote_password is empty". Only `Converters.int/bool` and `Checkers.int_*` echo the value, and no secret uses them. [VERIFIED: codebase `common/config.py:65-125, 264-374`] Lock this in with a test that iterates `Config.secret_fields()` and asserts no response body contains the submitted value, so a future secret that uses an echoing converter fails the test.

### Pattern 3: Normalize on read in `enabled_targets()`
```python
targets.append(ArrTarget("Sonarr", "sonarr",
                         config.sonarr.sonarr_url or "",
                         normalize_arr_api_key(config.sonarr.sonarr_api_key)))
```
Consequences [VERIFIED: codebase]:
- `ArrTarget.identity` now tokenizes the **normalized** key. Re-saving a padded key as its trimmed form keeps the same identity, so no spurious `_reset_integration_state()`. A real key change still changes the token, so the gate resets and fetches immediately (no backoff wait).
- `test_enabled_target_with_blank_url_is_still_enabled` (None key gives `""`) still holds.

### Pattern 4: Fail-safe skip in `start_fetch` with warn-once
Place the check right after the existing URL-scheme check, mirroring it:
```python
if not is_valid_arr_api_key(target.api_key):
    token = _key_token(target.api_key)            # opaque "kN"; never logged
    if self.__key_skip_warned.get(target.code) != token:
        self.__key_skip_warned[target.code] = token
        self.logger.warning("%s queue check skipped: API key is missing or invalid", target.label)
    else:
        self.logger.debug("%s queue check skipped: API key is missing or invalid", target.label)
    return None
```
- `self.__key_skip_warned: Dict[str, str] = {}` is set up in `__init__`. It is controller-thread-only, like `__fetches`, so no lock is needed (see the module docstring's thread model).
- **Validate in `start_fetch`, not only in `enabled_targets`.** Tests and the sonarr5 replay build `ArrTarget` directly, and `start_fetch` is the single gate before any outbound request.
- **Defence in depth:** the worker can send `target.api_key` unchanged, because it is already normalized and validated by the time a worker exists.
- **"Once per key value":** the warning repeats only when the token differs from the last one warned for that code. A key that becomes valid and is later set back to the same invalid value will not re-warn unless the planner clears `__key_skip_warned[code]` on a successful start. **Recommendation:** clear it when a fetch is started with a valid key, so a re-broken key warns again. That matches the intent of "warn again only after the key changes".
- No gate change. `fid is None` triggers `_record_failure(t, now)` (`completion_gate.py:219-221`), which feeds `_classify` and returns `_UNAVAILABLE`, then `HOLD("sonarr_unavailable")`.

### Anti-Patterns to Avoid
- **Normalizing/validating in a PROP checker or converter.** See Pitfall 1: it would break startup for existing configs.
- **Validating only in `enabled_targets()` and building `ArrTarget(api_key="")` for invalid keys.** That collapses every invalid key to one token, so "warn again after the key changes" breaks. Keep the stripped (possibly invalid) key in the target and validate in `start_fetch`.
- **Logging `repr(target)` / `target` / the request headers.** `ArrTarget` is a NamedTuple, and its repr includes `api_key`. Never pass the target object to a log call.
- **Introducing a second regex copy.** Delete `_API_KEY_CHARS` from `web/handler/config.py`. Its only other reference is the docstring/test wording, and `grep _API_KEY_CHARS` shows the single use at `config.py:360`.
- **Matching the secret set on `ini_section` (TitleCase).** The request section is lowercase.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Which settings are secret | A hard-coded list in the handler | `Config.secret_fields()` | Auto-discovers every `secret=True` PROP. Future secrets get D-07 for free. |
| Key-change detection for warn-once | Storing the raw key, or a hash, on the client | `_key_token()` in `arr_queue.py` | Already opaque, per-process and never logged. A hash of a key is still key-derived material. |
| "Unavailable → hold" behaviour | New gate states or reason codes | `start_fetch` returning `None` | The gate already maps it to `_record_failure`, backoff and `HOLD(<code>_unavailable)`. |
| Log capture in tests | Ad-hoc string matching on one level | `_calls(self.logger, level)` helper (`test_arr_queue.py` ~160) and the `_CapturingHandler` / `SerializeLogRecord` pattern (`test_web_app_builder_logging.py`) | Already covers the formatted and SSE-serialized forms. |

## Runtime State Inventory

This is a behaviour change, not a rename. The question that matters is whether any stored state already holds padded keys.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `settings.cfg` on disk: configparser strips leading/trailing whitespace on read (`Config.from_str`). A padded key exists only in **in-memory** config after a save in the current session. | None. Normalize-on-read (ARR-02) covers the in-memory case. No data migration. |
| Live service config | None. Sonarr/Radarr themselves are not reconfigured. | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | Key *names* unchanged (`sonarr_api_key`, `radarr_api_key`). Encryption-at-rest (`to_str` encrypt hook) operates on the already-trimmed value. | None. |
| Build artifacts | None. | None. |

## Common Pitfalls

### Pitfall 1: Putting the rule in the config PROP layer breaks startup
**What goes wrong:** A stripping/validating `Checker` or `Converter` on `sonarr_api_key` also runs in `Config.from_str → from_dict → set_property` at startup and in `Config()` defaults (`None`/`""`). A stored key that is invalid after trimming (or an empty default) would raise `ConfigError` and stop the app from booting. Today that state merely holds completions.
**How to avoid:** Validate at the HTTP save boundary and at the queue call site only (D-03/D-06 define those two behaviours). Leave the PROPs as `Checkers.null` / `Converters.null`.
**Warning signs:** `test_common/test_config.py` fixtures with `sonarr_api_key=""` start failing.

### Pitfall 2: The ARR-02 regression must actually fail before the fix
**What goes wrong:** A test that builds `ArrTarget(..., API_KEY)` directly, or reloads from a file, passes before the fix.
**How to avoid:** Set `self.context.config.sonarr.sonarr_api_key = "  " + API_KEY + "\n"` on the in-memory (MagicMock) config. Get the target from `self.client.enabled_targets()`, call `start_fetch`, settle, then assert `mock_requests.get.assert_called_once_with(..., headers={"X-Api-Key": API_KEY}, ...)`. Before the fix the header holds the padded value, so the test fails. Record the RED run output in the plan/summary (TDD mode).

### Pitfall 3: `str.strip()` strips Unicode whitespace too
**What goes wrong:** `"key ".strip()` → `"key"`. NBSP, `　`, `\x1c-\x1f` and `\x85` count as whitespace for `str.strip()`. [VERIFIED: Python `str.isspace` semantics]
**How to avoid:** Nothing to fix. This is the existing Test Connection behaviour, and D-01 makes all three paths share it. Pin it in the rule-table test so it stays consistent. Inner NBSP still fails the charset rule.

### Pitfall 4: Warning-count assertions in shared-logger tests
**What goes wrong:** In `test_completion_gate.py` / `test_sonarr5`, `context.logger.getChild` returns the **same** MagicMock for the gate and the client. Gate debug lines and client lines land on one mock, so counts can be off.
**How to avoid:** Assert on message content (`"API key is missing or invalid"`), not on total warning counts, in gate-level tests. Use exact counts only in `test_arr_queue.py`, where only the client logs.

### Pitfall 5: The existing URL-skip test asserts exactly one warning
`test_start_fetch_rejects_non_http_scheme` (~`test_arr_queue.py:555`) expects `len(warnings) == 1` with a valid `API_KEY`, so it is unaffected. `test_start_fetch_rejects_blank_url` uses `("", "")`: the URL check runs first and returns `None` before the key check, which is fine. **Keep the URL check before the key check** so these stay green.

### Pitfall 6: Angular logs the save confirmation to the browser console
`settings-page.component.ts:152` runs `this._logger.info(reaction.data)`, so today's "sonarr.sonarr_api_key set to <KEY>" also lands in the browser console. D-07 fixes this server-side and needs no Angular change. [VERIFIED: codebase] Also, Angular's local config copy keeps the *untrimmed* entered value until the next config GET (`config.service.ts:66-69`). That is cosmetic only, because the server holds the trimmed value. UI changes are out of scope, so leave it alone and mention it in the summary.

### Pitfall 7: Trailing-space keys may "work" against real Sonarr
Kestrel/ASP.NET likely trims optional whitespace around header values (RFC 9110 field-value OWS), so a trailing-space key may have authenticated before. [ASSUMED] This does not change the design, because normalizing is still correct. Just don't write tests or docs claiming trailing space *always* produced a 401. The 122 review's "trailing space gets HTTP 401" claim is unverified.

## Code Examples

### ARR-02 regression (fail-before / pass-after)
```python
# in TestArrQueueFetch (class is @patch("controller.arr_queue.requests"))
def test_padded_in_memory_key_is_sent_normalized(self, mock_requests):
    self.context.config.sonarr.sonarr_api_key = "  " + API_KEY + "\n"
    _bind_exceptions(mock_requests)
    mock_requests.get.return_value = _response(200, [b"[]"])
    target = self.client.enabled_targets()[0]
    self.assertIsNotNone(self.client.start_fetch(target))
    self.assertTrue(settle(self.client, "sonarr"))
    self.assertEqual([], self.client.poll("sonarr").records)
    mock_requests.get.assert_called_once_with(
        "http://sonarr.internal.example:8989/api/v3/queue/details",
        headers={"X-Api-Key": API_KEY}, timeout=(3.05, 10),
        allow_redirects=False, stream=True)
```

### ARR-03 skip + warn-once + no key in logs
```python
def test_invalid_key_skips_request_and_warns_once_per_key(self, mock_requests):
    _bind_exceptions(mock_requests)
    bad = "LEAKPROBE inner space"
    before = threading.active_count()
    t1 = ArrTarget("Sonarr", "sonarr", SONARR_URL, bad)
    self.assertIsNone(self.client.start_fetch(t1))
    self.assertIsNone(self.client.start_fetch(t1))
    mock_requests.get.assert_not_called()
    self.assertEqual(before, threading.active_count())
    self.assertEqual(1, len(_calls(self.logger, "warning")))
    self.assertIn("API key is missing or invalid", _calls(self.logger, "warning")[0])
    self.assertIsNone(self.client.start_fetch(ArrTarget("Sonarr", "sonarr", SONARR_URL, "")))
    self.assertEqual(2, len(_calls(self.logger, "warning")))   # key changed → warns again
    for level in ("debug", "info", "warning", "error", "exception"):
        for line in _calls(self.logger, level):
            self.assertNotIn("LEAKPROBE", line)
```
Also include table cases: `None`, `""`, `"   "`, `"a\x00b"`, `"clé"`, `"a\tb"`.

### ARR-03 gate-level fail-safe
In `test_completion_gate.py`, use a real `ArrQueueClient` and a MagicMock config with `sonarr_api_key = "   "`. Then `gate.evaluate({ROOT: SIZE})[ROOT] == HOLD("sonarr_unavailable")`, `requests.get` is not called, and `client.in_flight("sonarr")` is False.

### ARR-01 + D-07 integration (real Config via WebTest)
```python
def test_set_arr_key_trimmed_and_not_echoed(self):
    resp = self.test_app.post_json("/server/config/set",
        {"section": "sonarr", "key": "sonarr_api_key", "value": "  abcDEF123\n"})
    self.assertEqual(200, resp.status_int)
    self.assertEqual("abcDEF123", self.context.config.sonarr.sonarr_api_key)
    self.assertEqual("sonarr.sonarr_api_key updated", str(resp.html))
    self.assertNotIn("abcDEF123", str(resp.html))
```
Plus these cases:
- `"   "` returns 400 "Invalid request body" with the stored key unchanged.
- `"abc def"` returns 400 "Sonarr API key contains invalid characters" with the stored key unchanged and the value absent from the body.
- The Radarr twin of each.
- Non-secret `general.debug` still returns "general.debug set to True".
- A loop over `Config.secret_fields()` asserts the success body never contains the submitted value.

### Parity test ("one consistent rule", ARR-02 second clause)
One padded key, `"\t" + K + "  "`, goes through all three paths. Save it via the handler, then check that `config.sonarr.sonarr_api_key == K`. Test Connection (requests patched) must send `K`. `ArrQueueClient.enabled_targets()[0].api_key == K`, and `start_fetch` must send `K`. The planner should also add a parity table in `test_arr_api_key.py`: each case gives the same accept/reject verdict from `is_valid_arr_api_key(normalize_arr_api_key(x))` as from the save handler's 200/400 outcome.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Key strip/validate only in Test Connection | One shared rule across save, test and queue | Phase 128 | Ends the "false all-clear" (122 WR-04). |
| Save echoes "set to <value>" for all props | Secret props answer "<s>.<k> updated" | Phase 128 (D-07) | Secrets no longer reach response bodies or the browser console. |

**Existing tests asserting "set to":** none. A `grep -rn "set to"` over `src/python/tests`, `src/e2e` and `src/angular/src` found no assertion on the save-confirmation text. [VERIFIED: grep] CONTEXT mentioned `test_seedsyncarr.py`, but the grep shows it does not assert this text. The e2e helper `settings.page.ts:setSonarrApiKey` only checks `response.ok()`. Its value `'test-FAKE-not-real-0000'` is valid under the rule, so e2e is unaffected.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Sonarr/Radarr (Kestrel) trims trailing OWS in header values, so trailing-space keys may have authenticated before this fix | Pitfall 7 | Low. It affects only the wording of the summary or release notes, not the design or tests. |

## Open Questions (RESOLVED)

1. **Should the warn-once memory reset after a successful (valid-key) start?**
   - What we know: D-06 says "warn once per key value (again only after the key changes)".
   - Recommendation: clear `__key_skip_warned[code]` when `start_fetch` passes validation. It is the simplest reading and costs nothing. Either choice satisfies D-06.
   - **RESOLVED:** yes, reset on a valid start. Planned in 128-03 Task 2 (`self.__key_skip_warned.pop(target.code, None)` when the key passes validation) and pinned by `test_invalid_key_warns_again_after_valid_key_seen` (128-03 Task 1).
2. **Clearing a stored Arr key.** After D-04 there is still no way to clear a key through Save (empty was already refused). That is pre-existing behaviour, and the owner explicitly accepted it in D-04. No action.
   - **RESOLVED:** no action. Accepted by the owner in D-04; no plan changes how a key is cleared.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest (pipx venv, carries bottle/requests/WebTest) | Unit + integration tests | ✓ | pytest 9.0.3, requests 2.33.1 | — |
| ruff | Whole-tree lint gate | ✓ | 0.15.9 locally (CI pins 0.15.22) | — |
| pytest-cov | `fail_under = 88` coverage gate | ✗ in the pipx venv. The poetry venv exists at `~/Library/Caches/pypoetry/virtualenvs/seedsyncarr-5QbP0KwB-py3.12`, but `poetry run python -c "import requests"` failed, so its deps are not installed. | — | Run `cd src/python && poetry install --with dev`, then `make coverage-python` (`poetry run pytest --cov`). CI's python job runs `pytest -v` in Docker (`make run-tests-python`). |
| Docker | `make run-tests-python` (CI parity) | client present (29.9.3); daemon not confirmed | — | Local pytest is sufficient per task. Use Docker only for the phase gate if desired. |

Baseline in this session: `pytest -q -p no:cacheprovider` over `test_arr_queue.py`, `test_config_handler.py`, the integration `test_config.py` and `test_web_app_builder_logging.py` gave **196 passed** in 6.3 s. `ruff check src/python/` reported "All checks passed!".

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (+ unittest.TestCase style, WebTest for integration) |
| Config file | `src/python/pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`, `fail_under = 88`) |
| Quick run command | `cd src/python && pytest -q -p no:cacheprovider tests/unittests/test_common/test_arr_api_key.py tests/unittests/test_controller/test_arr_queue.py tests/unittests/test_controller/test_completion_gate.py tests/unittests/test_web/test_handler/test_config_handler.py tests/unittests/test_web/test_web_app_builder_logging.py tests/integration/test_web/test_handler/test_config.py tests/unittests/test_sonarr5` |
| Full suite command | `cd src/python && pytest -q -p no:cacheprovider` **and** `cd <repo root> && ruff check src/python/` **and** coverage: `cd src/python && poetry run pytest --cov` (≥ 88) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARR-01 | Padded key saved trimmed (Sonarr + Radarr) | integration | `pytest tests/integration/test_web/test_handler/test_config.py -k arr_key -q` | ✅ file / ❌ tests (Wave 0) |
| ARR-01 / D-03 | Inner-invalid key → 400 "<Svc> API key contains invalid characters", stored key unchanged, value not echoed | unit + integration | `pytest tests/unittests/test_web/test_handler/test_config_handler.py -k arr_key -q` | ✅ / ❌ |
| ARR-01 / D-04 | Whitespace-only → 400 "Invalid request body", stored unchanged | unit + integration | same | ✅ / ❌ |
| ARR-01 / D-01 | Test Connection behaviour unchanged after refactor | unit (existing) | `pytest tests/unittests/test_web -k "whitespace_stripped or newline_never" -q` | ✅ |
| ARR-02 | In-memory padded key sent normalized by the queue client (**fail-before/pass-after**) | unit | `pytest tests/unittests/test_controller/test_arr_queue.py -k padded -q` | ✅ / ❌ |
| ARR-02 | Padded vs trimmed key give the same `identity` (no spurious gate reset) | unit | `pytest tests/unittests/test_controller/test_arr_queue.py -k identity -q` | ✅ / ❌ |
| ARR-02 | One rule across the three paths (string-input parity) | integration + unit | `pytest tests/integration/test_web/test_handler/test_arr_key_parity.py tests/unittests/test_common/test_arr_api_key.py -q` | ❌ Wave 0 (128-01, 128-04) |
| ARR-03 | Empty/invalid key → `start_fetch` None, no request, no thread | unit | `pytest tests/unittests/test_controller/test_arr_queue.py -k "invalid_key or missing_key" -q` | ✅ / ❌ |
| ARR-03 | Warn once per key token, debug thereafter, warn again on change | unit | same | ✅ / ❌ |
| ARR-03 | Gate holds `<code>_unavailable` with a bad key (no unsafe decision) | unit | `pytest tests/unittests/test_controller/test_completion_gate.py -k bad_key -q` | ✅ / ❌ |
| ARR-03 | No key substring in any log line (all levels) | unit | covered in the arr_queue tests above | ✅ / ❌ |
| D-07 | Every `secret_fields()` prop answers "<s>.<k> updated" and never echoes the value. Non-secret keeps "set to". | integration | `pytest tests/integration/test_web/test_handler/test_config.py -k secret -q` | ✅ / ❌ |

### Sampling Rate
- **Per task commit:** the quick run command above (< 15 s), plus `ruff check src/python/`.
- **Per wave merge:** the full `pytest -q -p no:cacheprovider` in `src/python`, plus whole-tree ruff.
- **Phase gate:** full suite green, whole-tree ruff clean, and coverage ≥ 88 (`poetry run pytest --cov` after `poetry install --with dev`) before `/bm:verify-work`.

### Wave 0 Gaps
- [ ] `tests/unittests/test_common/test_arr_api_key.py`: rule table (None, "", whitespace-only, padded valid, inner space, tab, CR/LF, NUL, non-ASCII, NBSP padding).
- [ ] RED tests in the existing files listed above. For TDD, record the failing run of the ARR-02 padded-key test before the `enabled_targets` change.
- No framework install is needed for pytest or ruff. Coverage needs `poetry install --with dev` locally.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (outbound credential only) | — |
| V3 Session Management | no | — |
| V4 Access Control | no (save endpoint auth unchanged) | — |
| V5 Input Validation | yes | Shared allowlist regex `[\x21-\x7e]+` + trim at the save boundary, with refusal rather than silent mutation for inner-invalid keys |
| V6 Cryptography | no (encryption-at-rest unchanged) | — |
| V7 Error Handling & Logging | yes | No key in logs (label + fixed reason only; `type(e).__name__` at boundaries). Fixed refusal strings. |
| V8 Data Protection | yes | No secret values echoed in HTTP responses (D-07), and therefore none in the browser console. |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leaked via `requests.InvalidHeader` message (CR/LF/leading space in header) | Information disclosure | Validate before any request (start_fetch skip). The worker already logs only the type name. |
| Secret echoed in the HTTP save response, then logged by the browser | Information disclosure | D-07: "<s>.<k> updated" for `secret_fields()` |
| Secret in a log via `ArrTarget` repr | Information disclosure | Never log target objects. Tests sweep all logger levels for a probe substring. |
| Header injection via CR/LF in a stored key | Tampering | The charset rule excludes control characters, and the queue path now enforces it too. |
| Misconfigured key causing an unsafe completion decision | Elevation/Tampering (data loss) | Skip → `None` → gate `HOLD(<code>_unavailable)`. The gate is untouched. |

## Sources

### Primary (HIGH confidence)
- Codebase (read in this session): `src/python/web/handler/config.py`, `controller/arr_queue.py`, `controller/completion_gate.py`, `common/config.py`, `common/context.py`, `common/__init__.py`, `web/serialize/serialize_config.py`, Angular `config.service.ts` / `settings-page.component.ts`, e2e `settings.page.ts`, tests listed above.
- `.planning/phases/122-safety-acceptance-and-logging-fixes/122-REVIEW.md` §WR-04.
- Local probe: `requests.utils.check_header_validity` on requests 2.33.1 (leading space and `\n` raise InvalidHeader; trailing space, tab and `""` pass).
- Local runs: the 196-test baseline, and ruff "All checks passed!".

### Tertiary (LOW confidence)
- Kestrel header-value OWS trimming (A1). Training knowledge only.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new dependencies; versions verified locally.
- Architecture: HIGH. Every integration point was read, and the gate's failure path was traced end to end.
- Pitfalls: HIGH, except Pitfall 7, which is ASSUMED.

**Research date:** 2026-11-18
**Valid until:** 2026-12-18 (stable internal code; re-check if `arr_queue.py` or `config.py` changes first)
