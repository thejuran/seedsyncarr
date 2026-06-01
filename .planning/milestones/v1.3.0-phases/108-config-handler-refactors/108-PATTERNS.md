# Phase 108: Config + Handler Refactors - Pattern Map

**Mapped:** 2026-06-01
**Files analyzed:** 3 source files modified (+ 2 test files extended)
**Analogs found:** 5 / 5 (all in-file / same-module analogs — both refactors collapse existing duplication, so the best analog for each new construct already lives beside it)

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `src/python/common/config.py` | config (model/registry) | transform (serialize/deserialize roundtrip) | `InnerConfig.as_dict` / `set_property` property-metadata iteration (same file, lines 183-218) | exact (in-file) |
| `src/python/seedsyncarr.py` | service (startup orchestration) | batch (per-field iteration) | existing `for attr, field, _ in _SECRET_FIELD_PATHS` loop (same file, line 413) | exact (in-file, repoint) |
| `src/python/web/handler/controller.py` | handler (controller/route) | request-response | the 5 near-identical `__handle_action_*` scaffolds (same file, lines 76-181) | exact (in-file dedup) |
| `tests/unittests/test_common/test_config.py` | test | transform | `_build_config_ini` + `TestConfig` Fernet roundtrip suite (same file) | exact (in-file) |
| `tests/unittests/test_web/test_handler/test_controller_handler.py` | test | request-response | `TestControllerHandlerSingleAction` (same file, lines 38-80) | exact (in-file) |

