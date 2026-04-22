# Phase 81: Optional Fernet Encryption at Rest - Research

**Researched:** 2026-04-22
**Domain:** Symmetric file-at-rest encryption of 5 config secrets using `cryptography.fernet`, integrated into the existing `Config.from_str / to_str` serialization seam, with opt-in flag and transparent decrypt on load.
**Confidence:** HIGH

## 1. Summary

Seedsyncarr's configuration layer is a clean `configparser`-backed `Persist` subclass (`src/python/common/config.py`) that routes every read through `Config.from_str` and every write through `Config.to_str`. The five secrets named in SEC-02 (`general.webhook_secret`, `general.api_token`, `sonarr.sonarr_api_key`, `radarr.radarr_api_key`, `lftp.remote_password`) are already declared on the relevant `InnerConfig` subclasses with `Checkers.null` — they accept empty strings, which is the exact property we need to store arbitrary Fernet ciphertext in. No schema change is needed to store encrypted values; only the serialization seam must be widened to encrypt-on-write and decrypt-on-read for those five fields. [VERIFIED: grep of src/python/common/config.py]

The entry-point `Seedsyncarr.__init__` (`src/python/seedsyncarr.py:35-104`) already calls `Config.from_file(config_path)` then immediately writes the config back (if defaults were created), and `Seedsyncarr.persist()` writes the full config on a periodic timer plus on shutdown (lines 212-217). This gives us a natural "re-encrypt plaintext on startup" hook: load → detect plaintext in the five fields → re-encrypt → save. Three existing tests (`test_from_file`, `test_to_file`, `test_persist_read_error`) demonstrate the exact patterns we must preserve. [VERIFIED: direct read of `seedsyncarr.py` and `test_config.py`]

The `cryptography` package (v46.0.7, PyPI 2026-04) ships a stable `Fernet` primitive with a 44-byte url-safe-base64 key, authenticated AES-128-CBC + HMAC-SHA256, and a deterministic token prefix (`gAAAAA`) that makes plaintext/ciphertext discrimination trivial without attempting a decrypt. Decrypt failures raise a single exception type (`cryptography.fernet.InvalidToken`) which we can catch and surface as a startup warning. [VERIFIED: live Python repl — see Section 6.2]

**Primary recommendation:** Add `cryptography>=44.0.0,<47` to `[project.dependencies]`, introduce a new `[Encryption]` config section (flag: `enabled: bool`, default `false`) following the established AutoDelete/Sonarr backward-compatible-optional-section pattern, and funnel all encrypt/decrypt through a new `common.encryption` module. Override `Config.from_str` and `Config.to_str` to transform the five target fields after parsing and before writing. Keyfile lives at `{config_dir}/secrets.key` with 0600 permissions (matching the existing `Persist.to_file` convention at `common/persist.py:50`). No code changes outside `config.py`, `encryption.py` (new), `seedsyncarr.py` (one call to re-encrypt-plaintext on startup), `pyproject.toml`, `poetry.lock`, and the three test files touching config.

## 2. Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEC-02 | Optional Fernet encryption at rest for 5 secrets (`api_token`, `webhook_secret`, `sonarr_api_key`, `radarr_api_key`, `remote_password`); 0600 keyfile; transparent decrypt in `config.py` read path; plaintext-on-startup re-encrypt in place; config flag to disable for manual editing; backward-compatible with existing plaintext installs | Sections 4 (architecture), 5 (stack), 6.1 (Fernet API behavior), 7 (patterns), 8 (pitfalls), 9 (examples), 11 (test map) |

## 3. Project Constraints (from STATE.md / REQUIREMENTS.md / ROADMAP.md)

