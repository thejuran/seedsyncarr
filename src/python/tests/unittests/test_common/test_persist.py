import errno
import os
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch

from common import overrides, Persist, AppError, Localization, ServiceExit


# Captured before any test patches os.fsync, so the side-effect helpers below
# can fall through to the real call for the descriptors they do not target.
_real_fsync = os.fsync


def _fail_on_regular_file(fd):
    if stat.S_ISREG(os.fstat(fd).st_mode):
        raise OSError(errno.EIO, "injected file fsync failure")
    return _real_fsync(fd)


def _fail_on_directory(fd):
    if stat.S_ISDIR(os.fstat(fd).st_mode):
        raise OSError(errno.EINVAL, "injected dir fsync failure")
    return _real_fsync(fd)


def _interrupt_on_regular_file(fd):
    if stat.S_ISREG(os.fstat(fd).st_mode):
        raise ServiceExit()
    return _real_fsync(fd)


class DummyPersist(Persist):
    def __init__(self):
        self.my_content = None

    @classmethod
    @overrides(Persist)
    def from_str(cls: "DummyPersist", content: str) -> "DummyPersist":
        persist = DummyPersist()
        persist.my_content = content
        return persist

    @overrides(Persist)
    def to_str(self) -> str:
        return self.my_content


class FailingToStrPersist(DummyPersist):
    @overrides(DummyPersist)
    def to_str(self) -> str:
        raise ValueError("injected serialization failure")


class TestPersist(unittest.TestCase):
    @overrides(unittest.TestCase)
    def setUp(self):
        # Create a temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="test_persist")

    @overrides(unittest.TestCase)
    def tearDown(self):
        # Cleanup
        shutil.rmtree(self.temp_dir)

    def test_from_file(self):
        file_path = os.path.join(self.temp_dir, "persist")
        with open(file_path, "w") as f:
            f.write("some test content")
        persist = DummyPersist.from_file(file_path)
        self.assertEqual("some test content", persist.my_content)

    def test_from_file_non_existing(self):
        file_path = os.path.join(self.temp_dir, "persist")
        with self.assertRaises(AppError) as context:
            DummyPersist.from_file(file_path)
        self.assertEqual(Localization.Error.MISSING_FILE.format(file_path), str(context.exception))

    def test_to_file_non_existing(self):
        file_path = os.path.join(self.temp_dir, "persist")
        persist = DummyPersist()
        persist.my_content = "write out some content"
        persist.to_file(file_path)
        self.assertTrue(os.path.isfile(file_path))
        with open(file_path, "r") as f:
            self.assertEqual("write out some content", f.read())

    def test_to_file_overwrite(self):
        file_path = os.path.join(self.temp_dir, "persist")
        with open(file_path, "w") as f:
            f.write("pre-existing content")
            f.flush()
        persist = DummyPersist()
        persist.my_content = "write out some new content"
        persist.to_file(file_path)
        self.assertTrue(os.path.isfile(file_path))
        with open(file_path, "r") as f:
            self.assertEqual("write out some new content", f.read())

    def test_to_file_sets_0600_permissions(self):
        file_path = os.path.join(self.temp_dir, "persist_perms")
        persist = DummyPersist()
        persist.my_content = "sensitive content"
        persist.to_file(file_path)
        mode = os.stat(file_path).st_mode & 0o777
        self.assertEqual(0o600, mode, f"Expected 0600 permissions, got {oct(mode)}")

    def test_from_file_tightens_permissive_permissions(self):
        file_path = os.path.join(self.temp_dir, "persist_tighten")
        with open(file_path, "w") as f:
            f.write("some content")
        os.chmod(file_path, 0o644)
        DummyPersist.from_file(file_path)
        mode = os.stat(file_path).st_mode & 0o777
        self.assertEqual(0o600, mode, f"Expected 0600 permissions after from_file(), got {oct(mode)}")

    def test_to_file_overwrite_preserves_0600_permissions(self):
        file_path = os.path.join(self.temp_dir, "persist_overwrite_perms")
        persist = DummyPersist()
        persist.my_content = "first write"
        persist.to_file(file_path)
        mode = os.stat(file_path).st_mode & 0o777
        self.assertEqual(0o600, mode, f"Expected 0600 after first write, got {oct(mode)}")
        persist.my_content = "second write"
        persist.to_file(file_path)
        mode = os.stat(file_path).st_mode & 0o777
        self.assertEqual(0o600, mode, f"Expected 0600 after overwrite, got {oct(mode)}")
        with open(file_path, "r") as f:
            self.assertEqual("second write", f.read())