> Note: full test path roots are `src/python/tests/unittests/...` (the project's python source root is `src/python/`, and its tests live under `src/python/tests/`). Table abbreviates to `tests/...` for readability.

---

## Pattern Assignments

### ARCH-02 — `src/python/common/config.py` (config, transform)

**Analog:** the existing dynamic property-metadata discovery already in this file (`__prop_addon_map` + `PropMetadata`). ARCH-02 extends that *same* mechanism with a `secret` flag rather than inventing a new one. The hand-maintained `_SECRET_FIELD_PATHS` tuple (lines 19-25) is the duplication being removed.

**1. PropMetadata carrier to extend** (lines 130-146) — add a third `secret: bool` field, threaded through `_create_property` and the `PROP` alias:
```python
class PropMetadata:
    """Tracks property metadata"""
    def __init__(self, checker: Callable, converter: Callable):
        self.checker = checker
        self.converter = converter

@classmethod
def _create_property(cls, name: str, checker: Callable, converter: Callable) -> property:
    prop = property(fget=lambda s: s._get_property(name),
                    fset=lambda s, v: s._set_property(name, v, checker))
    prop_addon = InnerConfig.PropMetadata(checker=checker, converter=converter)
    InnerConfig.__prop_addon_map[prop] = prop_addon
    return prop
```
> D-01 mechanism: add `secret: bool = False` to `PropMetadata.__init__` and a `secret: bool = False` keyword to `_create_property`. `PROP = InnerConfig._create_property` (line 222) keeps working unchanged for non-secret callers; secret declarations become `PROP("api_token", Checkers.null, Converters.null, secret=True)`.

**2. The 5 secret PROP declarations to flag** (only these get `secret=True`):
```python
# General (lines 231-232)
webhook_secret = PROP("webhook_secret", Checkers.null, Converters.null, secret=True)
api_token      = PROP("api_token",      Checkers.null, Converters.null, secret=True)
# Lftp (line 248)
remote_password = PROP("remote_password", Checkers.string_nonempty, Converters.null, secret=True)
# Sonarr (line 324)
sonarr_api_key = PROP("sonarr_api_key", Checkers.null, Converters.null, secret=True)
# Radarr (line 335)
radarr_api_key = PROP("radarr_api_key", Checkers.null, Converters.null, secret=True)
```

**3. Discovery API — copy the metadata-iteration pattern from `as_dict`/`set_property`** (lines 183-218). This is the canonical in-file way to map a property object back to its name AND look up its `PropMetadata`. The new `secret_fields()` API must reproduce the *exact same 3-tuple shape* the tuple gave: `(inner_attr_name_on_Config, field_name, ini_section)`.

The two halves to combine:
```python
# (a) property-object -> field-name, ordered by creation — from as_dict (lines 188-196)
cls = self.__class__
my_property_to_name_map = {getattr(cls, p): p for p in dir(cls) if isinstance(getattr(cls, p), property)}
all_properties = InnerConfig.__prop_addon_map.keys()
for prop in all_properties:
    if prop in my_property_to_name_map.keys():
        name = my_property_to_name_map[prop]
        ...

# (b) property-object -> its PropMetadata — from set_property (line 214)
prop_addon = InnerConfig.__prop_addon_map[getattr(cls, name)]
# new: prop_addon.secret  -> bool
```
> **Section derivation (D-01).** The third tuple element (`ini_section`) is currently a string literal (`"General"`, `"Lftp"`, `"Sonarr"`, `"Radarr"`). D-01 requires deriving it *structurally* instead. The structural source of truth is `Config.as_dict` (lines 582-595): the `InnerConfig` subclass `General` maps to ini-section `"General"`, `Lftp`→`"Lftp"`, `Sonarr`→`"Sonarr"`, `Radarr`→`"Radarr"`. Note `attr` is lowercase (`"general"`) but `ini_section` is TitleCase (`"General"`) — these differ for the attr/section pair, so the API must still emit both. The owning `InnerConfig` subclass name == the ini-section name in every case, so `subclass.__name__` is the structural section key. Planner/researcher choose where to anchor the walk (a `Config`-level classmethod iterating `self.__dict__` inner configs, or an `InnerConfig`-level helper); whatever shape is chosen MUST yield the same five `(attr, field, ini_section)` triples the tuple yielded.

**4. Encrypt consumer to repoint** — `to_str`, lines 494-499. Replace `for (_, field_name, ini_section) in _SECRET_FIELD_PATHS:` with the new discovery API. Body of the loop (the encrypt-if-non-empty-plaintext logic) stays byte-identical:
```python
for (_, field_name, ini_section) in _SECRET_FIELD_PATHS:           # <- replace iterator only
    if ini_section in config_dict and field_name in config_dict[ini_section]:
        value = config_dict[ini_section][field_name]
        if value and not is_ciphertext(value):
            config_dict[ini_section][field_name] = encrypt_field(fernet_key, str(value))
```

**5. Decrypt consumers to repoint** — `from_str`, all three uses (lines 446, 451, 457). Same rule: swap the iterator, keep the loop body. The `has_existing_ciphertext` `any(...)` at line 444-447 and both `for (_, field_name, ini_section) in _SECRET_FIELD_PATHS:` loops (451, 457) must consume the new API:
```python
has_existing_ciphertext = any(
    is_ciphertext(config_dict.get(ini_section, {}).get(field_name, ""))
    for (_, field_name, ini_section) in _SECRET_FIELD_PATHS      # <- replace iterator only
)
```
> **Critical invariant (COMPAT):** the `[Encryption]` section's `enabled` flag is NOT a secret and must never be discovered (T-81-02-07). The `Encryption.enabled` PROP (line 355) must keep `secret=False` (the default) — verify it is never flagged.

**6. Remove the tuple** — delete lines 19-25 (`_SECRET_FIELD_PATHS = (...)`) and its comment block (lines 14-18). D-02: no same-named alias is kept.

---

### ARCH-02 — `src/python/seedsyncarr.py` (service, batch)

**Analog:** the existing `for attr, field, _ in _SECRET_FIELD_PATHS` loop is the only out-of-module consumer; repoint it to the new API. It unpacks the *first two* tuple elements (`attr`, `field`) and discards the section (`_`).

**Import to change** (line 18):
```python
from common.config import _SECRET_FIELD_PATHS          # <- remove
# becomes an import of the new discovery API, e.g.:
# from common import Config            (already imported, line 13) and call Config.secret_fields()
```

**Consumer loop to repoint** (`_reencrypt_plaintext_if_needed`, lines 412-417) — keep body identical, swap the iterable:
```python
for attr, field, _ in _SECRET_FIELD_PATHS:            # <- replace iterable with new API
    value = getattr(getattr(config, attr), field, None)
    if value and not is_ciphertext(value):
        has_plaintext = True
        break
```
> This consumer relies on `attr` being the *lowercase Config attribute* (`config.general`, `config.lftp`, `config.sonarr`, `config.radarr`) used via `getattr(getattr(config, attr), field)`, NOT the TitleCase ini-section. The new API must still return the lowercase attr as element 0 — this is exactly why D-01 keeps the full 3-tuple shape `(attr, field, ini_section)` rather than just `(field, section)`.

---

### ARCH-03 — `src/python/web/handler/controller.py` (handler, request-response)

**Analog:** the five `__handle_action_*` methods (lines 76-181) ARE each other's analog. Four of the five are byte-identical except (a) the `Controller.Command.Action.*` enum, (b) the success-body string, and (c) the presence/absence of the `_check_path_safe` guard. D-03 collapses the shared ~15-line scaffold into one `_dispatch_command` helper.

**The exact shared scaffold to extract** (canonical copy — `__handle_action_extract`, lines 119-135, which is the guarded variant):
```python
file_name = unquote(file_name)            # value is double encoded

guard = self._check_path_safe(file_name)  # GUARDED variant only (extract/delete_local/delete_remote)
if guard:
    return guard

command = Controller.Command(Controller.Command.Action.EXTRACT, file_name)
callback = WebResponseActionCallback()
command.add_callback(callback)
self.__controller.queue_command(command)
completed = callback.wait(timeout=self._ACTION_TIMEOUT)
if not completed:
    return HTTPResponse(body="Operation timed out", status=504)
if callback.success:
    return HTTPResponse(body="Requested extraction for file '{}'".format(file_name))
else:
    return HTTPResponse(body=callback.error, status=callback.error_code)
```

**The three per-handler variation points** (everything else is identical):
| Handler | lines | Action enum | success body | guard? |
|---------|-------|-------------|--------------|--------|
| `__handle_action_queue` | 76-93 | `QUEUE` | `"Queued file '{}'"` | no |
| `__handle_action_stop` | 95-112 | `STOP` | `"Stopped file '{}'"` | no |
| `__handle_action_extract` | 114-135 | `EXTRACT` | `"Requested extraction for file '{}'"` | **yes** |
| `__handle_action_delete_local` | 137-158 | `DELETE_LOCAL` | `"Requested local delete for file '{}'"` | **yes** |
| `__handle_action_delete_remote` | 160-181 | `DELETE_REMOTE` | `"Requested remote delete for file '{}'"` | **yes** |

**Target helper signature** (D-03 — exact name/positional-vs-keyword at planner discretion, but this captures the contract):
```python
def _dispatch_command(
    self,
    action: "Controller.Command.Action",
    file_name: str,
    success_msg: str,
    *,
    guard: bool = False,
) -> HTTPResponse:
    file_name = unquote(file_name)
    if guard:
        path_guard = self._check_path_safe(file_name)
        if path_guard:
            return path_guard
    command = Controller.Command(action, file_name)
    callback = WebResponseActionCallback()
    command.add_callback(callback)
    self.__controller.queue_command(command)
    if not callback.wait(timeout=self._ACTION_TIMEOUT):
        return HTTPResponse(body="Operation timed out", status=504)
    if callback.success:
        return HTTPResponse(body=success_msg.format(file_name))
    return HTTPResponse(body=callback.error, status=callback.error_code)
```
Each of the five public handlers shrinks to a one-liner delegate, e.g.:
```python
def __handle_action_queue(self, file_name: str) -> HTTPResponse:
    return self._dispatch_command(Controller.Command.Action.QUEUE, file_name, "Queued file '{}'")

def __handle_action_extract(self, file_name: str) -> HTTPResponse:
    return self._dispatch_command(
        Controller.Command.Action.EXTRACT, file_name,
        "Requested extraction for file '{}'", guard=True,
    )
```

**Behavior-preserving invariants the helper MUST keep exactly** (the regression contract):
- `unquote(file_name)` happens BEFORE the guard (matches current order, lines 119 then 121).
- 504 body is exactly `"Operation timed out"`; success bodies match the table above char-for-char.
- failure path returns `callback.error` with `callback.error_code` (default 400, set by `WebResponseActionCallback`, lines 31/36).
- `_ACTION_TIMEOUT = 30.0` (line 184) is referenced via `self._ACTION_TIMEOUT` so the test's monkeypatch (`ControllerHandler._ACTION_TIMEOUT = 0.1`) still works.

> `self.__controller` is name-mangled to `self._ControllerHandler__controller`; calling it from `_dispatch_command` (still inside the class) is fine — keep using `self.__controller`.

**EXPLICITLY OUT OF SCOPE — do NOT touch:**
- `__handle_bulk_command` (lines 227-332) and `_process_bulk_commands` (lines 334-448) stay byte-identical (D-03 / deferred). The bulk path has its own parallel-queue + per-file-timeout + partial-failure semantics and its own guard handling via `_GUARDED_ACTIONS` (lines 196-200) — it must NOT be routed through `_dispatch_command`.
- `add_routes` registration (lines 65-74) is unchanged — the five public `__handle_action_*` method names stay the same, only their bodies delegate.

---

## Shared Patterns

### `@overrides` decorator convention
**Source:** `src/python/common/types.py` (imported as `from common import overrides`, used in controller.py lines 12, 33, 40, 64)
**Apply to:** any method that implements an interface (`IHandler.add_routes`, `Persist.from_str`/`to_str`). Neither refactor adds new interface methods, but the existing `@overrides(Persist)` on `from_str`/`to_str` (config.py lines 404, 477) must be preserved when their loop bodies are edited.

### Property-metadata iteration (ARCH-02 backbone)
**Source:** `src/python/common/config.py` lines 188-196 (`as_dict`) and 214 (`set_property`)
**Apply to:** the new `secret_fields()` discovery API. This is the ONLY established in-codebase pattern for "given an `InnerConfig` subclass, enumerate its properties in declaration order and look up each property's `PropMetadata`." Reuse it rather than introducing a registry/scan-by-name approach.

### `HTTPResponse` status/body contract (ARCH-03 backbone)
**Source:** `src/python/web/handler/controller.py` — the five handlers themselves
**Apply to:** `_dispatch_command`. Status codes (200 / 504 / `callback.error_code`) and body strings are the public API the integration test (`test_controller.py`) and unit test (`test_controller_handler.py`) assert against. Treat them as frozen.

---

## Test Patterns (regression net + new declarative-discovery test)

### ARCH-02 regression + new test — `tests/unittests/test_common/test_config.py`
**Scaffold to reuse:** `_build_config_ini(...)` (lines 12-87) — parameterizes the 5 secret fields into a full INI skeleton; and `TestConfig.setUp` keyfile injection pattern (lines 181-183):
```python
self.keyfile = os.path.join(self.temp_dir, "secrets.key")
Config.set_keyfile_path(self.keyfile)
self.addCleanup(Config.set_keyfile_path, None)
```
**New test (ARCH-02 success criterion #2 — "a new `secret=True` field is auto-discovered without touching other files"):** Define a throwaway `InnerConfig` subclass (analog: `DummyInnerConfig` / `DummyInnerConfig2`, lines 127-144) that declares one `PROP(..., secret=True)`, then assert the discovery API surfaces exactly that field — proving discovery is structural, not list-driven. Shape at planner discretion (D — Claude's Discretion).
**Roundtrip guarantee:** existing encrypt/decrypt/redact tests (the Phase 81 Fernet suite in `TestConfig`) must stay green unmodified — they are the proof the same 5 fields are still covered after the tuple is removed.

### ARCH-03 regression — `tests/unittests/test_web/test_handler/test_controller_handler.py`
**Scaffold to reuse:** `TestControllerHandlerSingleAction` (lines 38-80). Note the private-method call convention via name-mangling (line 45):
```python
return self.handler._ControllerHandler__handle_action_queue(file_name)
```
and the timeout-override pattern (lines 56-66) that monkeypatches `ControllerHandler._ACTION_TIMEOUT`. Because `add_routes` and the public handler names are unchanged, these tests should pass without edits — that is the behavior-preserving proof. The integration suite `tests/integration/test_web/test_handler/test_controller.py` covers the full single + bulk HTTP paths (per CONCERNS.md) and is the outer regression net.

---

## No Analog Found

None. Both refactors collapse or extend duplication that already exists in the target files, so every new construct has an exact in-file analog. The planner should prefer these in-file patterns over any generic examples in RESEARCH.md.

---

## Metadata

**Analog search scope:** `src/python/common/`, `src/python/web/handler/`, `src/python/seedsyncarr.py`, `src/python/tests/unittests/test_common/`, `src/python/tests/unittests/test_web/test_handler/`, `src/python/tests/integration/test_web/test_handler/`
**Files scanned:** 3 source targets read in full + 2 test files (scaffold sections); `_SECRET_FIELD_PATHS` and `PropMetadata`/`__prop_addon_map` consumer grep across `src` + `tests` (worktrees excluded)
**Confirmed consumer count:** `_SECRET_FIELD_PATHS` has exactly 2 consuming modules — `config.py` (encrypt + decrypt) and `seedsyncarr.py` (startup re-encrypt). No web-layer or test reference. (CONTEXT.md integration-points claim verified.)
**Pattern extraction date:** 2026-06-01