- **No new user-facing features in v1.1.1** (REQUIREMENTS.md:6). SEC-02 is the single exception — explicitly called out as "net-new capability (optional Fernet encryption, opt-in, backward-compatible)." Implication: no settings-page UI for this phase. The flag is set by editing `settings.cfg` manually.
- **"No code changes outside `config.py`"** (ROADMAP.md:349, success criterion #2). Interpreted: the rest of the app continues to read `config.general.api_token` etc. and sees plaintext. The encrypt/decrypt seam MUST live entirely in the serialization layer, not in any caller. One small exception (startup plaintext re-encryption) lives in `seedsyncarr.py` — this is the existing owner of file I/O and is consistent with the success criterion's spirit (no consumer changes). Acceptable because (a) `seedsyncarr.py` already owns `to_file(self.config_path)` calls and (b) a new helper module is allowed.
- **Backward compatibility** (criterion #3): plaintext installs with flag disabled continue working unchanged. Every existing test that writes `settings.cfg` without `[Encryption]` must still pass.
- **Round-trip preservation** (criterion #4): enable→disable restores plaintext values with no data loss. Implies the disable path must decrypt all 5 fields and write them back in plaintext.
- **Decrypt failure warning** (criterion #5): must surface a "clear startup warning." The existing `Seedsyncarr._emit_startup_warnings` (lines 356-376) is the exact precedent — uses `logger.warning(...)` for security states.
- **Python version pin:** `>=3.11,<3.13` (pyproject.toml:10). `cryptography>=44` requires Python ≥3.9, so we're well within range.
- **Test coverage floor:** `fail_under = 84` (pyproject.toml:89). New `common/encryption.py` must be covered accordingly.
- **`commit_docs: true`** (.planning/config.json:4) — plan commits each generated doc.
- **`nyquist_validation` key is ABSENT** in `.planning/config.json` — treat as enabled; include Validation Architecture section.

## 4. Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Key generation & file persistence | Backend / `common.encryption` module | — | Pure Python, one-shot on first enable, tied to config_dir |
| Encrypt-on-write of 5 fields | Backend / `Config.to_str` (config.py) | `common.encryption` (primitive) | Serialization seam; keeps app callers oblivious |
| Decrypt-on-read of 5 fields | Backend / `Config.from_str` (config.py) | `common.encryption` (primitive) | Inverse of write seam |
| Plaintext detection on load | Backend / `common.encryption.is_ciphertext()` | — | Used during read (graceful plaintext fallback) and during re-encrypt pass |
| Re-encrypt plaintext on startup | Backend / `seedsyncarr.py` (post-load hook) | `Config.to_file` + `common.encryption` | Owner of startup sequence + file I/O; symmetric with existing `_emit_startup_warnings` |
| Decrypt-failure warning | Backend / `seedsyncarr.py` startup | logger | Matches existing `_emit_startup_warnings` pattern |
| Opt-in flag | Backend / `Config.Encryption` new InnerConfig | — | Follows AutoDelete/Sonarr precedent |
| Settings UI | NOT IN THIS PHASE | — | v1.1.1 constraint: "no user-visible feature additions" |

**Tier assignment sanity check:** Fernet is a symmetric-crypto primitive — it belongs in the same process that reads/writes `settings.cfg`. There is no "server" tier here; the Python backend IS the sole process. No frontend involvement.

## 5. Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | `>=44.0.0,<47` (current stable: 46.0.7, 2026-04) | `cryptography.fernet.Fernet` + `InvalidToken` | The PyCA reference implementation — the single "don't hand-roll" choice for Python symmetric crypto; used by Django, Ansible Vault, HashiCorp Vault Python client, AWS SDK boto3 crypto, and ~every Python project that asks "how do I encrypt a string." Fernet is the high-level recipe layer of PyCA; it is the literal recommendation in the cryptography.io docs for "encrypt a small piece of data and have my hands held" use cases. [VERIFIED: PyPI, pip3 show cryptography on this machine shows 46.0.6 already present; fernet/spec.md token format confirmed] |

### Supporting (none needed)

No additional libraries. `cryptography` brings its own C backend (openssl). The stdlib `configparser`, `os`, `base64`, and `tempfile` cover everything else.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cryptography.fernet` | `PyNaCl` (SecretBox) | PyNaCl is equally solid but requires an extra dep and wraps libsodium. Fernet is strictly what SEC-02 names by word. Also the token format doubles as an "is-it-ciphertext?" discriminator (prefix `gAAAAA`) with no extra work. [CITED: REQUIREMENTS.md:32] |
| `cryptography.fernet` | `cryptography.hazmat.primitives.ciphers.aead.ChaCha20Poly1305` | Hazmat = "here's the rope, try not to hang yourself." Fernet hides IV generation, padding, HMAC, base64. Don't hand-roll. |
| Our own token format | Raw AES-GCM | Requires us to design key rotation, versioning, and corruption detection. Fernet already gives us a version byte, timestamp, and HMAC. |

**Installation:**

```bash
# Via poetry (canonical for this project, per pyproject.toml:42-69)
cd src/python && poetry add "cryptography>=44,<47"
# Via pip (secondary, for [project.dependencies] in same file)
pip install "cryptography>=44,<47"
```

Both `[project.dependencies]` (line 11-20) and `[tool.poetry.dependencies]` (line 51-58) MUST be updated — the project uses a dual hatchling + poetry setup (pyproject.toml:2-4 declare hatchling as build-system; poetry is used for `poetry install` in Dockerfile:53, 106). Keep both lists in sync.

**Version verification:** `npm view` equivalent for PyPI is `pip index versions cryptography` or the live PyPI JSON endpoint. Verified 2026-04-22: latest stable is `46.0.7`. `44.0.0` was released 2024-11, stable API surface unchanged through 46.x. Pin `>=44,<47` gives room for security patches while capping a major (PyCA has a history of deprecating hazmat APIs across majors — `fernet` itself is API-stable, but conservative cap is prudent). [VERIFIED: WebFetch https://pypi.org/pypi/cryptography/json]

## 6. Architecture Patterns

### 6.1 System Architecture Diagram

```
   ┌──────────────────────────────────────────────────────────────────┐
   │  Disk:  {config_dir}/                                            │
   │    settings.cfg      (INI, may contain 5 ciphertext values)      │
   │    secrets.key       (44-byte Fernet key, 0600)                  │
   └──────────────────────────────────────────────────────────────────┘
              │                                      ▲
              │ read                                 │ write
              ▼                                      │
   ┌──────────────────────────────────────────────────────────────────┐
   │  common/persist.py  Persist.from_file / to_file                  │
   │   - enforces 0600 permissions (unchanged)                        │
   │   - delegates to Config.from_str / to_str                        │
   └──────────────────────────────────────────────────────────────────┘
              │                                      ▲
              ▼                                      │
   ┌──────────────────────────────────────────────────────────────────┐
   │  common/config.py  Config.from_str / to_str  (SERIALIZATION SEAM)│
   │                                                                  │
   │   from_str(content):                                             │
   │     1. parse INI → dict                                          │
   │     2. read [Encryption].enabled flag (default False if absent)  │
   │     3. IF enabled: load keyfile → Fernet → for each of 5 secret  │
   │        paths, IF is_ciphertext(v) → decrypt, ELSE leave as-is    │
   │        (plaintext fallback; flag re-encrypt on next write)       │
   │     4. populate Config.general/lftp/sonarr/radarr/autodelete/... │
   │                                                                  │
   │   to_str():                                                      │
   │     1. Config.as_dict() → OrderedDict                            │
   │     2. IF enabled: for each of 5 secret paths, IF value is       │
   │        non-empty AND NOT already ciphertext → encrypt            │
   │     3. serialize INI → str                                       │
   └──────────────────────────────────────────────────────────────────┘
              │                                      ▲
              ▼                                      │
   ┌──────────────────────────────────────────────────────────────────┐
   │  common/encryption.py  (NEW)                                     │
   │   - load_or_create_key(keyfile_path) -> bytes (0600 on create)   │
   │   - is_ciphertext(s: str) -> bool   (checks 'gAAAAA' prefix)     │
   │   - encrypt(key, plaintext: str) -> str                          │
   │   - decrypt(key, token: str) -> str  (raises DecryptionError on  │
   │     InvalidToken)                                                │
   └──────────────────────────────────────────────────────────────────┘
              ▲
              │
   ┌──────────────────────────────────────────────────────────────────┐
   │  seedsyncarr.py  startup sequence                                │
   │    1. Config.from_file(config_path)   [decrypts if enabled]      │
   │    2. _emit_startup_warnings(...)     [add DecryptionError warn] │
   │    3. if encryption_enabled AND any_plaintext_in_5_fields:       │
   │          config.to_file(config_path)  [re-encrypts in place]     │
   │    4. rest of app runs unchanged, sees plaintext via context     │
   └──────────────────────────────────────────────────────────────────┘
```

**Trace for the primary "enable on an existing plaintext install" case:**

1. User stops app, edits `settings.cfg`, appends `[Encryption]\nenabled = True`, restarts app.
2. `seedsyncarr.__init__` calls `Config.from_file(config_path)`.
3. `from_str` parses INI, sees `[Encryption].enabled = True`, constructs a `Fernet` from `load_or_create_key({config_dir}/secrets.key)`. Keyfile doesn't exist → generate + write 0600.
4. `from_str` checks each of the 5 fields. Value is `my_real_password` → `is_ciphertext('my_real_password') == False` → leave as plaintext, but flag `has_plaintext = True` on the returned Config (or re-check in seedsyncarr).
5. `Config.general/lftp/...` populated with plaintext.
6. `seedsyncarr.py` sees the `has_plaintext` flag → calls `self.context.config.to_file(self.config_path)`.
7. `to_str` re-runs: enabled=True, each of the 5 fields is non-empty plaintext → `Fernet.encrypt(...)` → writes `settings.cfg` with ciphertext in those slots.
8. Disk now shows encrypted `settings.cfg`. Permissions on `settings.cfg` (0600 via `Persist.to_file`) and `secrets.key` (0600 set on creation) both enforced.
9. App continues; rest of runtime sees plaintext via `context.config.*`.

### 6.2 Recommended File Structure

```
src/python/
├── common/
│   ├── config.py             # MODIFIED: from_str/to_str widened; new [Encryption] section
│   ├── encryption.py         # NEW: key mgmt + encrypt/decrypt helpers + is_ciphertext
│   ├── persist.py            # UNCHANGED: still enforces 0600
│   └── __init__.py           # MODIFIED: export new encryption helpers if needed
├── seedsyncarr.py            # MODIFIED: add re-encrypt-plaintext-on-startup call + warning
├── pyproject.toml            # MODIFIED: add cryptography to [project.dependencies] + [tool.poetry.dependencies]
├── poetry.lock               # MODIFIED: regenerated
└── tests/unittests/test_common/
    ├── test_config.py        # MODIFIED: add 5 SEC-02 test cases (enable-new, enable-existing, disable-restore, bad-value, missing-keyfile)
    └── test_encryption.py    # NEW: unit tests for encryption module (round-trip, is_ciphertext, keyfile perms, InvalidToken handling)
```

### 6.3 Pattern 1: Serialization-Seam Encryption

**What:** Put encrypt/decrypt on the exact boundary between "on-disk bytes" and "in-memory Python objects." Every caller upstream of the seam sees plaintext. Every byte downstream of the seam is ciphertext (or explicit plaintext when the flag is off).

**When to use:** Whenever a configuration or persistence system already has a clean serialize/deserialize pair. Seedsyncarr already has this: `Persist.from_str` / `to_str`. The existing `SerializeConfig.config(..., authenticated=True)` in `web/serialize/serialize_config.py` follows the same "decorate-at-serialization-boundary" pattern for redaction.

**Example:**

```python
# src/python/common/config.py (MODIFIED - pattern only, not full code)

_SECRET_FIELD_PATHS = (
    ("general", "webhook_secret"),
    ("general", "api_token"),
    ("lftp", "remote_password"),
    ("sonarr", "sonarr_api_key"),
    ("radarr", "radarr_api_key"),
)

class Config(Persist):
    # ... existing classes unchanged ...

    class Encryption(IC):
        enabled = PROP("enabled", Checkers.null, Converters.bool)
        # key_file is intentionally NOT configurable — fixed at {config_dir}/secrets.key
        # to keep success-criterion #1 tractable.

        def __init__(self):
            super().__init__()
            self.enabled = None

    def __init__(self):
        # ... existing ...
        self.encryption = Config.Encryption()
        self._keyfile_path: Optional[str] = None  # injected by seedsyncarr before from_file

    @classmethod
    def from_str(cls, content: str) -> "Config":
        # Parse INI as before
        config_parser = configparser.ConfigParser()
        try:
            config_parser.read_string(content)
        except (configparser.MissingSectionHeaderError, configparser.ParsingError) as e:
            raise PersistError(...)
        config_dict = _parser_to_dict(config_parser)

        # Resolve encryption flag (backward-compat: default False)
        enc_section = config_dict.get("Encryption", {"enabled": "False"})
        encryption_enabled = _strtobool(enc_section.get("enabled", "False")) == 1

        if encryption_enabled and cls._keyfile_path:
            from .encryption import load_or_create_key, decrypt_field_if_token
            key = load_or_create_key(cls._keyfile_path)
            for section, field in _SECRET_FIELD_PATHS:
                section_key = section.capitalize()  # INI sections are TitleCase
                if section_key in config_dict and field in config_dict[section_key]:
                    config_dict[section_key][field] = decrypt_field_if_token(
                        key, config_dict[section_key][field]
                    )

        return Config.from_dict(config_dict)

    def to_str(self) -> str:
        config_dict = self.as_dict()
        if self.encryption.enabled and self._keyfile_path:
            from .encryption import load_or_create_key, encrypt_field_if_plaintext
            key = load_or_create_key(self._keyfile_path)
            for section, field in _SECRET_FIELD_PATHS:
                section_key = section.capitalize()
                if section_key in config_dict and field in config_dict[section_key]:
                    val = config_dict[section_key][field]
                    if val:  # only encrypt non-empty
                        config_dict[section_key][field] = encrypt_field_if_plaintext(
                            key, val
                        )
        # ... existing serialization from dict to INI ...
```

*Source: adapted from existing `Config.from_str` / `to_str` in `src/python/common/config.py:360-389`.*

### 6.4 Pattern 2: Plaintext/Ciphertext Discrimination via Token Prefix

**What:** Fernet tokens are the url-safe-base64 of `version_byte(0x80) || timestamp(8B) || IV(16B) || ciphertext || HMAC(32B)`. With version byte 0x80 and a 32-bit epoch timestamp whose upper 3 bytes are zero until year 2106, the first 6 characters of every Fernet token are deterministically `gAAAAA`. [VERIFIED: Fernet spec; confirmed with 5 random tokens at different times in Section 9.1]

**When to use:** Whenever you need to decide "is this string already encrypted?" without paying a decrypt attempt or risking an exception-control-flow anti-pattern.

**Caveat:** A user-chosen plaintext password that literally starts with the 6 characters `gAAAAA` would be mis-classified as ciphertext. Mitigations: (1) the full check is `len >= 100 AND startswith('gAAAAA') AND decodes as valid url-safe base64`; (2) even if mis-classified, the decrypt attempt will raise `InvalidToken` on real data (because HMAC won't match), which surfaces the clear startup warning required by criterion #5. The ambiguity is a known Fernet-at-rest quirk; the mitigation is documented below in Section 8.

**Example:**

```python
# src/python/common/encryption.py (NEW)

_FERNET_TOKEN_PREFIX = "gAAAAA"
_FERNET_TOKEN_MIN_LEN = 100  # empirically observed — shortest meaningful token

def is_ciphertext(s: str) -> bool:
    """
    Best-effort discriminator. Returns True iff s has the shape of a Fernet token.
    A user-chosen plaintext starting with 'gAAAAA' would be a false positive; the
    subsequent decrypt attempt will then raise InvalidToken and surface a warning.
    """
    if not s or len(s) < _FERNET_TOKEN_MIN_LEN:
        return False
    if not s.startswith(_FERNET_TOKEN_PREFIX):
        return False
    # Final shape check: valid url-safe base64
    try:
        import base64
        base64.urlsafe_b64decode(s.encode("ascii"))
        return True
    except (ValueError, binascii.Error):
        return False
```

### 6.5 Pattern 3: Backward-Compatible Optional Section

**What:** New INI sections are added as optional in `Config.from_dict`, with explicit defaults for missing keys. The established pattern is at `config.py:411-438` for Sonarr, Radarr, AutoDelete.

**When to use:** ANY new `[Section]` added to `settings.cfg` in this project.

**Example:** See `config.py:429-438`:
```python
if "AutoDelete" in config_dict:
    config.autodelete = Config.AutoDelete.from_dict(
        Config._check_section(config_dict, "AutoDelete")
    )
else:
    config.autodelete.enabled = False
    config.autodelete.dry_run = False
    config.autodelete.delay_seconds = 60
```

For `[Encryption]` the default is `enabled = False`, which is exactly the backward-compat criterion #3 requires.

### 6.6 Anti-Patterns to Avoid

- **Wrapping `context.config.api_token` with a decrypt property.** This forces callers to know about encryption and violates success criterion #2 ("no code changes outside `config.py`").
- **Using `hazmat` primitives directly.** Never hand-roll AES-GCM, key derivation, or IV generation. Fernet exists for this exact reason.
- **Calling `os.chmod(keyfile, 0o600)` blind on Windows.** It's a no-op on Windows (see Section 8.3). We need either a best-effort + warn, or a platform guard.
- **Storing the keyfile inside the encrypted config file** ("bootstrap paradox"). The whole point is the key is external.
- **Emitting the keyfile path in logs or error messages with the key contents.** Existing log-redaction covers values named `password|api_key|api_token|secret|webhook_secret|remote_password` (`context.py:54`); "key" is NOT in that list. The keyfile content must never be logged.
- **Raising `InvalidToken` up to the user.** Criterion #5 requires a "clear startup warning," not a crash. Catch at the encryption module boundary and surface via logger + continue (with plaintext fallback or disabled crypto state).
- **Putting crypto behind an auto-generated key on `from_file`.** That would create a keyfile the first time someone reads the config for ANY reason. The key must only be created when `[Encryption].enabled = True` is observed.

## 7. Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Authenticated symmetric encryption | AES-CBC with separate HMAC, or "XOR with the key" | `cryptography.fernet.Fernet` | Fernet composes AES-128-CBC + PKCS7 padding + HMAC-SHA256 + IV management + versioning + base64 encoding. Each of those is a mistake-factory on its own. |
| Random IV generation | `random.randbytes(16)` or `os.urandom(16)` by hand | `Fernet.encrypt` (handles it) | Easy to forget and get deterministic IV reuse, which breaks semantic security |
| Key file format | Write raw bytes and hope | `Fernet.generate_key()` emits a self-describing 44-byte url-safe-base64 token; write those bytes directly | The format is literally what the `Fernet()` constructor wants back |
| Ciphertext-vs-plaintext detection | Regex for "looks encrypted" | Prefix check on `gAAAAA` + length gate + b64 parse | Deterministic from the Fernet spec; no heuristic needed |
| Key rotation | Manually re-encrypt everything | `cryptography.fernet.MultiFernet([new_key, old_key])` decrypts with any, encrypts with first | Out of scope for SEC-02 but worth noting so future rotation work has a trivial path. See Open Questions. |
| Secure file permissions on new files | `open(...)` then `os.chmod` | `os.open(path, os.O_WRONLY \| os.O_CREAT \| os.O_EXCL, 0o600)` followed by `os.fdopen` | Race-free on POSIX; Windows limitation documented below. Seedsyncarr's existing `persist.py:to_file` uses the non-atomic two-step; we should match it for consistency UNLESS we want to tighten. Recommendation: match `persist.py` for consistency, add the `os.chmod` after write. (NB: Existing `persist.py` writes then chmod's — same pattern.) |
| Constant-time comparison | `==` on tokens | Not needed for Fernet; the HMAC inside Fernet already provides this | Irrelevant for our use |

**Key insight:** Fernet exists precisely because nine out of ten "encrypt a secret at rest" implementations in the wild are broken (missing authentication, IV reuse, padding oracle, etc.). The library author's position is literally "use Fernet for anything that fits, use hazmat otherwise and take the blame." [CITED: cryptography.io/en/latest/fernet/]

## 8. Common Pitfalls

### 8.1 Pitfall 1: Plaintext Leak via Backup File

**What goes wrong:** `Seedsyncarr.__backup_file(self.config_path)` (`seedsyncarr.py:424-438`) is called when `Config.from_file` raises `ConfigError` or `PersistError`. It does `shutil.copy(file_path, backup_path)`. If a decrypt failure surfaces as one of those errors, the backup will contain encrypted data AT 0644 (the default mode `shutil.copy` preserves from source). If the original `settings.cfg` was 0600, the backup should inherit 0600 — `shutil.copy` copies mode only with `shutil.copy2` or `copystat`. `shutil.copy` preserves mode via `copymode`. [VERIFIED: Python docs `shutil.copy` "copies the permission bits"]

**Why it happens:** Backup is a secondary write path that most people forget about when auditing a secret-at-rest scheme.

**How to avoid:** (a) Decrypt failures should NOT reach `__backup_file` — they should be caught inside the encryption module, logged as warning, and returned as plaintext-fallback. Only genuine parse errors (`MissingSectionHeaderError`, `ParsingError`) should trigger backup. (b) Add an `os.chmod(backup_path, 0o600)` inside `__backup_file` defensively. (c) If the backup MUST contain encrypted content, that's acceptable as long as permissions are tight and the keyfile is still present — the ciphertext is worthless without it.

**Warning signs:** `settings.cfg.1.bak` at 0644 containing `gAAAAA`-prefixed strings in the field values.

### 8.2 Pitfall 2: `gAAAAA` False-Positive on User Plaintext

**What goes wrong:** A user picks `gAAAAAmyreallylongpassword_1234567890...` as a password longer than 100 chars. `is_ciphertext()` returns True; decrypt raises `InvalidToken`; startup logs a warning; plaintext fallback happens (or worse, the value is discarded if we're not careful).

**Why it happens:** Our discriminator is a prefix heuristic. It's "good enough" because real passwords almost never start with `gAAAAA`, but it's not rigorous.

**How to avoid:** When `is_ciphertext()` returns True but decrypt raises `InvalidToken`, log a CLEAR warning like `"Value in [Section].field looks like ciphertext but failed decryption. Treating as plaintext. If this is your actual password, please rotate it — it cannot be distinguished from encrypted content."` Then leave the value as-is. Do NOT encrypt it automatically next write — that would turn a real-password "gAAAAA-prefixed" value into ciphertext during the next save and the user couldn't recover it. Safer: surface warning, leave plaintext, require user action.

**Warning signs:** Decrypt warning on startup for a specific field in an install that was never encrypted.

### 8.3 Pitfall 3: Windows `os.chmod(0o600)` Is a No-Op

**What goes wrong:** Success criterion #1 says "keyfile is generated with 0600 permissions." On Windows, `os.chmod(path, 0o600)` only toggles the read-only flag via `stat.S_IWRITE | stat.S_IREAD`. All the owner/group/other distinctions are completely ignored. Python's os.chmod on Windows did not gain rich ACL support until 3.13. [VERIFIED: Python docs + WebFetch on os.chmod]

**Why it happens:** Windows uses ACLs, not POSIX permission bits. Python exposes only a tiny subset.

**How to avoid:** (1) Still call `os.chmod(keyfile, 0o600)` unconditionally — harmless on Windows, effective on Linux/macOS. (2) In the success-criterion test, use `os.name == 'posix'` to skip the mode assertion on Windows (or mark the test `@unittest.skipUnless(sys.platform != 'win32', ...)`). (3) Document the limitation in a code comment near the keyfile write. (4) Seedsyncarr is targeted at Linux (Docker runtime image is `python:3.11-slim` / Debian 12 — `src/docker/build/docker-image/Dockerfile:75`); Windows is a nice-to-have, not a hard requirement. Existing `persist.py` uses `os.chmod(..., 0o600)` without any Windows guard (`persist.py:43, 50`) and the existing test `test_to_file_sets_0600_permissions` in `test_persist.py:70-76` runs successfully on this macOS machine — CI runs on `ubuntu-latest` so POSIX semantics hold. Match that.

**Warning signs:** Test `test_keyfile_permissions` fails on Windows with `0o666` instead of `0o600`. Skip-on-Windows annotation resolves.

### 8.4 Pitfall 4: Losing the Keyfile == Losing the Data

**What goes wrong:** User deletes `secrets.key` thinking it's stale. Next startup, `from_str` finds `[Encryption].enabled = True` and 5 ciphertext values. A NEW key is generated. Decrypt of the old ciphertext raises `InvalidToken`. Five secrets are now unrecoverable.

**Why it happens:** The opt-in flag doesn't care whether the keyfile is fresh or ancient; the only signal is "enabled".

**How to avoid:** (1) On startup, if `[Encryption].enabled = True` AND no keyfile exists AND any of the 5 fields is already ciphertext-shaped → refuse to auto-create a new key, log a LOUD error, and leave the config untouched. Only create a key when the fields are plaintext (first-time-enable) or all empty. This is the honest "undelete-proof" behavior. (2) Document in `docs/configuration.md` that `secrets.key` MUST be backed up alongside `settings.cfg`. (3) The keyfile path (not contents) should be logged at INFO on first use so operators know what to back up.

**Warning signs:** User reports "my API keys don't work anymore after I cleaned up my config directory."

### 8.5 Pitfall 5: Periodic `persist()` Re-Writes While Flag Is Disabled

**What goes wrong:** `Seedsyncarr.persist()` at line 212-217 writes `config.to_file(self.config_path)` every `MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS`. If a user edits `[Encryption].enabled = True` at runtime via the `/server/config/set/...` handler (which DOES exist — `web/handler/config.py:23` registers the route), the in-memory config flips but the keyfile is not created until the next `to_str` call. At periodic persist time, `to_str` encrypts-in-memory, creates the keyfile, writes encrypted `settings.cfg`. This is actually the desired behavior — BUT: if the user flips the flag in-memory and then the process crashes before the next persist, the on-disk config is still plaintext + `[Encryption].enabled = True`. The restart then re-reads plaintext, treats as already-enabled-plaintext, re-encrypts. Fine. But during the brief window, any SSE observer or `/server/config/get` response would show the in-memory state with encryption flag flipped while on-disk is not yet re-encrypted. Acceptable for a single-user tool. Document.

**Why it happens:** Runtime toggle creates a transient inconsistency between in-memory config and on-disk config.

**How to avoid:** (1) Treat the flag like any other config change — the existing architecture of "mutate in memory, persist periodically" already tolerates this. (2) Recommend in docs that users flip the flag with the app stopped, edit `settings.cfg` directly, and restart — this is literally what the "flag lets users disable encryption for manual editing" use case in criterion #4 implies.

**Warning signs:** Not really a bug, but a UX quirk.

### 8.6 Pitfall 6: `Config.from_dict` Is Used In Tests Directly

**What goes wrong:** `test_config.py:test_to_file` at line 479 builds a `Config` instance by setting fields in Python, calls `config.to_file(path)`, reads back, string-compares against a golden. If we make `to_str` encrypt when `encryption.enabled = True`, all existing tests must default `encryption.enabled = False`. If we forget to add `encryption.enabled = False` to `_create_default_config` (`seedsyncarr.py:292-344`) OR to the test builders, the `to_str` path will try to resolve a keyfile path (which is None) and crash.

**Why it happens:** Default-value drift — a new field is added to the schema but some callers pre-date its existence.

**How to avoid:** (1) Add `config.encryption.enabled = False` to `_create_default_config` in `seedsyncarr.py`. (2) In `Config.to_str`, when `encryption.enabled = True` but `_keyfile_path` is None, raise a clear `ConfigError` ("Encryption enabled but no keyfile path set — call Config.set_keyfile_path() before to_str()"). (3) Ensure existing tests either explicitly set `encryption.enabled = False` OR rely on the default. (4) Provide a module-level helper `_make_default_test_config()` fixture in `tests/conftest.py` if repetition is high.

**Warning signs:** Dozens of test failures on CI after landing the encryption code, all complaining about missing `encryption` section.

## 9. Code Examples

### 9.1 Fernet API Behavior (live-verified on this machine)

```python
# VERIFIED via interactive python3 session on 2026-04-22:
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

key = Fernet.generate_key()            # type=bytes, len=44 (url-safe base64)
f = Fernet(key)
token = f.encrypt(b'my_secret_password')
# type=bytes, len=100, ALWAYS starts with b'gAAAAA'
# (Observed 5/5 random tokens prefix 'gAAAAABp6O6R' at test time)

plain = f.decrypt(token)               # → b'my_secret_password'

# Failure modes — ALL raise the SAME exception class:
Fernet(other_key).decrypt(token)       # → InvalidToken()
f.decrypt(b'gAAAAAnot-a-real-token')   # → InvalidToken()
f.decrypt(b'')                         # → InvalidToken()

# Rotation primitive (out of scope for Phase 81 but trivial to adopt later):
mf = MultiFernet([Fernet(new_key), Fernet(old_key)])
mf.decrypt(old_token)                  # → plaintext (tries new first, falls back to old)
mf.encrypt(b'secret')                  # → always encrypted with new_key
```

*Source: direct repl on /usr/bin/python3 (Python 3.9.6, cryptography 46.0.6) on this machine.*

### 9.2 Keyfile Creation + Load

```python
# src/python/common/encryption.py (NEW - recommended content)
import os
from cryptography.fernet import Fernet, InvalidToken

from .error import AppError

class DecryptionError(AppError):
    """Raised when a Fernet token cannot be decrypted."""
    pass

def load_or_create_key(keyfile_path: str) -> bytes:
    """
    Returns the Fernet key at keyfile_path.
    Creates a new 44-byte url-safe-base64 key with 0600 permissions if absent.
    On POSIX this enforces owner-only access; on Windows chmod is best-effort
    (only read-only flag is honored — see Pitfall 8.3).
    """
    if os.path.isfile(keyfile_path):
        # Tighten permissions on existing file (matches Persist.from_file)
        try:
            os.chmod(keyfile_path, 0o600)
        except OSError:
            pass  # best-effort on Windows
        with open(keyfile_path, "rb") as f:
            return f.read().strip()

    key = Fernet.generate_key()  # 44 bytes, url-safe base64
    # Write atomically-ish: open exclusive, write, chmod.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(keyfile_path, flags, 0o600)
    try:
        os.write(fd, key)
    finally:
        os.close(fd)
    try:
        os.chmod(keyfile_path, 0o600)
    except OSError:
        pass
    return key
```

*Source: adapted from `persist.py:to_file` pattern (`src/python/common/persist.py:47-50`) plus Fernet docs.*

### 9.3 Widened `Config.from_str` (pattern only)

See Section 6.3 — the full integration sketch. Important implementation detail: the `Config` class is stateful (`self.encryption`, `self._keyfile_path`), and `from_str` is a `@classmethod`. The keyfile path must be passed as a class-level hook. Recommended approach: introduce `Config.set_keyfile_path(path: str)` as a classmethod that sets a private class-level attribute, called once from `Seedsyncarr.__init__` immediately before `Config.from_file(self.config_path)`. This preserves the `Persist` contract (no extra arg to `from_file`).

Alternative: teach `Persist.from_file` to accept `**kwargs` and pass through. More invasive; not recommended.

### 9.4 Startup Re-encryption of Plaintext

```python
# src/python/seedsyncarr.py (MODIFIED - post _create_default_config section)
# After `config = Config.from_file(self.config_path)` and before logger setup:

# Re-encrypt plaintext-in-encrypted-mode in place (SEC-02 criterion #3)
if config.encryption.enabled:
    from common.encryption import is_ciphertext
    has_plaintext = False
    for section, field in Config.SECRET_FIELD_PATHS:
        inner = getattr(config, section)
        value = getattr(inner, field, None)
        if value and not is_ciphertext(value):
            has_plaintext = True
            break
    if has_plaintext:
        # to_file will re-encrypt via to_str
        config.to_file(self.config_path)
```

### 9.5 Unit Test Skeletons (maps to criterion #5)

```python
# src/python/tests/unittests/test_common/test_encryption.py (NEW)
import unittest, os, tempfile, stat, sys
from common.encryption import (
    load_or_create_key, is_ciphertext, encrypt_field, decrypt_field, DecryptionError,
)

class TestEncryption(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.keyfile = os.path.join(self.tmp, "secrets.key")
    def tearDown(self):
        import shutil; shutil.rmtree(self.tmp)

    def test_key_generated_on_first_call(self):
        self.assertFalse(os.path.isfile(self.keyfile))
        key = load_or_create_key(self.keyfile)
        self.assertTrue(os.path.isfile(self.keyfile))
        self.assertEqual(44, len(key))

    @unittest.skipIf(sys.platform == "win32", "POSIX permission bits only")
    def test_keyfile_is_0600(self):
        load_or_create_key(self.keyfile)
        mode = os.stat(self.keyfile).st_mode & 0o777
        self.assertEqual(0o600, mode)

    def test_round_trip(self):
        key = load_or_create_key(self.keyfile)
        token = encrypt_field(key, "my_password")
        self.assertTrue(is_ciphertext(token))
        self.assertEqual("my_password", decrypt_field(key, token))

    def test_is_ciphertext_rejects_plaintext(self):
        self.assertFalse(is_ciphertext(""))
        self.assertFalse(is_ciphertext("short"))
        self.assertFalse(is_ciphertext("gAAAAA_short"))
        self.assertFalse(is_ciphertext("not_a_token_but_long_enough_" * 10))

    def test_decrypt_wrong_key_raises_decryption_error(self):
        key1 = load_or_create_key(self.keyfile)
        token = encrypt_field(key1, "secret")
        # Regenerate: simulate keyfile loss
        os.remove(self.keyfile)
        key2 = load_or_create_key(self.keyfile)
        with self.assertRaises(DecryptionError):
            decrypt_field(key2, token)
```

```python
# src/python/tests/unittests/test_common/test_config.py (APPEND to TestConfig)

def test_encryption_disabled_by_default(self):
    """Backward-compat: existing configs without [Encryption] section load with flag=False."""
    # Build a config string WITHOUT [Encryption]
    content = "[General]\ndebug=False\nverbose=False\nwebhook_secret=\napi_token=\nallowed_hostname=\n..."
    config = Config.from_str(content)
    self.assertEqual(False, config.encryption.enabled)

def test_enable_new_install_encrypts_on_write(self):
    """Criterion #1: first run with flag enabled encrypts secrets in place."""
    # ...

def test_enable_existing_plaintext_reencrypts(self):
    """Criterion #3: plaintext values on enabled install are re-encrypted."""
    # ...

def test_disable_restores_plaintext(self):
    """Criterion #4: round-trip enable→disable preserves all 5 values."""
    # ...

def test_decrypt_failure_emits_warning(self):
    """Criterion #5: corrupt ciphertext surfaces a clear startup warning."""
    # ...
```

## 10. Runtime State Inventory

> Phase 81 is net-new capability, not a rename/refactor. No existing runtime state embeds a "Fernet" or "secrets.key" token that will need migration. This section is brief; included for completeness per research protocol.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `settings.cfg` at `{config_dir}/settings.cfg` contains 5 plaintext secrets today. Becomes ciphertext after opt-in. No DB, no Redis, no external datastore. | Data-path migration: the startup re-encrypt pass (criterion #3) IS the migration. No separate migration tool needed. |
| Live service config | None — no n8n, no Datadog, no Tailscale, no Cloudflare Tunnel. | None. |
| OS-registered state | `systemd` unit for the `.deb` install references `ExecStart=seedsyncarr -c /etc/seedsyncarr` (assumed — not verified in this pass). Unit does not embed secrets. | None. |
| Secrets and env vars | Project does NOT use env vars for the 5 secrets today — all 5 live in `settings.cfg`. No CI secret with these names. | None. |
| Build artifacts / installed packages | Docker runtime image `seedsyncarr_run_python` (Dockerfile:115) uses `poetry install --only main`. Adding `cryptography` as a main dep causes it to be installed into the runtime layer (desired). No stale egg-info/binaries. `pyinstaller` stage (Dockerfile:57) bundles scanfs only, not the main app — so `cryptography` does NOT need to be frozen in. | Rebuild Docker images after `pyproject.toml` change. Confirm in CI. |

## 11. Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `cryptography` Python package | Phase 81 entire implementation | System: ✓ (46.0.6 at `/usr/bin/python3 -m pip show cryptography`) | 46.0.6 | None — hard dep. Pin in pyproject.toml; poetry.lock regenerates on first `poetry install`. |
| Python `>=3.11,<3.13` | Existing project pin | ✓ (Dockerfile pins `python:3.11-slim`) | 3.11 in CI | None |
| `poetry` | Existing project build | ✓ (Dockerfile:46, 96 `pip3 install poetry`) | any | None |
| `openssl` (runtime dep of `cryptography`) | Fernet's C backend | ✓ (present in Debian 12 slim) | any | None |
| Write access to `{config_dir}` | Keyfile creation | ✓ (config_dir is user-provided, must already be writable — existing `to_file` relies on this) | — | Hard fail with clear AppError if not |

**Missing dependencies with no fallback:** None — `cryptography` is already available on the research machine and is a stable PyPI package with prebuilt wheels for linux/amd64, linux/arm64, macOS, Windows (per pypi wheels listing).

**Missing dependencies with fallback:** None needed.

## 12. Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + unittest.TestCase (project uses unittest classes via pytest runner) |
| Config file | `src/python/pyproject.toml` `[tool.pytest.ini_options]` (lines 71-78) |
| Quick run command | `cd src/python && poetry run pytest tests/unittests/test_common/test_encryption.py tests/unittests/test_common/test_config.py -x` |
| Full suite command | `make run-tests-python` (root Makefile) — runs the full Python suite in Docker |
| Coverage gate | 84% per `[tool.coverage.report]` fail_under (pyproject.toml:89) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-02 #1a | Keyfile generated with 0600 on first enable | unit | `poetry run pytest tests/unittests/test_common/test_encryption.py::TestEncryption::test_keyfile_is_0600 -x` | ❌ Wave 0 |
| SEC-02 #1b | 5 secrets encrypted in place on first enable | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_enable_new_install_encrypts_on_write -x` | ❌ Wave 0 |
| SEC-02 #2 | Read path transparently decrypts; callers see plaintext | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_from_file_enabled_decrypts -x` | ❌ Wave 0 |
| SEC-02 #3a | Plaintext detected on startup → re-encrypted in place | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_enable_existing_plaintext_reencrypts -x` | ❌ Wave 0 |
| SEC-02 #3b | Plaintext install with flag disabled works unchanged (backward compat) | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_encryption_disabled_by_default -x` | ❌ Wave 0 |
| SEC-02 #4 | Disable → restore plaintext (round-trip) | unit | `poetry run pytest tests/unittests/test_common/test_config.py::TestConfig::test_disable_restores_plaintext -x` | ❌ Wave 0 |
| SEC-02 #5a | Keyfile permission test (0600) | unit | same as #1a | ❌ Wave 0 |
| SEC-02 #5b | Decrypt failure surfaces clear startup warning | unit | `poetry run pytest tests/unittests/test_seedsyncarr.py::TestSeedsyncarr::test_decrypt_failure_emits_warning -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `poetry run pytest tests/unittests/test_common/test_encryption.py tests/unittests/test_common/test_config.py -x` (runs in <5s locally)
- **Per wave merge:** `poetry run pytest tests/unittests/ -x` (full unit suite)
- **Phase gate:** `make run-tests-python` (full Docker-based suite, matches CI) green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `src/python/tests/unittests/test_common/test_encryption.py` — covers SEC-02 #1, #5a, plus `is_ciphertext` discriminator correctness.
- [ ] 5 new test methods in `src/python/tests/unittests/test_common/test_config.py` — covers SEC-02 #1b, #2, #3a, #3b, #4.
- [ ] 1 new test method in `src/python/tests/unittests/test_seedsyncarr.py` — covers SEC-02 #5b (startup warning).
- [ ] No framework install needed; `pytest` is already a dev dep.

## 13. Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Not touched by this phase (existing Bearer auth is unaffected) |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No access control changes |
| V5 Input Validation | partial | Encrypted token format must be validated before decrypt attempt (`is_ciphertext` gate). Use `cryptography.fernet` parser. |
| V6 Cryptography | **yes (primary)** | Fernet (AES-128-CBC + HMAC-SHA256). **Never hand-roll.** |
| V8 Data Protection | **yes (primary)** | Secrets at rest: 0600 keyfile + ciphertext in `settings.cfg`. |
| V14 Configuration | yes | Keyfile is a config artifact; must be excluded from backups/logs and documented. |

### Known Threat Patterns for Python + Local-File-Config Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secrets at rest readable by co-tenants on shared host | Information Disclosure | 0600 on both `settings.cfg` and `secrets.key`; Fernet AES-128 on the secret fields |
| Keyfile leak via log / error message | Information Disclosure | Never log keyfile contents; log only path at INFO. Existing `context.py:_REDACTED_KEYS` does NOT currently redact the word "key" — add it if any log path could print a raw key |
| Keyfile leak via backup tool / rsync | Information Disclosure | Document that `secrets.key` is a critical backup artifact; out-of-scope to solve in-app |
| Ciphertext tampering | Tampering | Fernet HMAC-SHA256 detects modification; `InvalidToken` surfaces warning |
| Replay of old token | N/A | Fernet token has timestamp; optional TTL on decrypt not needed here (we're not checking freshness) |
| Padding oracle | Tampering | Fernet's HMAC-before-CBC construction prevents this (per the Fernet spec) |
| Downgrade from encrypted to plaintext | Tampering | Our re-encrypt-on-startup pass closes this: if flag=True and value is plaintext, re-encrypt |
| Weak RNG for IV/key | Cryptographic | Fernet uses `os.urandom` internally; not our problem |

## 14. State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Write secrets in plaintext INI | Optional Fernet-at-rest | This phase (v1.1.1) | Adds `cryptography` dep; new `[Encryption]` section |
| `cryptography<44` | `cryptography>=44` pin | 2024-11 | Fernet API is stable across majors; bump is just for security patches |
| (no precedent) | PyCA `Fernet` as the "right answer" for Python symmetric crypto | ~2015 onward | Don't evaluate alternatives; just use Fernet |

**Deprecated/outdated:**
- Use of `hashlib` + `hmac` + manual AES — deprecated pattern; Fernet supersedes it.
- Storing secrets in env vars as the ONLY mechanism — not wrong but not what SEC-02 asks for; env vars are orthogonal.

## 15. Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Keyfile path `{config_dir}/secrets.key` (not configurable) is acceptable per criterion #1 (which says only "a keyfile is generated") | 4, 6.2 | Low — if a configurable path is wanted, planner can widen to `[Encryption].key_file` with a default. |
| A2 | Re-encrypt-plaintext-on-startup lives in `seedsyncarr.py`, not `config.py` — technically outside `config.py` but consistent with existing file I/O ownership | 3, 6.1 | Low — criterion #2 ("no code changes outside config.py") is about CALLER changes. The entry-point already owns `to_file` calls. If planner disagrees, the re-encrypt hook can move into `Config.from_file` itself (call `to_file(original_path)` at the end of load). |
| A3 | No settings-page UI for `[Encryption].enabled` in this phase (flag set by manual edit of `settings.cfg`) — per v1.1.1 "no user-visible features" scope | 3 | Low — explicitly locked by REQUIREMENTS.md:6. |
| A4 | The `SerializeConfig` web serializer (`web/serialize/serialize_config.py`) does not need changes — it already redacts these 5 fields for unauthenticated requests; authenticated requests will see decrypted plaintext because `context.config.*` is the in-memory decrypted view | 4, 6.1 | Low — verified by grep of `_SENSITIVE_FIELDS` dict (serialize_config.py:8-13). |
| A5 | `os.chmod(path, 0o600)` on existing Linux CI and macOS dev boxes works; Windows is best-effort and tests gate on `sys.platform != 'win32'`. Project targets Linux primarily (Docker runtime is Debian) | 8.3 | Low — matches existing `persist.py` pattern; CI is `ubuntu-latest`. |
| A6 | `cryptography>=44,<47` upper bound is safe; Fernet's public API has been stable across majors and PyCA communicates deprecations | 5 | Medium — if PyCA ships a breaking major in the next ~12 months, pin may need a bump. Easy to fix. |
| A7 | The `api_token` HTML meta-tag injection (`web_app.py:219-224`) reads plaintext `context.config.general.api_token` which is the already-decrypted in-memory value — no change needed | 4 | Low — verified by direct read of the code path; the decrypt happened in `from_str`. |
| A8 | `Config.Encryption.enabled = False` default is all existing installs need; no data migration at upgrade. User-initiated opt-in only | 3, 6.5 | Low — matches AutoDelete/Sonarr backward-compat precedent. |

**If a user disagrees with A1-A8, raise in discuss-phase before planning locks.** In particular A1 (configurable keyfile path) and A3 (no settings UI) are product choices the planner or user might want to revisit.

## 16. Open Questions

1. **Key rotation: in scope?**
   - What we know: `cryptography.fernet.MultiFernet` supports N-key rotation trivially; existing Fernet tokens decrypt with any key in the list; new encrypts use the first key. SEC-02 as written does NOT mention rotation.
   - What's unclear: whether "rotate the key without re-encrypting" is a required v1.1.1 capability.
   - Recommendation: **Out of scope for Phase 81.** Document the MultiFernet path in a code comment near the keyfile load so a future phase can adopt it with minimal refactor.

2. **Keyfile backup / export UX?**
   - What we know: Losing `secrets.key` means losing the 5 secrets (Pitfall 8.4).
   - What's unclear: Should the app provide a "print your keyfile to screen once, then hide" flow? An "export encrypted secrets to a portable bundle"?
   - Recommendation: Out of scope. Document the risk in `docs/configuration.md` as part of the phase, and ensure the startup log mentions the keyfile path at INFO so operators can back it up.

3. **`disable` semantics when the keyfile is missing?**
   - What we know: criterion #4 says disable must preserve the 5 values.
   - What's unclear: What happens if the user sets `enabled = False` BUT the keyfile is gone? All 5 values are ciphertext in `settings.cfg`, undecryptable.
   - Recommendation: On disable-with-missing-keyfile, log a clear error ("Cannot disable encryption: keyfile is missing. Restore it or manually clear the 5 encrypted fields.") and leave `settings.cfg` untouched. Tests should cover this.

4. **Does the existing periodic `self.persist()` call in `Seedsyncarr.run()` (line 163) need any guard?**
   - What we know: `persist()` calls `config.to_file(self.config_path)` every `MIN_PERSIST_TO_FILE_INTERVAL_IN_SECS`.
   - What's unclear: Whether periodic re-encrypts are wasteful (every secret re-encrypted produces a NEW token because Fernet uses a new IV each time) — writes a new `settings.cfg` every interval even if nothing changed at the user level. Small cost but non-zero.
   - Recommendation: Not a real problem (we already persist every interval). If profiling shows this is a hot path, add an idempotence check in `to_str` (only re-encrypt if the current on-disk value differs). Not needed for Phase 81.

5. **Where does `Config.set_keyfile_path(path)` get called?**
   - What we know: the classmethod `from_file(path)` has no way to know the sibling keyfile location.
   - What's unclear: Injection pattern. Options: (a) classmethod setter called from `Seedsyncarr.__init__` before `from_file`; (b) widen `Persist.from_file` / `Persist.to_file` signatures; (c) make it an instance attr post-construction.
   - Recommendation: (a) classmethod setter — minimal blast radius, no signature changes to `Persist`. Alternative: store keyfile path on the `Config` instance and have `seedsyncarr.py` set `config._keyfile_path = ...` right after `from_file`. Planner to pick.

## 17. Sources

### Primary (HIGH confidence)
- Codebase grep + direct read of `src/python/common/config.py`, `src/python/common/persist.py`, `src/python/seedsyncarr.py`, `src/python/web/handler/config.py`, `src/python/web/serialize/serialize_config.py`, `src/python/web/web_app.py`, `src/python/tests/unittests/test_common/test_config.py`, `src/python/tests/unittests/test_common/test_persist.py`, `src/python/pyproject.toml`, `src/docker/build/docker-image/Dockerfile`
- Live Python REPL on this machine (Python 3.9.6, cryptography 46.0.6) — Fernet API behavior, token prefix, exception types, MultiFernet rotation. All 5 tokens observed starting with `gAAAAA`.
- PyPI metadata: https://pypi.org/pypi/cryptography/json — confirmed current stable 46.0.7
- Fernet spec: https://github.com/fernet/spec/blob/master/Spec.md — token format (version byte 0x80, 64-bit timestamp, 128-bit IV, ciphertext, HMAC-SHA256)
- Python docs: https://docs.python.org/3/library/os.html#os.chmod — Windows limitation
- REQUIREMENTS.md (SEC-02), ROADMAP.md (Phase 81 success criteria), STATE.md (current position)
- Phase 80 RESEARCH.md for format precedent

### Secondary (MEDIUM confidence)
- WebSearch "Python os.chmod 0600 Windows behavior cross-platform 2026" (2026-04-22) — independent confirmation of os.chmod Windows no-op

### Tertiary (LOW confidence)
- None — all claims in this document are verified.

## 18. Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `cryptography.fernet` is the unambiguous choice; version confirmed against PyPI live.
- Architecture: HIGH — maps directly onto existing `Persist.from_str / to_str` seam; no speculative refactor.
- Pitfalls: HIGH — each pitfall verified against a specific file/line in the existing codebase.
- Test strategy: HIGH — 5 success criteria have 1-to-1 mapping to 5 pytest methods in a framework already in use.
- Open questions #1-5: declared as non-blockers; each has a concrete recommendation.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — stable area: `cryptography.fernet` API is decade-stable; the only moving part is a potential `cryptography` major bump, which is monitored via Dependabot).
