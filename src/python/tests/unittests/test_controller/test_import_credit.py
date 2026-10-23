"""Regressions for early per-episode import credit (IMP-03).

Days of Hope incident, 2026-10-09: the season pack
'Days.of.Hope.1975.DVDRip.x264-HANDJOB' was still transferring when Sonarr
imported its first three episodes. Each of those three import notices was
rejected with "not downloaded by SeedSyncarr (no transfer evidence)" about a
minute before the root committed, because the evidence gate only looked at
the root. The notices were gone for good, so once the last episode was
imported the coverage guard saw 1 of 4 parts and deferred the auto-delete
24 times before giving up, stranding the local copy.

Contract encoded here:
- A notice for a uniquely identified child that is fully transferred while
  its root is still transferring is credited to imported_children[root]
  immediately and persisted, but never commits the root, never marks it
  imported and never arms auto-delete by itself.
- A notice whose child is not yet visible as DOWNLOADED (scan lag) is kept
  pending, bound to the resolved model path and the root's transfer
  lifecycle, revalidated every cycle and dropped on expiry, ambiguity, path
  change, root removal or a USER requeue.
- When a root holding credits commits, it is marked imported and auto-delete
  is armed (arm on commit), including after a restart.

These tests drive a real WebhookManager and real ModelFile trees through
Controller.process().
"""

from unittest.mock import MagicMock, patch

from controller import Controller
from controller.controller_persist import ControllerPersist
from controller.webhook_manager import WebhookManager
from model import ModelFile
from tests.unittests.test_controller.test_auto_delete import BaseAutoDeleteTestCase


ROOT = "Days.of.Hope.1975.DVDRip.x264-HANDJOB"
ROOT_REMOTE_SIZE = 8007628364
PART_SIZE = ROOT_REMOTE_SIZE // 4
PARTS = {i: "Days.of.Hope.Part.{}.DVDRip.x264-HANDJOB.mkv".format(i) for i in (1, 2, 3, 4)}

_REJECTION_PHRASE = "no import credit or automatic cleanup authorized"


def _lower(*indexes):
    return {PARTS[i].lower() for i in indexes}


def _child(name, done, size=PART_SIZE):
    """Leaf file. done -> DOWNLOADED with a complete local copy; otherwise
    DOWNLOADING with half the bytes on disk."""
    f = ModelFile(name, False)
    f.remote_size = size
    if done:
        f.state = ModelFile.State.DOWNLOADED
        f.local_size = size
    else:
        f.state = ModelFile.State.DOWNLOADING
        f.local_size = size // 2
    return f


def _dir(name, *children):
    d = ModelFile(name, True)
    for child in children:
        d.add_child(child)
    return d


def _transferring_pack(done=(1, 2, 3), root_name=ROOT, parts=None, extra_children=()):
    """Root directory still transferring (DOWNLOADING, local < remote).

    parts maps index -> child basename (defaults to PARTS). The tree must be
    complete before it is added to the model, which freezes it.
    """
    parts = parts or PARTS
    root = ModelFile(root_name, True)
    root.state = ModelFile.State.DOWNLOADING
    remote = ROOT_REMOTE_SIZE
    local = 0
    for i, name in sorted(parts.items()):
        child = _child(name, i in done)
        local += child.local_size
        root.add_child(child)
    for extra in extra_children:
        remote += extra.remote_size or 0
        local += extra.local_size or 0
        root.add_child(extra)
    root.remote_size = remote
    root.local_size = local
    return root


def _post_transfer_pack(root_state, part4_done, root_local_size=None):
    """Root between transfer end and commit (122-05 D-06(c)).

    Live shape: the lftp job for the root has ended (no LftpJobStatus, so
    _set_initial_state leaves the root DEFAULT instead of DOWNLOADING) while
    the local scan is still lagging behind. Unit-test-only shape (reachable
    because these tests inject the model directly and skip the pipeline's
    commit pass): the root already shows DOWNLOADED with every child
    individually complete, but its own size aggregate has not caught up
    (root_local_size stays stale). Either way the root is NOT committed here
    (never added to downloaded_file_names by this helper) -- parts 1-3 are
    always complete; part 4 is complete only when part4_done is True,
    otherwise it is a stale DEFAULT leaf (no transfer state at all, since the
    lftp job for it is gone too) with half its bytes on disk.
    """
    root = ModelFile(ROOT, True)
    root.state = root_state
    root.remote_size = ROOT_REMOTE_SIZE
    for i in (1, 2, 3):
        root.add_child(_child(PARTS[i], True))
    if part4_done:
        part4 = _child(PARTS[4], True)
    else:
        part4 = ModelFile(PARTS[4], False)
        part4.remote_size = PART_SIZE
        part4.local_size = PART_SIZE // 2
        part4.state = ModelFile.State.DEFAULT
    root.add_child(part4)
    root.local_size = (
        root_local_size if root_local_size is not None
        else sum(c.local_size or 0 for c in root.get_children())
    )
    return root