class TestPersistAtomicWrite(unittest.TestCase):
    """
    Pins the atomic-save contract of Persist.to_file:

    - a failure at any point before the file is committed (serialization, temp
      file creation, write, file fsync, replace, or an interrupt such as
      ServiceExit) leaves the original file intact byte-for-byte, leaves no
      temp file behind, and raises the original exception type unwrapped;
    - a directory fsync failure after the commit point is logged as a warning
      on seedsyncarr.Persist and not raised; the new file stays committed with
      0600 permissions and the warning never contains the file content.

    Failures are injected through the global os.fsync / os.replace /
    tempfile.mkstemp attributes, which Persist.to_file resolves at call time.
    """

    ORIGINAL = b"ORIGINAL"
    NEW_CONTENT = "NEW CONTENT"

    @overrides(unittest.TestCase)
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_persist_atomic")
        self.path = os.path.join(self.temp_dir, "persist")

    @overrides(unittest.TestCase)
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _seed(self, path: str, data: bytes):
        with open(path, "wb") as f:
            f.write(data)

    def _new_persist(self, content: str = NEW_CONTENT) -> DummyPersist:
        persist = DummyPersist()
        persist.my_content = content
        return persist

    def _assert_original_and_clean(self, path: str):
        with open(path, "rb") as f:
            self.assertEqual(self.ORIGINAL, f.read(), "original file must be intact byte-for-byte")
        self.assertEqual(["persist"], sorted(os.listdir(self.temp_dir)), "no temp file may be left behind")

    def test_serialization_failure_leaves_original_and_no_temp(self):
        self._seed(self.path, self.ORIGINAL)
        persist = FailingToStrPersist()
        with self.assertRaises(ValueError):
            persist.to_file(self.path)
        self._assert_original_and_clean(self.path)

    def test_write_failure_leaves_original_and_no_temp(self):
        self._seed(self.path, self.ORIGINAL)
        # A lone surrogate cannot be encoded as UTF-8, so the text write itself
        # raises UnicodeEncodeError without any mocking.
        persist = self._new_persist("ok \udc80 tail")
        with self.assertRaises(UnicodeEncodeError):
            persist.to_file(self.path)
        self._assert_original_and_clean(self.path)

    def test_file_fsync_failure_leaves_original_and_no_temp(self):
        self._seed(self.path, self.ORIGINAL)
        persist = self._new_persist()
        with patch("os.fsync", side_effect=_fail_on_regular_file):
            with self.assertRaises(OSError):
                persist.to_file(self.path)
        self._assert_original_and_clean(self.path)

    def test_replace_failure_leaves_original_and_no_temp(self):
        self._seed(self.path, self.ORIGINAL)
        persist = self._new_persist()
        with patch("os.replace", side_effect=OSError(errno.EACCES, "injected replace failure")):
            with self.assertRaises(OSError):
                persist.to_file(self.path)
        self._assert_original_and_clean(self.path)

    def test_temp_creation_failure_leaves_original_and_no_temp(self):
        self._seed(self.path, self.ORIGINAL)
        persist = self._new_persist()
        with patch("tempfile.mkstemp", side_effect=OSError(errno.ENOSPC, "injected temp creation failure")):
            with self.assertRaises(OSError):
                persist.to_file(self.path)
        self._assert_original_and_clean(self.path)

    def test_failure_with_no_existing_target_leaves_directory_empty(self):
        persist = self._new_persist()
        with patch("os.replace", side_effect=OSError(errno.EACCES, "injected replace failure")):
            with self.assertRaises(OSError):
                persist.to_file(self.path)
        self.assertEqual([], os.listdir(self.temp_dir), "a failed first save must leave nothing behind")

    def test_interrupt_mid_write_cleans_up_and_preserves_original(self):
        self._seed(self.path, self.ORIGINAL)
        persist = self._new_persist()
        with patch("os.fsync", side_effect=_interrupt_on_regular_file):
            with self.assertRaises(ServiceExit):
                persist.to_file(self.path)
        self._assert_original_and_clean(self.path)

    def test_directory_fsync_failure_is_logged_not_raised_and_file_committed(self):
        self._seed(self.path, self.ORIGINAL)
        persist = self._new_persist()
        with patch("os.fsync", side_effect=_fail_on_directory):
            with self.assertLogs("seedsyncarr.Persist", level="WARNING") as cm:
                persist.to_file(self.path)
        with open(self.path, "rb") as f:
            self.assertEqual(self.NEW_CONTENT.encode("utf-8"), f.read())
        self.assertEqual(["persist"], sorted(os.listdir(self.temp_dir)))
        self.assertEqual(0o600, os.stat(self.path).st_mode & 0o777)
        for line in cm.output:
            self.assertNotIn(self.NEW_CONTENT, line, "file content must never appear in logs")

    def test_temp_file_created_in_same_directory_as_target(self):
        self._seed(self.path, self.ORIGINAL)
        persist = self._new_persist()
        with patch("tempfile.mkstemp", wraps=tempfile.mkstemp) as spy:
            persist.to_file(self.path)
        spy.assert_called_once()
        self.assertEqual(os.path.dirname(os.path.realpath(self.path)), spy.call_args.kwargs["dir"])

    def test_no_temp_after_success(self):
        self._seed(self.path, self.ORIGINAL)
        persist = self._new_persist()
        persist.to_file(self.path)
        with open(self.path, "r") as f:
            self.assertEqual(self.NEW_CONTENT, f.read())
        self.assertEqual(["persist"], sorted(os.listdir(self.temp_dir)))
        self.assertEqual(0o600, os.stat(self.path).st_mode & 0o777)
