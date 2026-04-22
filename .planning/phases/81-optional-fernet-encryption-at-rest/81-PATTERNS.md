# Phase 81: Optional Fernet Encryption at Rest - Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 8 (4 new/widened source, 3 new/widened test, 1 doc)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/python/common/encryption.py` | utility (crypto primitive + file I/O) | file-I/O + transform | `src/python/common/persist.py` (0600 chmod + file write) and `src/python/common/error.py` (AppError subclass) | role-match |
| `src/python/common/config.py` (widen) | model (config registry) + transform | serialization seam | `src/python/common/config.py` existing `Config.Sonarr` / `AutoDelete` section class + `Config.from_str` / `to_str` / `from_dict` | exact (self-analog) |
| `src/python/seedsyncarr.py` (widen) | entry-point orchestrator | startup hook | `src/python/seedsyncarr.py` existing `_emit_startup_warnings` + `_create_default_config` + `persist()` | exact (self-analog) |
| `src/python/pyproject.toml` (widen) | config | dependency declaration | existing dual `[project.dependencies]` + `[tool.poetry.dependencies]` blocks | exact (self-analog) |
| `src/python/tests/unittests/test_common/test_encryption.py` | test (unit) | test fixture + assert | `src/python/tests/unittests/test_common/test_persist.py` (tempfile/shutil setUp/tearDown, 0600 perm assertion) | exact |
| `src/python/tests/unittests/test_common/test_config.py` (widen) | test (unit) | test fixture + assert | `src/python/tests/unittests/test_common/test_config.py` existing `test_general` / `test_from_file` / `test_to_file` | exact (self-analog) |
| `src/python/tests/unittests/test_seedsyncarr.py` (widen) | test (unit) | mock + assert | `src/python/tests/unittests/test_seedsyncarr.py` existing `TestSeedsyncarrStartupWarnings` class | exact (self-analog) |
| `docs/CONFIGURATION.md` (widen) | doc | prose + INI example | `docs/CONFIGURATION.md` existing structure (section-per-INI-section + table) | exact (self-analog) |

## Pattern Assignments

### `src/python/common/encryption.py` (NEW — utility, file-I/O + transform)

**Primary analog:** `src/python/common/persist.py` (0600 chmod + file I/O)
**Secondary analog:** `src/python/common/error.py` (AppError subclass pattern for a domain-specific exception)

**Imports pattern** — follow the minimal stdlib-first style from `persist.py:1-6`:

```python
# src/python/common/persist.py:1-6
import os
from abc import ABC, abstractmethod
from typing import Type, TypeVar

from .error import AppError
from .localization import Localization
```

Applied to encryption.py: `import os`, `import base64`, then `from cryptography.fernet import Fernet, InvalidToken`, then `from .error import AppError` for the `DecryptionError` subclass.

**Error-class pattern** — `AppError` subclass with docstring-only body, per `persist.py:26-30`:

```python
# src/python/common/persist.py:26-30
class PersistError(AppError):
    """
    Exception indicating persist loading/saving error
    """
    pass
```

Applied to encryption.py: `class DecryptionError(AppError): """Raised when a Fernet token cannot be decrypted."""`.

**0600 file-write pattern** — `persist.py:47-50` (copy exactly; this is the in-codebase convention — write first, then chmod):

```python
# src/python/common/persist.py:47-50
def to_file(self, file_path: str):
    with open(file_path, "w") as f:
        f.write(self.to_str())
    os.chmod(file_path, 0o600)  # restrict to owner read/write only
```

**0600 tighten-on-read pattern** — `persist.py:40-45` (use this form for the keyfile-exists branch of `load_or_create_key` so existing keyfiles get re-tightened on every load):

```python
# src/python/common/persist.py:40-45
@classmethod
def from_file(cls: Type[T_Persist], file_path: str) -> T_Persist:
    if not os.path.isfile(file_path):
        raise AppError(Localization.Error.MISSING_FILE.format(file_path))
    os.chmod(file_path, 0o600)  # tighten permissions on existing files
    with open(file_path, "r") as f:
        return cls.from_str(f.read())
```

**Note on atomic-create tightening:** The research (Section 9.2) recommends `os.open(..., os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)` for the first-time-create path — this is STRICTER than `persist.py`'s write-then-chmod, which is correct for a keyfile because the keyfile must never exist at looser perms even for a single syscall window. Use the atomic form for create, match `persist.py` for read-tighten.