def _local_gone_pack():
    """Root whose remote copy remains but whose local copy was removed
    outside SeedSyncarr after the transfer ended (122-REVIEW WR-02).

    Root directory in state DEFAULT with a remote copy (remote_size
    ROOT_REMOTE_SIZE) but no local copy (local_size None); every leaf child
    (PARTS 1-4) mirrors that shape (remote_size PART_SIZE, local_size None).
    """
    root = ModelFile(ROOT, True)
    root.state = ModelFile.State.DEFAULT
    root.remote_size = ROOT_REMOTE_SIZE
    root.local_size = None
    for i, name in sorted(PARTS.items()):
        child = ModelFile(name, False)
        child.remote_size = PART_SIZE
        child.local_size = None
        child.state = ModelFile.State.DEFAULT
        root.add_child(child)
    return root


def _committed_pack(done=(1, 2, 3, 4), root_name=ROOT):
    """Root fully transferred: DOWNLOADED with a complete local copy."""
    root = ModelFile(root_name, True)
    root.state = ModelFile.State.DOWNLOADED
    root.remote_size = ROOT_REMOTE_SIZE
    root.local_size = ROOT_REMOTE_SIZE
    for i, name in sorted(PARTS.items()):
        root.add_child(_child(name, i in done))
    return root


class BaseImportCreditTestCase(BaseAutoDeleteTestCase):

    def setUp(self):
        super().setUp()
        self.wm = WebhookManager(self.mock_context)
        self.controller = Controller(
            context=self.mock_context,
            persist=self.persist,
            webhook_manager=self.wm,
        )
        self._make_controller_started()

    # --- helpers -------------------------------------------------------------

    def _put(self, root):
        """Add the root to the model, or replace it if already present."""
        model = self.controller._Controller__model
        if root.name in model.get_file_names():
            model.update_file(root)
        else:
            model.add_file(root)

    def _remove(self, name):
        self.controller._Controller__model.remove_file(name)

    def _commit_root(self, done=(1, 2, 3, 4)):
        """The root finished transferring and the commit pass recorded it."""
        self._put(_committed_pack(done))
        self.persist.downloaded_file_names.add(ROOT)

    def _webhook(self, *indexes):
        for i in indexes:
            self.wm.enqueue_import("Sonarr", PARTS[i])

    def _credited(self, root=ROOT):
        entry = self.persist.imported_children.get(root)
        return None if entry is None else {c.lower() for c in entry.as_list()}

    def _messages(self, level):
        method = getattr(self.controller.logger, level)
        return [str(c.args[0]) for c in method.call_args_list if c.args]

    def _pending_timers(self):
        return dict(self.controller._Controller__pending_auto_deletes)

    def _pending_notices(self):
        return dict(getattr(self.controller, "_Controller__pending_child_notices", {}))

    def _fire(self, root=ROOT):
        self.controller._Controller__execute_auto_delete(root)

    def _reset_logs(self):
        self.controller.logger.reset_mock()


