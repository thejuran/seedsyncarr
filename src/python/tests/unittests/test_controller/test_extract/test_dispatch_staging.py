import os
import shutil
import tempfile
import threading
import unittest
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from common import overrides, Constants
from model import ModelFile
from controller.extract import ExtractDispatch, ExtractListener, ExtractError


class RecordingExtractListener(ExtractListener):
    """
    Records, at the moment each notification fires, which of the watched paths
    exist -- so a test can prove the final files were in place (and staging was
    gone) BEFORE extract_completed was delivered.
    """
    def __init__(self, watched_paths):
        self.watched_paths = list(watched_paths)
        self.completed = []  # (name, is_dir, {path: exists})
        self.failed = []
        self.event = threading.Event()

    def _snapshot(self):
        return {path: os.path.exists(path) for path in self.watched_paths}

    @overrides(ExtractListener)
    def extract_completed(self, name: str, is_dir: bool):
        self.completed.append((name, is_dir, self._snapshot()))
        self.event.set()

    @overrides(ExtractListener)
    def extract_failed(self, name: str, is_dir: bool):
        self.failed.append((name, is_dir, self._snapshot()))
        self.event.set()


class TestExtractDispatchStaging(unittest.TestCase):
    """
    Incident 2026-09-16: unrar wrote the mkv straight into the release folder
    and Radarr's completed-download handling imported a 6 GB partial of a
    38.5 GB file ~90 s into a 12-minute extraction. Output must now be
    invisible in the release folder until the archive is fully extracted, then
    appear via an atomic rename.

    Uses one real temp directory as both local_path and out_dir_path (the
    use_local_path_as_extract_path=True layout from the incident) with
    Extract.extract_archive patched to write files the way patool would.
    """

    PARTIAL = b"x" * 1024
    FULL = b"x" * 8192

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="test_dispatch_staging_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.staging_root = os.path.join(self.root, Constants.EXTRACT_STAGING_DIR_NAME)

        is_archive_patcher = patch("controller.extract.dispatch.Extract.is_archive", return_value=True)
        self.addCleanup(is_archive_patcher.stop)
        self.mock_is_archive = is_archive_patcher.start()
        extract_patcher = patch("controller.extract.dispatch.Extract.extract_archive")
        self.addCleanup(extract_patcher.stop)
        self.mock_extract_archive = extract_patcher.start()

        self.dispatch = ExtractDispatch(out_dir_path=self.root, local_path=self.root)
        self.dispatch.logger = MagicMock()
        self.dispatch.start()

    def tearDown(self):
        self.dispatch.stop()

    # --- helpers --------------------------------------------------------------

    def _make_release(self, name, archives=("release.rar",)):
        """
        Create <root>/<name>/<archive> on disk for each archive (which may be a
        relative path like 'ep01/ep01.rar') and the matching ModelFile tree.
        """
        release_dir = os.path.join(self.root, name)
        os.makedirs(release_dir, exist_ok=True)
        root_file = ModelFile(name, True)
        root_file.local_size = 4 * len(archives)
        dir_files = {"": root_file}
        for archive in archives:
            path = os.path.join(release_dir, archive)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"rar!")
            parent = ""
            parts = archive.split("/")
            for part in parts[:-1]:
                child_key = os.path.join(parent, part) if parent else part
                if child_key not in dir_files:
                    dir_file = ModelFile(part, True)
                    dir_file.local_size = 4
                    dir_files[parent].add_child(dir_file)
                    dir_files[child_key] = dir_file
                parent = child_key
            archive_file = ModelFile(parts[-1], False)
            archive_file.local_size = 4
            dir_files[parent].add_child(archive_file)
        return root_file, release_dir

    def _wait(self, listener):
        self.assertTrue(listener.event.wait(5), "listener was never notified")

    def _warnings(self):
        return [str(c.args[0]) for c in self.dispatch.logger.warning.call_args_list if c.args]

    # --- tests ----------------------------------------------------------------

    @pytest.mark.timeout(10)
    def test_output_not_visible_in_release_dir_until_extraction_finishes(self):
        root_file, release_dir = self._make_release("The.Burbs.1989.2160p.UHD.BluRay.x265-B0MBARDiERS")
        final_path = os.path.join(release_dir, "movie.mkv")
        observed = {}

        def _extract(archive_path, out_dir_path):
            # Behave like patool: create the out dir, write a partial file,
            # then finish it. The release folder must not change meanwhile.
            os.makedirs(out_dir_path, exist_ok=True)
            staged = os.path.join(out_dir_path, "movie.mkv")
            with open(staged, "wb") as f:
                f.write(self.PARTIAL)
            observed["final_exists_mid_extract"] = os.path.exists(final_path)
            observed["release_dir_mid_extract"] = sorted(os.listdir(release_dir))
            observed["out_dir_path"] = out_dir_path
            with open(staged, "ab") as f:
                f.write(self.FULL[len(self.PARTIAL):])
        self.mock_extract_archive.side_effect = _extract

        listener = RecordingExtractListener([final_path, self.staging_root])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        # Mid-extraction: nothing new in the release folder, output lives in staging
        self.assertFalse(observed["final_exists_mid_extract"])
        self.assertEqual(["release.rar"], observed["release_dir_mid_extract"])
        self.assertEqual(
            os.path.join(self.staging_root, "The.Burbs.1989.2160p.UHD.BluRay.x265-B0MBARDiERS"),
            observed["out_dir_path"]
        )
        # extract_completed fired once, AFTER the move: full file in place, staging gone
        self.assertEqual([], listener.failed)
        self.assertEqual(1, len(listener.completed))
        name, is_dir, existed = listener.completed[0]
        self.assertEqual("The.Burbs.1989.2160p.UHD.BluRay.x265-B0MBARDiERS", name)
        self.assertTrue(is_dir)
        self.assertTrue(existed[final_path])
        self.assertFalse(existed[self.staging_root])
        self.assertEqual(len(self.FULL), os.path.getsize(final_path))
        self.assertEqual(["movie.mkv", "release.rar"], sorted(os.listdir(release_dir)))
        self.assertFalse(os.path.exists(self.staging_root))

    @pytest.mark.timeout(10)
    def test_extract_error_leaves_release_dir_untouched_and_no_staging_residue(self):
        root_file, release_dir = self._make_release("Bad.Release")
        final_path = os.path.join(release_dir, "movie.mkv")

        def _extract(archive_path, out_dir_path):
            os.makedirs(out_dir_path, exist_ok=True)
            with open(os.path.join(out_dir_path, "movie.mkv"), "wb") as f:
                f.write(self.PARTIAL)
            raise ExtractError("CRC failed")
        self.mock_extract_archive.side_effect = _extract

        listener = RecordingExtractListener([final_path, self.staging_root])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        self.assertEqual([], listener.completed)
        self.assertEqual(1, len(listener.failed))
        _, _, existed = listener.failed[0]
        self.assertFalse(existed[final_path])
        self.assertFalse(existed[self.staging_root])
        self.assertEqual(["release.rar"], sorted(os.listdir(release_dir)))
        self.assertFalse(os.path.exists(self.staging_root))
        discard_logs = [m for m in self._warnings() if m.startswith("Discarded partial extraction output of ")]
        self.assertEqual(1, len(discard_logs))
        self.assertIn("removed 1 file(s) ['movie.mkv']", discard_logs[0])

    @pytest.mark.timeout(10)
    def test_existing_target_is_replaced_by_newly_extracted_copy(self):
        root_file, release_dir = self._make_release("Re.Extract")
        final_path = os.path.join(release_dir, "movie.mkv")
        # e.g. the truncated file left behind by a pre-fix in-place extraction
        with open(final_path, "wb") as f:
            f.write(b"old truncated copy")

        def _extract(archive_path, out_dir_path):
            os.makedirs(out_dir_path, exist_ok=True)
            with open(os.path.join(out_dir_path, "movie.mkv"), "wb") as f:
                f.write(self.FULL)
        self.mock_extract_archive.side_effect = _extract

        listener = RecordingExtractListener([final_path])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        self.assertEqual(1, len(listener.completed))
        with open(final_path, "rb") as f:
            self.assertEqual(self.FULL, f.read())
        self.assertIn(
            "Replacing existing '{}' with the newly extracted copy".format(final_path),
            self._warnings()
        )

    @pytest.mark.timeout(10)
    def test_extracted_directory_merges_into_existing_directory(self):
        root_file, release_dir = self._make_release("Merge.Subs")
        existing = os.path.join(release_dir, "Subs", "existing.srt")
        os.makedirs(os.path.dirname(existing))
        with open(existing, "wb") as f:
            f.write(b"existing")
        extracted = os.path.join(release_dir, "Subs", "new.srt")

        def _extract(archive_path, out_dir_path):
            os.makedirs(os.path.join(out_dir_path, "Subs"))
            with open(os.path.join(out_dir_path, "Subs", "new.srt"), "wb") as f:
                f.write(b"new")
        self.mock_extract_archive.side_effect = _extract

        listener = RecordingExtractListener([extracted])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        self.assertEqual(1, len(listener.completed))
        self.assertTrue(os.path.isfile(existing))
        self.assertTrue(os.path.isfile(extracted))
        self.assertFalse(os.path.exists(self.staging_root))
        self.assertEqual([], self._warnings())

    @pytest.mark.timeout(10)
    def test_extracted_file_replaces_existing_directory_of_same_name(self):
        # Type clash: a directory already occupies the extracted file's name in
        # the release folder. os.replace cannot put a file over a directory, so
        # the publish step must remove the directory first (dispatch.py's
        # shutil.rmtree(dst) branch -- the one place it deletes a release-dir
        # path that it did not create).
        root_file, release_dir = self._make_release("Type.Clash")
        final_path = os.path.join(release_dir, "movie.mkv")
        os.makedirs(os.path.join(final_path, "stale"))
        with open(os.path.join(final_path, "stale", "leftover.bin"), "wb") as f:
            f.write(b"leftover")

        def _extract(archive_path, out_dir_path):
            os.makedirs(out_dir_path, exist_ok=True)
            with open(os.path.join(out_dir_path, "movie.mkv"), "wb") as f:
                f.write(self.FULL)
        self.mock_extract_archive.side_effect = _extract

        listener = RecordingExtractListener([final_path, self.staging_root])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        self.assertEqual([], listener.failed)
        self.assertEqual(1, len(listener.completed))
        self.assertTrue(os.path.isfile(final_path))
        with open(final_path, "rb") as f:
            self.assertEqual(self.FULL, f.read())
        self.assertEqual(["movie.mkv", "release.rar"], sorted(os.listdir(release_dir)))
        self.assertFalse(os.path.exists(self.staging_root))
        self.assertIn(
            "Replacing existing '{}' with the newly extracted copy".format(final_path),
            self._warnings()
        )

    @pytest.mark.timeout(10)
    def test_extracted_directory_replaces_existing_file_of_same_name(self):
        # The reverse type clash: a stray plain file already occupies the name
        # of the archive's top-level directory in the release folder. os.replace
        # cannot put a directory over a file, so the publish step must remove
        # the file first. The newly extracted copy is authoritative.
        root_file, release_dir = self._make_release("Reverse.Clash")
        final_dir = os.path.join(release_dir, "Subs")
        with open(final_dir, "wb") as f:
            f.write(b"stray file where a directory belongs")

        def _extract(archive_path, out_dir_path):
            os.makedirs(os.path.join(out_dir_path, "Subs"), exist_ok=True)
            with open(os.path.join(out_dir_path, "Subs", "movie.srt"), "wb") as f:
                f.write(self.FULL)
        self.mock_extract_archive.side_effect = _extract

        listener = RecordingExtractListener([final_dir, self.staging_root])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        self.assertEqual([], listener.failed)
        self.assertEqual(1, len(listener.completed))
        self.assertTrue(os.path.isdir(final_dir))
        self.assertEqual(["movie.srt"], os.listdir(final_dir))
        with open(os.path.join(final_dir, "movie.srt"), "rb") as f:
            self.assertEqual(self.FULL, f.read())
        self.assertEqual(["Subs", "release.rar"], sorted(os.listdir(release_dir)))
        self.assertFalse(os.path.exists(self.staging_root))
        self.assertIn(
            "Replacing existing '{}' with the newly extracted copy".format(final_dir),
            self._warnings()
        )

    @pytest.mark.timeout(10)
    def test_symlinks_in_extracted_output_are_dropped_before_publish(self):
        # A crafted archive can carry symlinks pointing anywhere. None may reach
        # the arr-visible release folder: top-level and nested symlinks (to a
        # file, to a directory, dangling) are all removed with a warning, the
        # real files are published, and no staging residue remains.
        root_file, release_dir = self._make_release("Sym.Link")
        final_path = os.path.join(release_dir, "movie.mkv")
        subs_dir = os.path.join(release_dir, "Subs")
        outside_dir = os.path.join(self.root, "outside")
        os.makedirs(outside_dir)

        def _extract(archive_path, out_dir_path):
            os.makedirs(os.path.join(out_dir_path, "Subs"), exist_ok=True)
            with open(os.path.join(out_dir_path, "movie.mkv"), "wb") as f:
                f.write(self.FULL)
            with open(os.path.join(out_dir_path, "Subs", "movie.srt"), "wb") as f:
                f.write(b"subs")
            os.symlink("/etc/passwd", os.path.join(out_dir_path, "passwd"))
            os.symlink(outside_dir, os.path.join(out_dir_path, "escape"))
            os.symlink("../nowhere", os.path.join(out_dir_path, "Subs", "dangling"))
        self.mock_extract_archive.side_effect = _extract

        listener = RecordingExtractListener([final_path, self.staging_root])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        self.assertEqual([], listener.failed)
        self.assertEqual(1, len(listener.completed))
        self.assertEqual(["Subs", "movie.mkv", "release.rar"], sorted(os.listdir(release_dir)))
        self.assertEqual(["movie.srt"], os.listdir(subs_dir))
        with open(final_path, "rb") as f:
            self.assertEqual(self.FULL, f.read())
        self.assertFalse(os.path.lexists(os.path.join(release_dir, "passwd")))
        self.assertFalse(os.path.lexists(os.path.join(release_dir, "escape")))
        self.assertFalse(os.path.exists(self.staging_root))
        self.assertTrue(os.path.isdir(outside_dir))  # the symlink target was never touched
        symlink_warnings = [w for w in self._warnings() if w.startswith("Skipping symlink '")]
        self.assertEqual(3, len(symlink_warnings))
        self.assertTrue(any("-> '/etc/passwd'" in w for w in symlink_warnings))
        self.assertTrue(any("-> '{}'".format(outside_dir) in w for w in symlink_warnings))
        self.assertTrue(any("-> '../nowhere'" in w for w in symlink_warnings))

    @pytest.mark.timeout(10)
    def test_publish_failure_logs_dropped_entries_and_leaves_no_staging_residue(self):
        # The move into the release folder fails after the first entry has
        # landed. The task must fail, the release folder must hold exactly what
        # landed, the entries that never made it must be named in a WARNING
        # before the task cleanup discards them, and no staging residue remains.
        root_file, release_dir = self._make_release("Half.Published")
        names = ["part1.mkv", "part2.mkv", "part3.mkv"]

        def _extract(archive_path, out_dir_path):
            os.makedirs(out_dir_path, exist_ok=True)
            for name in names:
                with open(os.path.join(out_dir_path, name), "wb") as f:
                    f.write(self.FULL)
        self.mock_extract_archive.side_effect = _extract

        real_rename = os.rename
        moved = []

        def _rename(src, dst):
            if moved:
                raise OSError("simulated rename failure")
            real_rename(src, dst)
            moved.append(os.path.basename(dst))
        rename_patcher = patch("controller.extract.dispatch.os.rename", side_effect=_rename)
        self.addCleanup(rename_patcher.stop)
        rename_patcher.start()

        listener = RecordingExtractListener([self.staging_root])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        # The ExtractError surfaced through the worker: extract_failed, not completed
        self.assertEqual([], listener.completed)
        self.assertEqual(1, len(listener.failed))
        name, is_dir, existed = listener.failed[0]
        self.assertEqual("Half.Published", name)
        self.assertTrue(is_dir)
        self.assertFalse(existed[self.staging_root])
        self.dispatch.logger.exception.assert_any_call("Caught an extraction error")
        # Only the entry that landed before the failure is in the release folder
        self.assertEqual(1, len(moved))
        self.assertEqual(sorted(["release.rar"] + moved), sorted(os.listdir(release_dir)))
        self.assertFalse(os.path.exists(self.staging_root))
        # The warning names exactly the entries that were dropped
        dropped = sorted(set(names) - set(moved))
        self.assertIn(
            "Discarding unpublished extraction output of {}: 2 file(s) {} in staging dir {} "
            "never reached {} and will be removed".format(
                os.path.join(release_dir, "release.rar"),
                dropped,
                os.path.join(self.staging_root, "Half.Published"),
                release_dir,
            ),
            self._warnings()
        )

    @pytest.mark.timeout(10)
    def test_multi_archive_dir_completes_once_after_all_archives_are_moved(self):
        root_file, release_dir = self._make_release(
            "Pack.S01", archives=("ep01/ep01.rar", "ep02/ep02.rar")
        )
        finals = [
            os.path.join(release_dir, "ep01", "ep01.mkv"),
            os.path.join(release_dir, "ep02", "ep02.mkv"),
        ]

        def _extract(archive_path, out_dir_path):
            os.makedirs(out_dir_path, exist_ok=True)
            name = os.path.splitext(os.path.basename(archive_path))[0] + ".mkv"
            with open(os.path.join(out_dir_path, name), "wb") as f:
                f.write(self.FULL)
        self.mock_extract_archive.side_effect = _extract

        listener = RecordingExtractListener(finals + [self.staging_root])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self._wait(listener)

        self.assertEqual(2, self.mock_extract_archive.call_count)
        self.assertEqual(1, len(listener.completed))
        _, _, existed = listener.completed[0]
        for final in finals:
            self.assertTrue(existed[final], final)
            self.assertEqual(len(self.FULL), os.path.getsize(final))
        self.assertFalse(existed[self.staging_root])
        self.assertFalse(os.path.exists(self.staging_root))

    def test_startup_removes_stale_staging_dir_with_warning(self):
        stale = os.path.join(self.staging_root, "Interrupted.Release")
        os.makedirs(stale)
        with open(os.path.join(stale, "movie.mkv"), "wb") as f:
            f.write(self.PARTIAL)

        dispatch = ExtractDispatch(out_dir_path=self.root, local_path=self.root)
        dispatch.logger = MagicMock()
        dispatch.start()
        try:
            self.assertFalse(os.path.exists(self.staging_root))
            self.assertIn(
                "Removing stale extraction staging dir {} left by an interrupted extraction; "
                "its contents are partial and the archives remain in place to be re-extracted".format(
                    self.staging_root
                ),
                [str(c.args[0]) for c in dispatch.logger.warning.call_args_list if c.args]
            )
        finally:
            dispatch.stop()

    def test_startup_without_staging_dir_is_silent(self):
        dispatch = ExtractDispatch(out_dir_path=self.root, local_path=self.root)
        dispatch.logger = MagicMock()
        dispatch.start()
        try:
            dispatch.logger.warning.assert_not_called()
        finally:
            dispatch.stop()