**Public surface to export** (add to `src/python/common/__init__.py` only if callers outside `common` need them; RESEARCH §4 says only `config.py` and `seedsyncarr.py` call into it — so re-export is optional):

- `load_or_create_key(keyfile_path: str) -> bytes`
- `is_ciphertext(s: str) -> bool`
- `encrypt_field(key: bytes, plaintext: str) -> str`
- `decrypt_field(key: bytes, token: str) -> str` (raises `DecryptionError` on `InvalidToken`)
- `DecryptionError` (AppError subclass)

---

### `src/python/common/config.py` (WIDEN — model + transform, serialization seam)

**Primary analog:** `config.py` itself — the existing `Sonarr` / `Radarr` / `AutoDelete` inner classes and the `from_dict` backward-compat branches.

**Inner-class pattern** — copy from `config.py:323-332` (AutoDelete is the closest template because its first field is also `enabled: bool`):

```python
# src/python/common/config.py:323-332
class AutoDelete(IC):
    enabled = PROP("enabled", Checkers.null, Converters.bool)
    dry_run = PROP("dry_run", Checkers.null, Converters.bool)
    delay_seconds = PROP("delay_seconds", Checkers.int_positive, Converters.int)

    def __init__(self):
        super().__init__()
        self.enabled = None
        self.dry_run = None
        self.delay_seconds = None
```

Applied to `Config.Encryption`: single field `enabled` using `Checkers.null` + `Converters.bool`, `__init__` sets `self.enabled = None`. Do NOT add a keyfile-path field — RESEARCH §A1 says path is fixed at `{config_dir}/secrets.key`.

**Register in `Config.__init__`** — follow `config.py:334-342`:

```python
# src/python/common/config.py:334-342
def __init__(self):
    self.general = Config.General()
    self.lftp = Config.Lftp()
    self.controller = Config.Controller()
    self.web = Config.Web()
    self.autoqueue = Config.AutoQueue()
    self.sonarr = Config.Sonarr()
    self.radarr = Config.Radarr()
    self.autodelete = Config.AutoDelete()
```

Add `self.encryption = Config.Encryption()` at the bottom.

**Backward-compatible optional-section pattern** — `config.py:429-438` (this is the canonical pattern for `enabled = False` default when the INI section is missing):

```python
# src/python/common/config.py:429-438
# AutoDelete section is optional for backward compatibility
if "AutoDelete" in config_dict:
    config.autodelete = Config.AutoDelete.from_dict(
        Config._check_section(config_dict, "AutoDelete")
    )
else:
    # Default values for existing installs missing [AutoDelete] section
    config.autodelete.enabled = False
    config.autodelete.dry_run = False
    config.autodelete.delay_seconds = 60
```

Applied to `[Encryption]` in `Config.from_dict`: single-field default `config.encryption.enabled = False`. This directly satisfies SEC-02 criterion #3 (backward compat).

**Register in `as_dict`** — follow `config.py:443-455`:

```python
# src/python/common/config.py:443-455
def as_dict(self) -> OuterConfigType:
    config_dict = collections.OrderedDict()
    config_dict["General"] = self.general.as_dict()
    config_dict["Lftp"] = self.lftp.as_dict()
    config_dict["Controller"] = self.controller.as_dict()
    config_dict["Web"] = self.web.as_dict()
    config_dict["AutoQueue"] = self.autoqueue.as_dict()
    config_dict["Sonarr"] = self.sonarr.as_dict()
    config_dict["Radarr"] = self.radarr.as_dict()
    config_dict["AutoDelete"] = self.autodelete.as_dict()
    return config_dict
```

Add `config_dict["Encryption"] = self.encryption.as_dict()` at the bottom.

**Serialization seam — existing `from_str`** (widen at `config.py:358-376`):

```python
# src/python/common/config.py:358-376
@classmethod
@overrides(Persist)
def from_str(cls: "Config", content: str) -> "Config":
    config_parser = configparser.ConfigParser()
    try:
        config_parser.read_string(content)
    except (
            configparser.MissingSectionHeaderError,
            configparser.ParsingError
    ) as e:
        raise PersistError("Error parsing Config - {}: {}".format(
            type(e).__name__, str(e))
        )
    config_dict = {}
    for section in config_parser.sections():
        config_dict[section] = {}
        for option in config_parser.options(section):
            config_dict[section][option] = config_parser.get(section, option)
    return Config.from_dict(config_dict)
```