class TestEarlyChildCredit(BaseImportCreditTestCase):

    def test_child_notices_before_commit_are_credited_not_dropped(self):
        """Days of Hope replay: parts 3, 1, 2 imported while part 4 still
        transfers. Each is credited, the root stays uncommitted and no
        auto-delete is armed."""
        self._put(_transferring_pack(done=(1, 2, 3)))

        self._webhook(3, 1, 2)
        self.controller.process()

        self.assertIn(ROOT, self.persist.imported_children,
                      "early child notices must be credited, not dropped")
        self.assertEqual(_lower(1, 2, 3), self._credited())
        self.assertNotIn(ROOT, self.persist.downloaded_file_names)
        self.assertNotIn(ROOT, self.persist.imported_file_names)
        self.assertEqual({}, self._pending_timers())
        self.assertFalse([w for w in self._messages("warning") if "no transfer evidence" in w])
        credited_lines = [m for m in self._messages("info") if "Credited early import" in m]
        self.assertEqual(3, len(credited_lines))
        self.assertTrue(all(ROOT in m for m in credited_lines))

    def test_credit_persists_immediately_via_callback(self):
        callback = MagicMock()
        self.controller = Controller(
            context=self.mock_context,
            persist=self.persist,
            webhook_manager=self.wm,
            persist_callback=callback,
        )
        self._make_controller_started()
        self._put(_transferring_pack(done=(1, 2, 3)))

        self._webhook(1)
        self.controller.process()
        self.assertGreaterEqual(callback.call_count, 1)

        callback.reset_mock()
        self.controller.process()
        callback.assert_not_called()

    def test_credit_survives_persist_round_trip(self):
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._webhook(3, 1, 2)
        self.controller.process()

        restored = ControllerPersist.from_str(self.persist.to_str())
        self.assertIn(ROOT, restored.imported_children)
        self.assertEqual(_lower(1, 2, 3),
                         {c.lower() for c in restored.imported_children[ROOT].as_list()})

    def test_root_commit_then_last_child_webhook_arms_and_deletes(self):
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._webhook(3, 1, 2)
        self.controller.process()

        self._commit_root()
        self._webhook(4)
        self.controller.process()

        self.assertIn(ROOT, self.persist.imported_file_names)
        self.assertEqual(_lower(1, 2, 3, 4), self._credited())
        self.assertIn(ROOT, self._pending_timers())

        self._fire()
        self.mock_file_op_manager.delete_local.assert_called_once()

    def test_arm_on_commit_without_further_webhook(self):
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._webhook(3, 1, 2)
        self.controller.process()

        # Root commits with part 4 on disk but not yet imported.
        self._commit_root()
        self.controller.process()

        self.assertIn(ROOT, self.persist.imported_file_names)
        self.assertIn(ROOT, self._pending_timers())
        self.assertTrue([m for m in self._messages("info") if "applied on commit" in m])

        # First firing: 3 of 4 on-disk videos imported -> partial-coverage defer.
        self._fire()
        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertTrue([m for m in self._messages("info")
                         if "partial import" in m and "3 of 4" in m])

        # Part 4 imported -> next firing deletes.
        self._webhook(4)
        self.controller.process()
        self._fire()
        self.mock_file_op_manager.delete_local.assert_called_once()

    def test_restart_with_persisted_credit_arms_on_commit(self):
        seeded = ControllerPersist(max_tracked_files=100)
        for i in (1, 2, 3, 4):
            seeded.add_imported_child(ROOT, PARTS[i].lower())
        seeded.downloaded_file_names.add(ROOT)
        self.persist = ControllerPersist.from_str(seeded.to_str())

        self.controller = Controller(
            context=self.mock_context,
            persist=self.persist,
            webhook_manager=self.wm,
        )
        self._make_controller_started()
        self._put(_committed_pack())

        self.controller.process()

        self.assertIn(ROOT, self.persist.imported_file_names)
        self.assertIn(ROOT, self._pending_timers())

    def test_credit_alone_never_deletes(self):
        """All four children credited while the root still transfers: the
        root is not committed, so the Timer path refuses outright. An
        in-flight subtitle keeps the root short of its remote size."""
        subtitle = _child("Days.of.Hope.en.srt", False, size=4096)
        self._put(_transferring_pack(done=(1, 2, 3, 4), extra_children=[subtitle]))
        self._webhook(1, 2, 3, 4)
        self.controller.process()

        self.assertEqual(_lower(1, 2, 3, 4), self._credited())
        self.assertEqual({}, self._pending_timers())
        self.assertNotIn(ROOT, self.persist.downloaded_file_names)

        self._fire()
        self.mock_file_op_manager.delete_local.assert_not_called()
        self.assertTrue([w for w in self._messages("warning")
                         if "not downloaded by SeedSyncarr" in w])