class TestExtractDispatchStagingRealArchive(unittest.TestCase):
    """
    End-to-end through the real Extract/patool path with a zip built by the
    standard library: the file lands in the release folder and no staging
    directory is left behind.
    """

    CONTENT = b"12345678" * 1024

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="test_dispatch_staging_real_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.staging_root = os.path.join(self.root, Constants.EXTRACT_STAGING_DIR_NAME)
        self.dispatch = ExtractDispatch(out_dir_path=self.root, local_path=self.root)
        self.dispatch.start()

    def tearDown(self):
        self.dispatch.stop()

    @pytest.mark.timeout(20)
    def test_zip_is_extracted_via_staging_into_release_dir(self):
        release_dir = os.path.join(self.root, "Zipped.Release")
        os.makedirs(release_dir)
        archive_path = os.path.join(release_dir, "file.zip")
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("file", self.CONTENT)
        root_file = ModelFile("Zipped.Release", True)
        root_file.local_size = os.path.getsize(archive_path)
        archive_file = ModelFile("file.zip", False)
        archive_file.local_size = os.path.getsize(archive_path)
        root_file.add_child(archive_file)

        final_path = os.path.join(release_dir, "file")
        listener = RecordingExtractListener([final_path, self.staging_root])
        self.dispatch.add_listener(listener)
        self.dispatch.extract(root_file)
        self.assertTrue(listener.event.wait(15))

        self.assertEqual([], listener.failed)
        self.assertEqual(1, len(listener.completed))
        _, _, existed = listener.completed[0]
        self.assertTrue(existed[final_path])
        self.assertFalse(existed[self.staging_root])
        with open(final_path, "rb") as f:
            self.assertEqual(self.CONTENT, f.read())
        self.assertFalse(os.path.exists(self.staging_root))
