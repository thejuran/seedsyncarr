import os
import base64
import binascii
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from .error import AppError

# Module-level constants for the Fernet token discriminator.
# Every Fernet token's first 6 characters are deterministically "gAAAAA"
# (derived from version byte 0x80 + 64-bit timestamp whose upper bytes are zero
# until year 2106). A minimum length of 100 characters gates the b64 decode for
# performance — see RESEARCH §6.4 and threat model T-81-01-05.
_FERNET_TOKEN_PREFIX = "gAAAAA"
_FERNET_TOKEN_MIN_LEN = 100

# Fernet tokens are version(1) + timestamp(8) + IV(16) + ciphertext(>=16) +
# HMAC(32) = 73+ bytes raw, which base64-encodes to ceil(73/3)*4 = 100+ chars.
# We use 73 as the minimum decoded length to reject truncated tokens early.
_FERNET_TOKEN_MIN_DECODED_LEN = 73


class EncryptionError(AppError):
    """Raised when a Fernet encrypt operation fails (e.g. malformed key)."""
    pass


class DecryptionError(AppError):
    """
    Raised when a Fernet token cannot be decrypted.

    Wraps cryptography.fernet.InvalidToken so that callers never see the raw
    PyCA exception at the module boundary (threat model T-81-01-03, T-81-01-04).
    """
    pass


# ─── Deliberate deviation from persist.py pattern ─────────────────────────────
# persist.py:to_file uses the two-step write-then-chmod pattern (write with
# default umask, then restrict to 0600). For a private keyfile we use the
# stricter os.open(..., O_WRONLY | O_CREAT | O_EXCL, 0o600) atomic approach so
# the file NEVER exists at looser permissions even for a single syscall window.
# The existing-keyfile read branch matches persist.py:40-45 exactly (tighten on
# load, swallow OSError for Windows best-effort per RESEARCH §8.3 / T-81-01-07).
# ──────────────────────────────────────────────────────────────────────────────

def load_or_create_key(keyfile_path: str) -> bytes:
    """
    Return the Fernet key stored at keyfile_path.

    Creates a new 44-byte url-safe-base64 key with 0600 permissions atomically
    if the file does not yet exist.  On every load of an existing keyfile the
    permissions are re-tightened to 0600 (matches Persist.from_file precedent at
    persist.py:43).  On Windows, os.chmod is best-effort (only the read-only ACL
    flag is honored); the project targets Linux (Debian 12 Docker runtime) so
    POSIX semantics are guaranteed in production — see RESEARCH Pitfall 8.3 and
    threat model T-81-01-07.
    """
    if os.path.isfile(keyfile_path):
        # Tighten permissions on every load — matches persist.py:from_file:43.
        try:
            os.chmod(keyfile_path, 0o600)
        except OSError:
            pass  # best-effort on Windows (chmod is a no-op for owner bits)
        with open(keyfile_path, "rb") as f:
            return f.read().strip()

    # First-time creation: use O_EXCL so the file is created directly at 0600,
    # never existing at a world-readable permission even for one syscall.
    # Note: CPython bytes objects are immutable and cannot be zeroed in place;
    # explicit key wiping is not possible without ctypes/mmap (accepted risk).
    key = Fernet.generate_key()  # 44 bytes, url-safe base64, os.urandom-backed
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(keyfile_path, flags, 0o600)
    try:
        os.write(fd, key)
    except BaseException:
        os.close(fd)
        try:
            os.unlink(keyfile_path)
        except OSError:
            pass
        raise
    else:
        os.close(fd)
    # Defensive second chmod — guards against platforms that ignore the mode
    # argument to os.open (e.g. some Windows environments).
    try:
        os.chmod(keyfile_path, 0o600)
    except OSError:
        pass  # best-effort on Windows
    return key


def is_ciphertext(s: Optional[str]) -> bool:
    """
    Best-effort discriminator: returns True iff s has the shape of a Fernet token.

    Gates applied in order (cheapest first per T-81-01-05):
      1. Falsy / non-str  → False
      2. len(s) < 100     → False  (O(1), caps CPU before b64 decode)
      3. prefix != gAAAAA → False
      4. not valid url-safe base64 → False
      5. decoded length < 73 bytes → False  (Fernet minimum: ver+ts+IV+block+HMAC)

    Caveat: a user-chosen plaintext that begins with "gAAAAA" and is ≥100 chars
    of valid base64 is a false positive.  The subsequent decrypt_field call will
    raise DecryptionError and surface a startup warning per RESEARCH §8.2.
    """
    if not s or not isinstance(s, str):
        return False
    if len(s) < _FERNET_TOKEN_MIN_LEN:
        return False
    if not s.startswith(_FERNET_TOKEN_PREFIX):
        return False
    try:
        decoded = base64.urlsafe_b64decode(s.encode("ascii"))
        return len(decoded) >= _FERNET_TOKEN_MIN_DECODED_LEN
    except (ValueError, binascii.Error):
        return False


def encrypt_field(key: bytes, plaintext: str) -> str:
    """
    Encrypt plaintext with key using Fernet (AES-128-CBC + HMAC-SHA256).

    Returns a str-typed Fernet token.  The token always starts with "gAAAAA"
    and is url-safe base64 encoded, making it safe to store in an INI file.

    Raises:
        EncryptionError: if the key is malformed (corrupted or truncated
            keyfile).  The raw ValueError from the Fernet constructor is
            never allowed to escape the module boundary.
    """
    try:
        return Fernet(key).encrypt(plaintext.encode("utf-8")).decode("ascii")
    except ValueError:
        raise EncryptionError(
            "Invalid Fernet key — the keyfile may be corrupted or truncated"
        ) from None


def decrypt_field(key: bytes, token: str) -> str:
    """
    Decrypt a Fernet token produced by encrypt_field.

    Returns the original plaintext string.

    Raises:
        DecryptionError: if the token is invalid, was encrypted with a different
            key, or has been tampered with.  The raw PyCA InvalidToken is never
            allowed to escape the module boundary (T-81-01-03, T-81-01-04).
            The error message is a fixed string and MUST NOT contain token
            contents or key material.
    """
    try:
        return Fernet(key).decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        raise DecryptionError("Failed to decrypt Fernet token") from None