class TestEarlyCreditGuards(BaseImportCreditTestCase):

    def test_foreign_local_only_dir_never_credited(self):
        """Incident 2026-08-21 analog: a local-only dir (no remote copy) that
        happens to contain a matching child name is never credited."""
        foreign = ModelFile("iplayer", True)
        foreign.local_size = 1000
        child = ModelFile("episode.mkv", False)
        child.local_size = 1000
        foreign.add_child(child)
        self._put(foreign)

        self.wm.enqueue_import("Sonarr", "episode.mkv")
        self.controller.process()

        self.assertNotIn("iplayer", self.persist.imported_children)
        self.assertNotIn("iplayer", self.persist.imported_file_names)
        self.assertTrue([w for w in self._messages("warning") if "no transfer evidence" in w])
        self.assertEqual({}, self._pending_notices())

    def test_ambiguous_child_still_rejected(self):
        other_parts = {1: PARTS[1], 9: "Other.Show.S01E09.mkv"}
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._put(_transferring_pack(done=(1, 9), root_name="Other.Release", parts=other_parts))

        self._webhook(1)
        self.controller.process()

        self.assertNotIn(ROOT, self.persist.imported_children)
        self.assertNotIn("Other.Release", self.persist.imported_children)
        self.assertTrue([w for w in self._messages("warning") if _REJECTION_PHRASE in w])

    def test_pending_notice_reevaluated_when_child_becomes_downloaded(self):
        self._put(_transferring_pack(done=(1,)))
        self._webhook(2)
        self.controller.process()

        self.assertIsNone(self._credited())
        self.assertFalse([w for w in self._messages("warning") if "no transfer evidence" in w])

        # Next scan shows part 2 complete; no new webhook.
        self._put(_transferring_pack(done=(1, 2)))
        self.controller.process()

        self.assertEqual(_lower(2), self._credited())
        self.assertEqual({}, self._pending_notices())

    def test_pending_notice_expires_with_warning(self):
        with patch("controller.controller._PENDING_NOTICE_TTL_SECS", 0, create=True):
            self._put(_transferring_pack(done=(1,)))
            self._webhook(2)
            self.controller.process()
            self.assertIsNone(self._credited())

            self.controller.process()
            self.assertTrue([w for w in self._messages("warning") if "expired" in w])
            self.assertEqual({}, self._pending_notices())

            # Even once part 2 completes, the expired notice gives no credit.
            self._put(_transferring_pack(done=(1, 2)))
            self.controller.process()
            self.assertIsNone(self._credited())

    def test_root_level_notice_while_pack_transferring_is_dropped(self):
        """A root-level notice (releaseTitle fallback) for a pack that is still
        transferring carries no per-child information. Kept and replayed at
        commit it would mark the pack imported with no imported_children
        entry, so the coverage guard would grandfather the whole pack for
        deletion before the remaining episodes are imported."""
        self._put(_transferring_pack(done=(1, 2, 3)))
        self.wm.enqueue_import("Sonarr", ROOT)
        self.controller.process()

        self.assertEqual({}, self._pending_notices())
        self.assertTrue([w for w in self._messages("warning") if "no transfer evidence" in w])

        self._commit_root()
        self.controller.process()

        self.assertNotIn(ROOT, self.persist.imported_file_names)
        self.assertNotIn(ROOT, self.persist.imported_children)
        self.assertEqual({}, self._pending_timers())