**Decrypt hook location:** After the `config_dict` is fully built (after line 375) and BEFORE `Config.from_dict`. Peek at `config_dict.get("Encryption", {}).get("enabled", "False")` with `_strtobool` (`config.py:12-26` existing helper). If enabled AND the class-level `_keyfile_path` is set, load key via `load_or_create_key` and walk the 5 `_SECRET_FIELD_PATHS` — for each, if `is_ciphertext(value)` then `decrypt_field(key, value)`; else leave plaintext (plaintext fallback for the "existing install with flag newly enabled" case).

**Serialization seam — existing `to_str`** (widen at `config.py:378-389`):

```python
# src/python/common/config.py:378-389
@overrides(Persist)
def to_str(self) -> str:
    config_parser = configparser.ConfigParser()
    config_dict = self.as_dict()
    for section in config_dict:
        config_parser.add_section(section)
        section_dict = config_dict[section]
        for key in section_dict:
            config_parser.set(section, key, str(section_dict[key]))
    str_io = StringIO()
    config_parser.write(str_io)
    return str_io.getvalue()
```

**Encrypt hook location:** Right after `config_dict = self.as_dict()` (line 381), before the section-loop. If `self.encryption.enabled` is True AND the class-level `_keyfile_path` is set, load key and walk the 5 `_SECRET_FIELD_PATHS`. For each non-empty value that is NOT already ciphertext, replace with `encrypt_field(key, value)`. Leave empty strings unchanged (research §6.3: "only encrypt non-empty").

**Keyfile-path injection** (new classmethod on `Config` — RESEARCH §9.3 + §A2 prefer this over widening `Persist.from_file`):

```python
# NEW — add to Config class (no existing analog; simplest pattern)
_keyfile_path: Optional[str] = None  # class-level, set before any from_file/to_file

@classmethod
def set_keyfile_path(cls, path: str) -> None:
    cls._keyfile_path = path
```

**Module-level constant** (new — place near the top of `config.py` after `_strtobool`):

```python
# NEW module-level tuple listing the 5 secret field paths
# Format: (inner_attr_name, inner_field_name, ini_section_name)
# The ini_section_name is needed because from_str operates on config_dict
# which is keyed by INI section name (TitleCase), not attr name (lowercase).
_SECRET_FIELD_PATHS = (
    ("general", "webhook_secret", "General"),
    ("general", "api_token", "General"),
    ("lftp", "remote_password", "Lftp"),
    ("sonarr", "sonarr_api_key", "Sonarr"),
    ("radarr", "radarr_api_key", "Radarr"),
)
```

**Key helper pattern already in file** — `_strtobool` at `config.py:12-26` is the existing precedent for a module-level helper function. Match its structure (lowercase, leading underscore, full docstring).

---

### `src/python/seedsyncarr.py` (WIDEN — entry-point, startup hook)

**Primary analog:** `seedsyncarr.py` itself.

**Keyfile path injection — location** — `seedsyncarr.py:41-45` (the existing pre-`from_file` block):

```python
# src/python/seedsyncarr.py:41-45
self.config_path = os.path.join(args.config_dir, Seedsyncarr.__FILE_CONFIG)
create_default_config = False
if os.path.isfile(self.config_path):
    try:
        config = Config.from_file(self.config_path)
```

**Insert before the `if os.path.isfile(...)` check:**

```python
# NEW
Config.set_keyfile_path(os.path.join(args.config_dir, "secrets.key"))
```

Add a new module-level class constant next to line 27-29 for discoverability:

```python
# Existing src/python/seedsyncarr.py:27-30
__FILE_CONFIG = "settings.cfg"
__FILE_AUTO_QUEUE_PERSIST = "autoqueue.persist"
__FILE_CONTROLLER_PERSIST = "controller.persist"
__CONFIG_DUMMY_VALUE = "<replace me>"
```

Add: `__FILE_SECRETS_KEY = "secrets.key"`.

