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
    root.remote_size = ROOT_REMOTE_SIZE
    local = 0
    for i, name in sorted(parts.items()):
        child = _child(name, i in done)
        local += child.local_size
        root.add_child(child)
    for extra in extra_children:
        root.add_child(extra)
    root.local_size = local
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
        root is not committed, so the Timer path refuses outright."""
        self._put(_transferring_pack(done=(1, 2, 3, 4)))
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
        self.wm.enqueue_import("Sonarr", ROOT)  # root-level notice
        self.controller.process()
        self.assertEqual(2, len(self._pending_notices()))

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