class TestPendingNoticeLifecycle(BaseImportCreditTestCase):
    """A pending notice is bound to the resolved model path and to the root's
    transfer lifecycle; it never outlives either."""

    def test_pending_notice_discarded_on_user_requeue_cannot_credit_new_attempt(self):
        self._put(_transferring_pack(done=(1,)))
        self._webhook(2)
        self.controller.process()
        self.assertIsNone(self._credited())

        # Explicit USER requeue: CommandProcessor resets the root's tracking.
        self.controller.queue_command(Controller.Command(Controller.Command.Action.QUEUE, ROOT))
        self.controller.process()

        discarded = [m for m in self._messages("info") if "Discarded 1 pending import notice" in m]
        self.assertTrue(discarded, "USER requeue must discard the pending notice")
        self.assertIn(ROOT, discarded[0])
        self.assertIn("user requeue", discarded[0])

        # The replacement copy's part 2 completes; no new webhook for it.
        self._put(_transferring_pack(done=(1, 2)))
        self.controller.process()
        self.assertNotIn(ROOT, self.persist.imported_children)

        # The new attempt commits and the arr imports parts 1, 3 and 4.
        # Part 2 of the new copy was never imported, so coverage must fail.
        self._commit_root()
        self.controller.process()
        self.assertNotIn(ROOT, self.persist.imported_file_names)
        self.assertEqual({}, self._pending_timers())

        self._webhook(1, 3, 4)
        self.controller.process()
        self.assertEqual(_lower(1, 3, 4), self._credited())
        self._fire()
        self.mock_file_op_manager.delete_local.assert_not_called()

    def test_pending_notice_revalidated_against_current_model_rejects_new_ambiguity(self):
        self._put(_transferring_pack(done=(1,)))
        self._webhook(2)
        self.controller.process()
        self.assertIsNone(self._credited())

        # A second release appears containing the same basename.
        other_parts = {2: PARTS[2], 9: "Other.Show.S01E09.mkv"}
        self._put(_transferring_pack(done=(9,), root_name="Other.Release", parts=other_parts))
        self._reset_logs()
        self.controller.process()

        rejected = [w for w in self._messages("warning") if _REJECTION_PHRASE in w]
        self.assertTrue(rejected, "a pending notice that became ambiguous must be discarded")
        self.assertIn(PARTS[2], rejected[0])

        # Both copies complete: neither root is credited.
        self._put(_transferring_pack(done=(1, 2)))
        self._put(_transferring_pack(done=(2, 9), root_name="Other.Release", parts=other_parts))
        self.controller.process()
        self.assertNotIn(ROOT, self.persist.imported_children)
        self.assertNotIn("Other.Release", self.persist.imported_children)

    def test_pending_notice_discarded_when_resolved_path_changes(self):
        self._put(_transferring_pack(done=(1,)))
        self._webhook(2)
        self.controller.process()

        # Part 2 is now found only under a subdirectory: unique, but a
        # different path from the one the notice resolved to.
        moved = {i: n for i, n in PARTS.items() if i != 2}
        self._put(_transferring_pack(done=(1,), parts=moved,
                                     extra_children=[_dir("sub", _child(PARTS[2], False))]))
        self._reset_logs()
        self.controller.process()
        self.assertTrue([w for w in self._messages("warning") if "no longer resolves" in w])

        self._put(_transferring_pack(done=(1,), parts=moved,
                                     extra_children=[_dir("sub", _child(PARTS[2], True))]))
        self.controller.process()
        self.assertNotIn(ROOT, self.persist.imported_children)

    def test_pending_notice_discarded_when_root_leaves_model(self):
        self._put(_transferring_pack(done=(1,)))
        self._webhook(2)
        self.controller.process()

        self._remove(ROOT)
        self._reset_logs()
        self.controller.process()
        self.assertTrue([w for w in self._messages("warning") if "no longer resolves" in w])
        self.assertEqual({}, self._pending_notices())

        self._put(_transferring_pack(done=(1, 2)))
        self.controller.process()
        self.assertNotIn(ROOT, self.persist.imported_children)

    def test_pending_notice_with_stale_generation_never_credits(self):
        self._put(_transferring_pack(done=(1,)))
        self._webhook(2)
        self.wm.enqueue_import("Sonarr", ROOT)  # root-level notice: dropped, never kept
        self.controller.process()
        self.assertEqual(1, len(self._pending_notices()))

        self.controller._Controller__root_lifecycle_generation[ROOT] += 1
        self._reset_logs()
        self.controller.process()
        self.assertEqual({}, self._pending_notices())
        self.assertTrue([m for m in self._messages("debug") if "lifecycle generation" in m])

        self._put(_transferring_pack(done=(1, 2)))
        self.controller.process()
        self.assertNotIn(ROOT, self.persist.imported_children)

        self._commit_root()
        self.controller.process()
        self.assertNotIn(ROOT, self.persist.imported_children)
        self.assertNotIn(ROOT, self.persist.imported_file_names)
        self.assertEqual({}, self._pending_timers())

    def test_discard_pending_notices_returns_count_and_bumps_generation(self):
        self._put(_transferring_pack(done=(), root_name="A",
                                     parts={1: "a.part.1.mkv", 2: "a.part.2.mkv"}))
        self._put(_transferring_pack(done=(), root_name="B", parts={1: "b.part.1.mkv"}))
        for name in ("a.part.1.mkv", "a.part.2.mkv", "b.part.1.mkv"):
            self.wm.enqueue_import("Sonarr", name)
        self.controller.process()
        self.assertEqual(3, len(self._pending_notices()))

        generations = self.controller._Controller__root_lifecycle_generation
        before = generations["A"]
        self.assertEqual(2, self.controller._discard_pending_notices("A", "test"))
        self.assertEqual([("B", "b.part.1.mkv")], list(self._pending_notices().keys()))
        self.assertEqual(before + 1, generations["A"])

        self.assertEqual(0, self.controller._discard_pending_notices("A", "test"))
        self.assertEqual(before + 2, generations["A"])