**Re-encrypt-on-startup hook** — follow the `_emit_startup_warnings` invocation pattern at `seedsyncarr.py:110-111` (static helper called from `run()`):

```python
# src/python/seedsyncarr.py:110-111
# Startup security warnings (WHOOK-02, WARN-01, WARN-02, WARN-03)
Seedsyncarr._emit_startup_warnings(self.context.logger, self.context.config)
```

**Recommended placement:** Inside `__init__`, AFTER `Config.from_file` succeeds (around line 46) and BEFORE `_create_default_config`. This matches RESEARCH §9.4. The hook needs access to `self.context.config` (decrypted in-memory) AND `self.config_path` (to re-write). It runs before the logger is set up — so log via `print` or defer until after logger setup. The cleaner path: put it AFTER logger setup (~line 73), symmetric with `_emit_startup_warnings` which also runs after logger setup.

**Defaults extension** — `_create_default_config` at `seedsyncarr.py:340-342` (the tail of the method):

```python
# src/python/seedsyncarr.py:340-342
config.autodelete.enabled = False
config.autodelete.dry_run = False
config.autodelete.delay_seconds = 60

return config
```

Insert before `return config`: `config.encryption.enabled = False` — this is CRITICAL per RESEARCH Pitfall 8.6 (prevents default-value drift in existing tests that build a Config in Python).

**Startup-warnings pattern for decrypt failure** — mirror `_emit_startup_warnings` at `seedsyncarr.py:355-376`:

```python
# src/python/seedsyncarr.py:355-376
@staticmethod
def _emit_startup_warnings(logger, config) -> None:
    """Emit security warnings for insecure configuration states."""
    if not config.general.webhook_secret:
        logger.warning(
            "Security: webhook_secret is not configured. "
            "Webhook endpoints will accept requests from any caller."
        )
    if not config.general.api_token:
        logger.warning(
            "Security: No API token configured. "
            "All API requests will be accepted without authentication."
        )
        logger.warning(
            "Security: Application is bound to 0.0.0.0 without an API token. "
            "Any host on the network can access the API."
        )
    else:
        logger.info(
            "Security: API token configured — "
            "all /server/* endpoints require Bearer authentication."
        )
```

**Applied:** Either (a) extend `_emit_startup_warnings` with decrypt-failure branches, OR (b) add a sibling static method `_emit_decrypt_warnings(logger, config, decrypt_errors)` called immediately after. Approach (b) is cleaner because the decrypt error list must be collected during `from_str` and plumbed through — add a new instance attr on `Config` like `self._decrypt_errors: list[str] = []`, populated inside `from_str` when `is_ciphertext(v) is True` but `decrypt_field` raises `DecryptionError`. After logger is set up in `__init__`, iterate `self.context.config._decrypt_errors` and emit one `logger.warning(...)` per entry.

**Periodic-persist path** — `seedsyncarr.py:212-217` (UNCHANGED; the encrypt-on-write happens transparently via the seam):

```python
# src/python/seedsyncarr.py:212-217
def persist(self):
    # Save the persists
    self.context.logger.debug("Persisting states to file")
    self.controller_persist.to_file(self.controller_persist_path)
    self.auto_queue_persist.to_file(self.auto_queue_persist_path)
    self.context.config.to_file(self.config_path)
```

No change needed — `config.to_file` -> `Persist.to_file` -> `Config.to_str` which now encrypts. The 0600 chmod in `persist.py:50` still applies to `settings.cfg`.

---

### `src/python/pyproject.toml` (WIDEN)

**Primary analog:** `pyproject.toml` itself. The project has the dual-declaration quirk called out in RESEARCH §5.

**Pattern for new dep** — add to BOTH lists. Existing `[project.dependencies]` at lines 11-20:

```toml
# src/python/pyproject.toml:11-20
dependencies = [
    "bottle>=0.13.4",
    "paste>=3.10.1",
    "patool>=4.0.3",
    "pexpect>=4.9.0",
    "pytz>=2025.2",
    "requests>=2.33.0",
    "tblib>=3.2.2",
    "timeout-decorator>=0.5.0",
]
```

Add: `"cryptography>=44.0.0,<47",` (alphabetical insertion between `bottle` and `paste`? — existing list is NOT alphabetical, just preserves addition order; safest to append at bottom to match project convention).

