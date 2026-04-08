# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest
import tempfile
import shutil
import os

from common import overrides, Persist, AppError, Localization


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