class TestPostTransferWindow(BaseImportCreditTestCase):
    """2026-10-22 sandbox failure (122-05 D-06(c)): SSA122.Alpha2.S01E04's
    deferred webhook notice was kept pending while its root transferred, then
    permanently dropped with "Ignoring webhook import ... no transfer
    evidence" 61 s later -- 2 s before the root committed -- because by then
    the root's lftp job had ended (no longer DOWNLOADING/QUEUED) but the
    local scan had not yet caught up, so the evidence gate saw neither
    committed evidence nor a transferring root. persist.imported_children
    stayed one child short forever. These tests reproduce that drop and pin
    down the fix's narrowness (a FRESH notice or a root that lost its remote
    copy is unaffected) and boundedness (TTL/path/generation/ambiguity
    discards are unchanged).
    """

    def test_pending_notice_survives_post_transfer_scan_lag_default_root(self):
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._webhook(1, 2, 3, 4)
        self.controller.process()
        self.assertEqual(_lower(1, 2, 3), self._credited())

        # Cycle 2: lftp job for the root has ended (DEFAULT), local scan
        # lagging on part 4; root not yet committed; no new webhook.
        self._reset_logs()
        self._put(_post_transfer_pack(ModelFile.State.DEFAULT, part4_done=False))
        self.controller.process()

        self.assertFalse([w for w in self._messages("warning") if "no transfer evidence" in w])
        self.assertIn((ROOT, PARTS[4]), self._pending_notices())
        self.assertEqual(_lower(1, 2, 3), self._credited())
        self.assertNotIn(ROOT, self.persist.imported_file_names)
        self.assertEqual({}, self._pending_timers())

        # Cycle 3: the root commits.
        self._reset_logs()
        self._commit_root()
        self.controller.process()

        self.assertEqual(_lower(1, 2, 3, 4), self._credited())
        self.assertIn(ROOT, self.persist.imported_file_names)
        self.assertIn(ROOT, self._pending_timers())
        self.assertEqual({}, self._pending_notices())
        recorded = [m for m in self._messages("info") if "Recorded webhook import" in m]
        self.assertTrue(recorded)
        self.assertTrue(any(PARTS[4] in m for m in recorded))

    def test_pending_notice_survives_post_transfer_scan_lag_downloaded_root(self):
        """Orchestrator-described shape: only reachable here because unit
        tests inject the model directly and skip the pipeline's commit pass
        (a live build would have already committed a DOWNLOADED root)."""
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._webhook(1, 2, 3, 4)
        self.controller.process()
        self.assertEqual(_lower(1, 2, 3), self._credited())

        self._reset_logs()
        self._put(_post_transfer_pack(ModelFile.State.DOWNLOADED, part4_done=True,
                                      root_local_size=ROOT_REMOTE_SIZE - 1))
        self.controller.process()

        self.assertFalse([w for w in self._messages("warning") if "no transfer evidence" in w])
        self.assertEqual(_lower(1, 2, 3, 4), self._credited())
        credited_lines = [m for m in self._messages("info") if "Credited early import" in m]
        self.assertTrue(any(PARTS[4] in m for m in credited_lines))
        self.assertNotIn(ROOT, self.persist.imported_file_names)
        self.assertNotIn(ROOT, self.persist.downloaded_file_names)
        self.assertEqual({}, self._pending_timers())
        self.assertEqual({}, self._pending_notices())

    def test_fresh_notice_for_uncommitted_non_transferring_root_still_ignored(self):
        """Guard: a FRESH notice (never pending) for a non-transferring,
        uncommitted root is still ignored exactly as before this phase."""
        self._put(_post_transfer_pack(ModelFile.State.DEFAULT, part4_done=False))
        self._webhook(4)
        self.controller.process()

        self.assertTrue([w for w in self._messages("warning") if "no transfer evidence" in w])
        self.assertEqual({}, self._pending_notices())
        self.assertNotIn(ROOT, self.persist.imported_children)

    def test_post_transfer_pending_notice_still_expires(self):
        """Guard: TTL expiry is unaffected -- an expired notice is discarded
        in revalidation before the post-transfer exception can apply."""
        with patch("controller.controller._PENDING_NOTICE_TTL_SECS", 0, create=True):
            self._put(_transferring_pack(done=(1,)))
            self._webhook(4)
            self.controller.process()
            self.assertIsNone(self._credited())

            self._reset_logs()
            self._put(_post_transfer_pack(ModelFile.State.DEFAULT, part4_done=False))
            self.controller.process()
            self.assertTrue([w for w in self._messages("warning") if "expired" in w])
            self.assertEqual({}, self._pending_notices())

            self._commit_root()
            self.controller.process()
            self.assertNotIn(PARTS[4].lower(), self._credited() or set())

    def test_post_transfer_pending_notice_dropped_when_root_loses_remote_copy(self):
        """Guard: if the root loses its remote copy (remote_size None), a
        previously-pending notice is still dropped, not credited."""
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._webhook(4)
        self.controller.process()
        self.assertIsNone(self._credited())

        self._reset_logs()
        gone = _post_transfer_pack(ModelFile.State.DEFAULT, part4_done=False)
        gone.remote_size = None
        for child in gone.get_children():
            child.remote_size = None
        self._put(gone)
        self.controller.process()

        self.assertTrue([w for w in self._messages("warning") if "no transfer evidence" in w])
        self.assertEqual({}, self._pending_notices())
        self.assertIsNone(self._credited())