Existing `[tool.poetry.dependencies]` at lines 49-58:

```toml
# src/python/pyproject.toml:49-58
[tool.poetry.dependencies]
python = ">=3.11,<3.13"
bottle = "^0.13.4"
paste = "^3.10.1"
patool = "^4.0.3"
pexpect = "^4.9.0"
pytz = ">=2025.2,<2027.0"
requests = "^2.33.0"
tblib = "^3.2.2"
timeout-decorator = "^0.5.0"
```

Add: `cryptography = ">=44.0.0,<47"` (note: poetry uses `=` and PEP 440 specifier, not caret, to match RESEARCH's `>=44,<47` range semantics — caret `^44` would forbid 45.x and 46.x which we explicitly want).

**Regenerate `poetry.lock`** after edit — this is a side effect; no pattern to copy but document the step in the plan.

---

### `src/python/tests/unittests/test_common/test_encryption.py` (NEW — unit tests)

**Primary analog:** `src/python/tests/unittests/test_common/test_persist.py` (tempfile + shutil setUp/tearDown + 0600 permission assertion).

**setUp / tearDown pattern** — `test_persist.py:25-34`:

```python
# src/python/tests/unittests/test_common/test_persist.py:25-34
class TestPersist(unittest.TestCase):
    @overrides(unittest.TestCase)
    def setUp(self):
        # Create a temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="test_persist")

    @overrides(unittest.TestCase)
    def tearDown(self):
        # Cleanup
        shutil.rmtree(self.temp_dir)
```

Applied: `self.temp_dir = tempfile.mkdtemp(prefix="test_encryption")`, `self.keyfile = os.path.join(self.temp_dir, "secrets.key")` — same shutil.rmtree cleanup.

**0600 permission assertion** — `test_persist.py:70-76`:

```python
# src/python/tests/unittests/test_common/test_persist.py:70-76
def test_to_file_sets_0600_permissions(self):
    file_path = os.path.join(self.temp_dir, "persist_perms")
    persist = DummyPersist()
    persist.my_content = "sensitive content"
    persist.to_file(file_path)
    mode = os.stat(file_path).st_mode & 0o777
    self.assertEqual(0o600, mode, f"Expected 0600 permissions, got {oct(mode)}")
```

Applied: `test_keyfile_is_0600` — call `load_or_create_key(self.keyfile)`, then `mode = os.stat(self.keyfile).st_mode & 0o777`, then `assertEqual(0o600, mode, ...)`. Gate with `@unittest.skipIf(sys.platform == "win32", "POSIX permission bits only")` per RESEARCH Pitfall 8.3.

**Import pattern** — `test_persist.py:1-6`:

```python
# src/python/tests/unittests/test_common/test_persist.py:1-6
import unittest
import tempfile
import shutil
import os

from common import overrides, Persist, AppError, Localization
```

Applied: `import unittest, tempfile, shutil, os, sys`; `from common.encryption import load_or_create_key, is_ciphertext, encrypt_field, decrypt_field, DecryptionError`.

**Tighten-on-read assertion** — `test_persist.py:78-85` (directly applies to `load_or_create_key` when keyfile already exists with 0644):

```python
# src/python/tests/unittests/test_common/test_persist.py:78-85
def test_from_file_tightens_permissive_permissions(self):
    file_path = os.path.join(self.temp_dir, "persist_tighten")
    with open(file_path, "w") as f:
        f.write("some content")
    os.chmod(file_path, 0o644)
    DummyPersist.from_file(file_path)
    mode = os.stat(file_path).st_mode & 0o777
    self.assertEqual(0o600, mode, f"Expected 0600 permissions after from_file(), got {oct(mode)}")
```

Applied: `test_load_tightens_existing_keyfile_permissions` — pre-create keyfile at 0644, call `load_or_create_key`, assert re-tightened to 0600.

**Test list** (from RESEARCH §9.5, matched to criteria):
- `test_key_generated_on_first_call` — first call creates keyfile, returns 44-byte key.
- `test_keyfile_is_0600` — POSIX permission gate.
- `test_load_tightens_existing_keyfile_permissions` — existing 0644 keyfile is re-tightened.
- `test_round_trip` — encrypt then decrypt returns the original plaintext.
- `test_is_ciphertext_rejects_plaintext` — empty, short, wrong-prefix, and long-but-not-b64 all return False.
- `test_is_ciphertext_accepts_real_token` — real Fernet token returns True.
- `test_decrypt_wrong_key_raises_decryption_error` — simulate keyfile loss.
- `test_decrypt_garbage_token_raises_decryption_error` — feed b64 garbage to `decrypt_field`.

---

### `src/python/tests/unittests/test_common/test_config.py` (WIDEN — 5 new test methods)

**Primary analog:** `test_config.py` itself.

**Builder pattern for a full `Config` instance** — `test_config.py:479-521` (the existing `test_to_file` is the canonical builder — copy its structure as a helper if repetition grows, but for 5 tests it's acceptable to inline):

```python
# src/python/tests/unittests/test_common/test_config.py:479-521 (abridged)
def test_to_file(self):
    config_file_path = tempfile.NamedTemporaryFile(suffix="test_config", delete=False).name

    config = Config()
    config.general.debug = True
    config.general.verbose = False
    config.general.webhook_secret = ""
    config.general.api_token = ""
    # ... 30 more lines populating all fields ...
    config.autodelete.enabled = False
    config.autodelete.dry_run = True
    config.autodelete.delay_seconds = 60
    config.to_file(config_file_path)
```

**CRITICAL:** Every existing test that builds a `Config()` in Python (not via `from_str`) MUST also set `config.encryption.enabled = False` — OR the default in `_create_default_config` must propagate via a fresh `Config()` constructor default. Per RESEARCH Pitfall 8.6, set the default to `False` in `Config.Encryption.__init__` via `self.enabled = None` (matching the AutoDelete pattern at `config.py:328-332`) AND in `Config.from_dict` backward-compat branch. Any test that hits `Config.to_str` on a raw `Config()` will need `config.encryption.enabled = False` explicitly.

**Golden-string pattern for `to_file`** — `test_config.py:526-580`:

```python
# src/python/tests/unittests/test_common/test_config.py:526-580 (abridged)
golden_str = """
[General]
debug = True
verbose = False
webhook_secret =
api_token =
...
[AutoDelete]
enabled = False
dry_run = True
delay_seconds = 60
"""

golden_lines = [s.strip() for s in golden_str.splitlines()]
golden_lines = list(filter(None, golden_lines))  # remove blank lines
actual_lines = [s.strip() for s in actual_str.splitlines()]
actual_lines = list(filter(None, actual_lines))
self.assertEqual(len(golden_lines), len(actual_lines))
for i, _ in enumerate(golden_lines):
    self.assertEqual(golden_lines[i], actual_lines[i])
```

**Impact:** The existing `test_to_file` MUST be updated to include `[Encryption]\nenabled = False` in the golden string, since `as_dict` will now include it (`config.py:443` change above).

**Backward-compat pattern** — borrow from `test_from_file` at `test_config.py:390-430`: a config string WITHOUT the new section and assert the default is applied. This is the precedent for the new `test_encryption_disabled_by_default` test.

**New test methods** (one per SEC-02 success criterion, placed in `TestConfig`):

| Test method | Criterion | Pattern to copy |
|-------------|-----------|-----------------|
| `test_encryption_disabled_by_default` | #3 backward compat | `test_from_file` body (INI without `[Encryption]` section, assert `config.encryption.enabled == False`) |
| `test_enable_new_install_encrypts_on_write` | #1 first-enable encrypts | `test_to_file` body (build Config, set flag, call `to_file`, read back, assert values start with `gAAAAA`). Requires `Config.set_keyfile_path(...)` call with a tempfile path in `setUp`. |
| `test_enable_existing_plaintext_reencrypts` | #3 startup re-encrypt | Build INI with `enabled=True` + plaintext secrets, call `from_str` → assert plaintext is preserved in memory; call `to_str` → assert values now encrypted. |
| `test_from_file_enabled_decrypts` | #2 transparent decrypt | `test_from_file` structure — write INI with `[Encryption] enabled=True` and already-encrypted values (produced via `encrypt_field` in the test setUp), call `Config.from_file`, assert the 5 fields come out plaintext. |
| `test_disable_restores_plaintext` | #4 round-trip | Encrypt → flip flag off → `to_str` → assert plaintext in output. |

**Keyfile tempfile handling in setUp** — no direct analog; create an ad-hoc pattern:

```python
# NEW setUp / tearDown for encryption-aware tests (add to TestConfig or new TestConfigEncryption class)
def setUp(self):
    self.temp_dir = tempfile.mkdtemp(prefix="test_config_enc")
    self.keyfile = os.path.join(self.temp_dir, "secrets.key")
    Config.set_keyfile_path(self.keyfile)

def tearDown(self):
    Config.set_keyfile_path(None)  # reset class state between tests
    shutil.rmtree(self.temp_dir)
```

Class-level state on `Config._keyfile_path` is a shared-mutable-state hazard in test isolation — reset in tearDown to `None` (the default).

---

### `src/python/tests/unittests/test_seedsyncarr.py` (WIDEN — 1 new test method)

**Primary analog:** `TestSeedsyncarrStartupWarnings` class at `test_seedsyncarr.py:193-255`.

**Mock-based warning-emission assertion** — `test_seedsyncarr.py:202-210`:

```python
# src/python/tests/unittests/test_seedsyncarr.py:202-210
def test_startup_warns_when_webhook_secret_empty(self):
    mock_logger = MagicMock()
    mock_config = self._make_mock_config(webhook_secret="", api_token="configured")
    Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
    warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
    self.assertTrue(
        any("webhook_secret" in call for call in warning_calls),
        msg="Expected a warning containing 'webhook_secret'"
    )
```

**Mock-config helper** — `test_seedsyncarr.py:196-200`:

```python
# src/python/tests/unittests/test_seedsyncarr.py:196-200
def _make_mock_config(self, webhook_secret="", api_token=""):
    mock_config = MagicMock()
    mock_config.general.webhook_secret = webhook_secret
    mock_config.general.api_token = api_token
    return mock_config
```

**New test:** `test_decrypt_failure_emits_warning` — follow the exact same shape. Populate a mock config with a `_decrypt_errors` list (e.g. `["general.api_token"]`), call `Seedsyncarr._emit_startup_warnings` (or the new sibling method), assert a warning was logged mentioning the field name.

**Do-not-raise assertion** — `test_seedsyncarr.py:250-255`:

```python
# src/python/tests/unittests/test_seedsyncarr.py:250-255
def test_startup_warnings_do_not_raise(self):
    """Warnings are advisory only — no exception should be raised (WARN-03)."""
    mock_logger = MagicMock()
    mock_config = self._make_mock_config(webhook_secret="", api_token="")
    # Must not raise
    Seedsyncarr._emit_startup_warnings(mock_logger, mock_config)
```

Applied: `test_decrypt_warning_does_not_raise` — decrypt warnings must NEVER crash startup (criterion #5).

---

### `docs/CONFIGURATION.md` (WIDEN)

**Primary analog:** `docs/CONFIGURATION.md` itself.

**Section-table pattern** — `CONFIGURATION.md:74-82` (General) and `CONFIGURATION.md:144-149` (AutoDelete):

```markdown
### [General]

| Setting | Required | Default | Description |
|---|---|---|---|
| `debug` | Optional | `False` | Enable verbose debug logging. |
| `verbose` | Optional | `False` | Enable extra verbose output. |
| `webhook_secret` | Optional | _(empty)_ | HMAC-SHA256 secret for verifying incoming webhook signatures. ... |
```

**Apply to new `[Encryption]` section:**

```markdown
### [Encryption]

| Setting | Required | Default | Description |
|---|---|---|---|
| `enabled` | Optional | `False` | When `True`, the five secret fields (`webhook_secret`, `api_token`, `remote_password`, `sonarr_api_key`, `radarr_api_key`) are encrypted at rest in `settings.cfg` using Fernet (AES-128-CBC + HMAC-SHA256). A keyfile is created at `<config_dir>/secrets.key` with 0600 permissions on first enable. **The keyfile is critical — back it up alongside `settings.cfg`.** Losing it makes the encrypted secrets unrecoverable. |
```

**INI example pattern** — `CONFIGURATION.md:12-66` (the existing full-file INI block). Add an `[Encryption]` section at the end of the example.

**New subsection — keyfile ops notes** (no direct analog in existing docs; follows the style of the `allowed_hostname` description paragraph at `CONFIGURATION.md:82`):

- State that `secrets.key` must be backed up.
- State that rotating/deleting `secrets.key` without disabling encryption first will result in unrecoverable secrets.
- State that `enabled = False` restores plaintext on next write.
- State that flipping the flag should be done with the app stopped (RESEARCH Pitfall 8.5 UX note).

---

## Shared Patterns

### 0600 File Permissions

**Source:** `src/python/common/persist.py:43` (on read) and `:50` (on write)
**Apply to:** `encryption.py` keyfile write/read paths. Match the write-then-chmod idiom exactly for load-existing; use stricter `os.open(..., O_EXCL, 0o600)` for first-create per RESEARCH §9.2.

```python
# src/python/common/persist.py:43, 50
os.chmod(file_path, 0o600)  # tighten permissions on existing files
# ... and ...
os.chmod(file_path, 0o600)  # restrict to owner read/write only
```

### AppError Subclass for Domain Exceptions

**Source:** `src/python/common/persist.py:26-30` (PersistError) and `src/python/common/config.py:28-32` (ConfigError)
**Apply to:** `encryption.py` `DecryptionError`. Single pass docstring body, inherit from `AppError`:

```python
# src/python/common/config.py:28-32
class ConfigError(AppError):
    """
    Exception indicating a bad config value
    """
    pass
```

### Backward-Compatible Optional INI Section (enabled=False default)

**Source:** `src/python/common/config.py:429-438` (AutoDelete)
**Apply to:** `Config.from_dict` handling of `[Encryption]`. Default `enabled = False` is mandatory for SEC-02 criterion #3.

### Static-Helper Style for Startup-Side-Effects

**Source:** `src/python/seedsyncarr.py:355-376` (`_emit_startup_warnings`)
**Apply to:** decrypt-failure warning emission in `seedsyncarr.py`. Either extend `_emit_startup_warnings` or add a sibling static method with the same signature `(logger, config) -> None`. Bounded side effects: log only, never raise.

### Mock-Logger-based Warning Assertion

**Source:** `src/python/tests/unittests/test_seedsyncarr.py:202-210` (TestSeedsyncarrStartupWarnings)
**Apply to:** new `test_decrypt_failure_emits_warning`. Use `MagicMock()` for logger, inspect `mock_logger.warning.call_args_list`, assert substring presence.

### Tempfile + shutil.rmtree setUp/tearDown Isolation

**Source:** `src/python/tests/unittests/test_common/test_persist.py:25-34`
**Apply to:** `test_encryption.py` (all tests) and the encryption-aware tests in `test_config.py`. Include tearDown reset of class-level `Config._keyfile_path` to avoid test pollution.

### `_strtobool` for INI-flag Parsing

**Source:** `src/python/common/config.py:12-26`
**Apply to:** reading `[Encryption].enabled` as a raw string out of the parsed `config_dict` before `Config.from_dict` runs. Use the existing helper verbatim — do NOT import `distutils.util.strtobool` (removed in Python 3.12).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | | | Every file has at least a role-match analog in the existing codebase. |

Notable "partial analog" callouts:

- **`Config.set_keyfile_path` classmethod:** No existing `Config` classmethod that mutates class-level state. Closest is `Config.from_dict` (staticmethod) and `Persist.from_file` (classmethod). The new setter introduces a new pattern but is trivially simple (single assignment); RESEARCH §9.3 endorses it over the more invasive alternative of widening `Persist.from_file` signatures.
- **Atomic exclusive-create file open (`os.O_EXCL | 0o600`):** No existing project usage — `persist.py` uses the non-atomic write-then-chmod. This is a net-new pattern for the keyfile-create path, justified by the stronger security requirement on a private key vs. a config file. Plan should note this is a deliberate deviation.

## Metadata

**Analog search scope:**
- `src/python/common/` (config.py, persist.py, error.py, __init__.py)
- `src/python/seedsyncarr.py`
- `src/python/tests/unittests/test_common/` (test_config.py, test_persist.py)
- `src/python/tests/unittests/test_seedsyncarr.py`
- `src/python/pyproject.toml`
- `docs/CONFIGURATION.md`

**Files scanned:** 10

**Pattern extraction date:** 2026-04-22
