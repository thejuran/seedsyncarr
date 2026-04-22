import unittest
import tempfile
import shutil
import os
import sys

from common.encryption import load_or_create_key, is_ciphertext, encrypt_field, decrypt_field, EncryptionError, DecryptionError


class TestEncryption(unittest.TestCase):
    def setUp(self):
        # Create a temp directory per test — matches test_persist.py:25-34 pattern
        self.temp_dir = tempfile.mkdtemp(prefix="test_encryption")
        self.keyfile = os.path.join(self.temp_dir, "secrets.key")

    def tearDown(self):
        # Cleanup — matches test_persist.py:31-34 pattern
        shutil.rmtree(self.temp_dir)

    # ── Task: 81-01-01 ────────────────────────────────────────────────────────

    def test_key_generated_on_first_call(self):
        """Keyfile does not exist before first call; load_or_create_key creates it
        and returns exactly 44 bytes (the url-safe-base64 Fernet key)."""
        self.assertFalse(os.path.isfile(self.keyfile))
        key = load_or_create_key(self.keyfile)
        self.assertTrue(os.path.isfile(self.keyfile))
        self.assertEqual(44, len(key))

    @unittest.skipIf(sys.platform == "win32", "POSIX permission bits only")
    def test_keyfile_is_0600(self):
        """Created keyfile must have exactly 0600 permissions on POSIX systems.

        Maps to VALIDATION task 81-01-01 (SEC-02 #1a / #5a).
        Skipped on Windows because os.chmod only toggles the read-only flag there.
        """
        load_or_create_key(self.keyfile)
        mode = os.stat(self.keyfile).st_mode & 0o777
        self.assertEqual(0o600, mode, f"Expected 0600 permissions, got {oct(mode)}")

    @unittest.skipIf(sys.platform == "win32", "POSIX permission bits only")
    def test_load_tightens_existing_keyfile_permissions(self):
        """If a keyfile already exists at 0644, load_or_create_key must re-tighten
        its permissions to 0600 on load — matches persist.py:from_file:43 pattern."""
        # Pre-create keyfile at 0644 with 44 bytes of content.
        # Note: these 44 b'a' bytes are NOT a valid Fernet key; load_or_create_key
        # only reads + strips, so validation is deferred to actual Fernet(key)
        # construction — which this test deliberately does not exercise.
        with open(self.keyfile, "wb") as f:
            f.write(b"a" * 44)
        os.chmod(self.keyfile, 0o644)
        # Confirm setup
        mode_before = os.stat(self.keyfile).st_mode & 0o777
        self.assertEqual(0o644, mode_before)
        # Load — should tighten to 0600
        load_or_create_key(self.keyfile)
        mode_after = os.stat(self.keyfile).st_mode & 0o777
        self.assertEqual(0o600, mode_after, f"Expected 0600 after load, got {oct(mode_after)}")

    def test_round_trip(self):
        """encrypt_field then decrypt_field returns original plaintext.

        Also exercises the real load_or_create_key code path (not Fernet.generate_key
        directly) to confirm the full encrypt/decrypt pipeline works end-to-end.
        """
        key = load_or_create_key(self.keyfile)
        token = encrypt_field(key, "my_password")
        self.assertTrue(is_ciphertext(token))
        self.assertEqual("my_password", decrypt_field(key, token))

    def test_is_ciphertext_rejects_plaintext(self):
        """is_ciphertext returns False for empty string, short strings, a gAAAAA-prefixed
        but too-short string, and a long string without the correct prefix."""
        self.assertFalse(is_ciphertext(""))
        self.assertFalse(is_ciphertext("short"))
        self.assertFalse(is_ciphertext("gAAAAA_short"))
        self.assertFalse(is_ciphertext("not_a_token_but_long_enough_" * 10))

    def test_is_ciphertext_accepts_real_token(self):
        """is_ciphertext returns True for an actual Fernet-encrypted token.

        Maps to VALIDATION task 81-01-02 (SEC-02 discriminator correctness).
        """
        key = load_or_create_key(self.keyfile)
        token = encrypt_field(key, "secret_value")
        self.assertTrue(is_ciphertext(token))

    def test_decrypt_wrong_key_raises_decryption_error(self):
        """Decrypting a token with a different key must raise DecryptionError,
        never the raw cryptography.fernet.InvalidToken.

        Simulates keyfile loss by removing the keyfile and creating a new one
        (which generates a different key), then attempting to decrypt the old token.
        """
        key1 = load_or_create_key(self.keyfile)
        token = encrypt_field(key1, "secret")
        # Simulate keyfile loss — delete and recreate with a new random key
        os.remove(self.keyfile)
        key2 = load_or_create_key(self.keyfile)
        self.assertNotEqual(key1, key2, "New key should differ from original")
        self.assertRaises(DecryptionError, decrypt_field, key2, token)

    def test_decrypt_garbage_token_raises_decryption_error(self):
        """Feeding a valid-looking but corrupt token to decrypt_field must raise
        DecryptionError, never the raw InvalidToken from the PyCA library."""
        key = load_or_create_key(self.keyfile)
        # "gAAAAA" + 194 'A' chars = 200 chars total (valid base64 padding),
        # passes the is_ciphertext gates but will fail HMAC verification inside Fernet.
        garbage_token = "gAAAAA" + "A" * 194
        self.assertTrue(is_ciphertext(garbage_token), "precondition: garbage token must pass is_ciphertext")
        self.assertRaises(DecryptionError, decrypt_field, key, garbage_token)

    def test_encrypt_bad_key_raises_encryption_error(self):
        """encrypt_field must raise EncryptionError (not DecryptionError) when the
        key is malformed — e.g. a truncated or non-base64 keyfile."""
        bad_key = b"not_a_valid_fernet_key"
        with self.assertRaises(EncryptionError):
            encrypt_field(bad_key, "any_plaintext")

    def test_is_ciphertext_rejects_short_decoded_length(self):
        """is_ciphertext must return False for a string that passes the prefix and
        length gates but whose decoded content is under the 73-byte Fernet minimum.

        'gAAAAA' + 'A'*90 + '====' = 100 chars, valid url-safe base64,
        decodes to 72 bytes — one byte below the 73-byte threshold.
        """
        short_decoded = "gAAAAA" + "A" * 90 + "===="
        self.assertEqual(100, len(short_decoded))
        self.assertFalse(is_ciphertext(short_decoded))