class TestPostTransferWindowBounds(BaseImportCreditTestCase):
    """122-REVIEW WR-02: the 122-10 post-transfer exception kept or credited
    a pending child notice for ANY non-transferring root that still had a
    remote copy, for up to the 6 h TTL -- including a stopped or failed
    transfer and a root whose local copy was deleted outside SeedSyncarr.
    These tests pin the narrowed window: post-transfer keep/credit now
    requires BOTH a local copy and that the root was last seen
    DOWNLOADING/QUEUED less than `_POST_TRANSFER_GRACE_SECS` (120 s) ago,
    and a user STOP or DELETE_LOCAL discards the root's pending notices at
    once.

    122-REVIEW WR-03: the import-credit INFO line always said "(root still
    transferring)", which is false on the post-transfer path. These tests
    also pin the reason-aware wording on both paths.
    """

    def test_post_transfer_notice_discarded_after_grace_window(self):
        with patch("controller.controller.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            self._put(_transferring_pack(done=(1, 2, 3)))
            self._webhook(1, 2, 3, 4)
            self.controller.process()
            self.assertEqual(_lower(1, 2, 3), self._credited())
            self.assertIn((ROOT, PARTS[4]), self._pending_notices())

            # Still within the 120 s grace window (119 s since last seen
            # transferring): kept pending, no discard warning.
            self._reset_logs()
            mock_time.monotonic.return_value = 1119.0
            self._put(_post_transfer_pack(ModelFile.State.DEFAULT, part4_done=False))
            self.controller.process()
            self.assertFalse([w for w in self._messages("warning")
                              if "Discarding pending webhook import" in w])
            self.assertIn((ROOT, PARTS[4]), self._pending_notices())

            # Past the grace window (121 s since last seen transferring):
            # discarded, never credited.
            self._reset_logs()
            mock_time.monotonic.return_value = 1121.0
            self.controller.process()
            self.assertEqual({}, self._pending_notices())
            discard_warnings = [w for w in self._messages("warning")
                                if "Discarding pending webhook import" in w]
            self.assertEqual(1, len(discard_warnings))
            self.assertIn(PARTS[4], discard_warnings[0])
            self.assertIn("no transfer seen for over 120 s without commit", discard_warnings[0])
            self.assertFalse([w for w in self._messages("warning") if "no transfer evidence" in w])

            self._commit_root()
            self.controller.process()
            self.assertNotIn(PARTS[4].lower(), self._credited() or set())

    def test_post_transfer_grace_refreshes_while_root_transfers(self):
        """Guard: the grace window is measured from the LAST time the root
        was seen transferring, so a root that keeps transferring refreshes
        it instead of expiring on a stale first sighting."""
        with patch("controller.controller.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            self._put(_transferring_pack(done=(1,)))
            self._webhook(4)
            self.controller.process()
            self.assertIn((ROOT, PARTS[4]), self._pending_notices())

            mock_time.monotonic.return_value = 1100.0
            self._put(_transferring_pack(done=(1,)))
            self.controller.process()
            self.assertIn((ROOT, PARTS[4]), self._pending_notices())

            # 119 s after the LAST transferring sighting (1100.0), not 219 s
            # after the first (1000.0): still within the grace window.
            self._reset_logs()
            mock_time.monotonic.return_value = 1219.0
            self._put(_post_transfer_pack(ModelFile.State.DEFAULT, part4_done=False))
            self.controller.process()
            self.assertFalse([w for w in self._messages("warning")
                              if "Discarding pending webhook import" in w])
            self.assertIn((ROOT, PARTS[4]), self._pending_notices())

    def test_post_transfer_notice_discarded_when_local_copy_gone(self):
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._webhook(4)
        self.controller.process()
        self.assertIn((ROOT, PARTS[4]), self._pending_notices())

        self._reset_logs()
        self._put(_local_gone_pack())
        self.controller.process()

        self.assertEqual({}, self._pending_notices())
        discard_warnings = [w for w in self._messages("warning")
                            if "Discarding pending webhook import" in w]
        self.assertEqual(1, len(discard_warnings))
        self.assertIn(PARTS[4], discard_warnings[0])
        self.assertIn("local copy gone", discard_warnings[0])

        self._reset_logs()
        self._put(_post_transfer_pack(ModelFile.State.DEFAULT, part4_done=True))
        self.controller.process()
        self.assertNotIn(PARTS[4].lower(), self._credited() or set())

    def test_user_stop_discards_pending_notice(self):
        self._put(_transferring_pack(done=(1,)))
        self._webhook(4)
        self.controller.process()
        self.assertIn((ROOT, PARTS[4]), self._pending_notices())

        self._reset_logs()
        self.controller.queue_command(Controller.Command(Controller.Command.Action.STOP, ROOT))
        # The transferring pack is still in the model: the STOP precondition
        # (state DOWNLOADING/QUEUED) must hold for CommandProcessor to accept it.
        self.controller.process()

        self.assertFalse([w for w in self._messages("warning") if "Command failed" in w])
        discarded = [m for m in self._messages("info") if "Discarded 1 pending import notice(s)" in m]
        self.assertTrue(discarded, "a successful STOP must discard the root's pending notices")
        self.assertIn(ROOT, discarded[0])
        self.assertIn("user stop", discarded[0])
        self.assertEqual({}, self._pending_notices())

        self._reset_logs()
        self._put(_post_transfer_pack(ModelFile.State.DEFAULT, part4_done=True))
        self.controller.process()
        self.assertFalse([m for m in self._messages("info")
                         if "Credited early import" in m and PARTS[4] in m])
        self.assertNotIn(PARTS[4].lower(), self._credited() or set())
        self.assertEqual({}, self._pending_timers())

    def test_user_delete_local_discards_pending_notice(self):
        self.mock_lftp_manager.submitted_unobserved_file_names.return_value = []
        self._put(_transferring_pack(done=(1,)))
        self._webhook(4)
        self.controller.process()
        self.assertIn((ROOT, PARTS[4]), self._pending_notices())

        self._reset_logs()
        self._put(_post_transfer_pack(ModelFile.State.DEFAULT, part4_done=False))
        self.controller.process()
        self.assertIn((ROOT, PARTS[4]), self._pending_notices())

        self._reset_logs()
        self.controller.queue_command(
            Controller.Command(Controller.Command.Action.DELETE_LOCAL, ROOT))
        self.controller.process()

        self.assertFalse([w for w in self._messages("warning") if "Command failed" in w])
        discarded = [m for m in self._messages("info") if "Discarded 1 pending import notice(s)" in m]
        self.assertTrue(discarded, "a successful DELETE_LOCAL must discard the root's pending notices")
        self.assertIn(ROOT, discarded[0])
        self.assertIn("local copy deleted", discarded[0])
        self.assertEqual({}, self._pending_notices())
        self.assertNotIn(ROOT, self.persist.imported_file_names)
        self.assertEqual({}, self._pending_timers())
        self.assertFalse([m for m in self._messages("info")
                         if "Recorded webhook import" in m and PARTS[4] in m])

    def test_post_transfer_credit_line_says_transfer_finished(self):
        self._put(_transferring_pack(done=(1, 2, 3)))
        self._webhook(1, 2, 3, 4)
        self.controller.process()
        credited_lines = [m for m in self._messages("info") if "Credited early import" in m]
        self.assertEqual(3, len(credited_lines))
        self.assertTrue(all("(root still transferring)" in m for m in credited_lines))

        self._reset_logs()
        self._put(_post_transfer_pack(ModelFile.State.DOWNLOADED, part4_done=True,
                                      root_local_size=ROOT_REMOTE_SIZE - 1))
        self.controller.process()

        credited_lines = [m for m in self._messages("info") if "Credited early import of" in m]
        self.assertEqual(1, len(credited_lines))
        self.assertIn(PARTS[4], credited_lines[0])
        self.assertIn("(transfer finished, awaiting commit)", credited_lines[0])
        self.assertNotIn("(root still transferring)", credited_lines[0])
