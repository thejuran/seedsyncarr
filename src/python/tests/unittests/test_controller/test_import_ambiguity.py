"""End-to-end regressions for ambiguous webhook import matching.

IMPORT-01: a Sonarr/Radarr webhook file name that resolves to two or more
distinct model paths must never be credited to a release. No import record,
no per-child coverage entry, no import badge and no auto-delete timer.

IMPORT-02: a webhook name that resolves to exactly one model path keeps the
existing behavior (record, badge, evidence gate, arm auto-delete), and the
same path referenced twice is one match, not an ambiguity.

These tests drive a real WebhookManager and real ModelFile trees through
Controller.process(), so they do not depend on the shape of the name lookup
passed between the controller and the webhook manager. The rejection tests
fail with an AssertionError against code that resolves names last-writer-wins.
"""

from controller import Controller
from controller.webhook_manager import WebhookManager
from model import ModelFile
from tests.unittests.test_controller.test_auto_delete import BaseAutoDeleteTestCase


def _leaf(name, size=50):
    """Non-directory ModelFile with matching remote and local sizes."""
    f = ModelFile(name, False)
    f.remote_size = size
    f.local_size = size
    return f


def _pack(name, *children):
    """Directory ModelFile with the given children attached.

    The whole tree must be built before Model.add_file, which freezes it.
    """
    root = ModelFile(name, True)
    root.remote_size = 100
    root.local_size = 100
    for child in children:
        root.add_child(child)
    return root


_REJECTION_PHRASE = "no import credit or automatic cleanup authorized"


class TestAmbiguousWebhookImport(BaseAutoDeleteTestCase):
    """Webhook import matching through Controller.process() with a real
    WebhookManager and real model trees."""

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

    def _add_root(self, root):
        """Add a root to the model and mark it downloaded so the evidence gate
        passes; a rejection must then come from ambiguity, not missing evidence."""
        self.controller._Controller__model.add_file(root)
        self.persist.downloaded_file_names.add(root.name)

    def _warnings(self):
        # The logger mock is shared by Controller, WebhookManager and
        # AutoDeleteManager, so callers filter by substring, never by count.
        return [
            str(c.args[0])
            for c in self.controller.logger.warning.call_args_list
            if c.args
        ]

    def _ambiguous_warnings(self):
        return [w for w in self._warnings() if "ambiguous" in w]

    def _badge(self, name):
        return self.controller._Controller__model.get_file(name).import_status

    def _pending(self):
        return dict(self.controller._Controller__pending_auto_deletes)

    def _assert_rejected(self, before, root_names):
        """Shared rejection assertions. The persist check comes first so the
        failure on last-writer-wins code is about state, not log wording."""
        self.assertEqual(before, self.persist.to_str(),
                         "ambiguous import must not change persisted state")
        self.assertEqual({}, self._pending(),
                         "ambiguous import must not arm auto-delete")
        for name in root_names:
            self.assertEqual(ModelFile.ImportStatus.NONE, self._badge(name),
                             "ambiguous import must not badge '{}'".format(name))
        ambiguous = self._ambiguous_warnings()
        self.assertEqual(1, len(ambiguous),
                         "expected exactly one ambiguity warning, got {}".format(ambiguous))
        self.assertIn(_REJECTION_PHRASE, ambiguous[0])
        return ambiguous[0]

    # --- IMPORT-01: rejection (fail on last-writer-wins lookup) ---------------

    def test_two_releases_sharing_sample_mkv_are_untouched(self):
        """D-03, success criterion 1: two releases each containing sample.mkv.
        The webhook name matches two distinct paths, so neither release is
        credited and no auto-delete is armed."""
        self._add_root(_pack("Rel.A", _leaf("ep.a.mkv"), _leaf("sample.mkv")))
        self._add_root(_pack("Rel.B", _leaf("ep.b.mkv"), _leaf("sample.mkv")))
        before = self.persist.to_str()

        self.wm.enqueue_import("Sonarr", "sample.mkv")
        self.controller.process()

        warning = self._assert_rejected(before, ["Rel.A", "Rel.B"])
        self.assertIn("'sample.mkv'", warning)
        self.assertIn("Rel.A", warning)
        self.assertIn("Rel.B", warning)

    def test_roots_differing_only_by_case_are_rejected(self):
        """D-01/D-03, success criterion 2: single-file roots 'Movie.mkv' and
        'movie.mkv' are distinct case-preserving paths sharing one lowercased
        key, so the webhook name is ambiguous."""
        self._add_root(_leaf("Movie.mkv"))
        self._add_root(_leaf("movie.mkv"))
        before = self.persist.to_str()

        self.wm.enqueue_import("Radarr", "movie.mkv")
        self.controller.process()

        warning = self._assert_rejected(before, ["Movie.mkv", "movie.mkv"])
        self.assertIn("Movie.mkv", warning)
        self.assertIn("movie.mkv", warning)

    def test_root_name_equal_to_child_basename_elsewhere_is_rejected(self):
        """D-03, success criterion 3: a single-file root 'sample.mkv' and a
        child 'Rel.A/sample.mkv' are two distinct paths for one name."""
        self._add_root(_leaf("sample.mkv"))
        self._add_root(_pack("Rel.A", _leaf("ep.a.mkv"), _leaf("sample.mkv")))
        before = self.persist.to_str()

        self.wm.enqueue_import("Sonarr", "sample.mkv")
        self.controller.process()

        warning = self._assert_rejected(before, ["sample.mkv", "Rel.A"])
        self.assertIn("Rel.A", warning)

    def test_duplicate_basename_within_one_pack_is_rejected(self):
        """D-03/D-04/D-08, success criterion 4: Pack/Disc1/movie.mkv and
        Pack/Disc2/movie.mkv. One webhook for movie.mkv cannot prove which
        disc was imported, so no per-child coverage is recorded for Pack and
        the warning lists both relative paths."""
        self._add_root(_pack(
            "Pack",
            _pack("Disc1", _leaf("movie.mkv")),
            _pack("Disc2", _leaf("movie.mkv")),
        ))
        before = self.persist.to_str()

        self.wm.enqueue_import("Radarr", "movie.mkv")
        self.controller.process()

        self.assertEqual(before, self.persist.to_str(),
                         "ambiguous import must not change persisted state")
        self.assertNotIn("Pack", self.persist.imported_children)
        warning = self._assert_rejected(before, ["Pack"])
        self.assertIn("Pack/Disc1/movie.mkv", warning)
        self.assertIn("Pack/Disc2/movie.mkv", warning)

    # --- IMPORT-02: preservation (pass before and after the fix) -------------

    def test_unique_child_name_imports_and_arms_exactly_as_before(self):
        """D-02, success criterion 5: a child name that exists at exactly one
        path is recorded, gets per-child coverage, is badged and arms
        auto-delete, while the other release is untouched."""
        self._add_root(_pack("Rel.A", _leaf("ep.a.mkv"), _leaf("sample.mkv")))
        self._add_root(_pack("Rel.B", _leaf("ep.b.mkv")))

        self.wm.enqueue_import("Sonarr", "ep.a.mkv")
        self.controller.process()

        self.assertIn("Rel.A", self.persist.imported_file_names)
        self.assertIn("ep.a.mkv", self.persist.imported_children["Rel.A"].as_list())
        self.assertEqual(ModelFile.ImportStatus.IMPORTED, self._badge("Rel.A"))
        self.assertIn("Rel.A", self._pending())

        self.assertNotIn("Rel.B", self.persist.imported_file_names)
        self.assertNotIn("Rel.B", self.persist.imported_children)
        self.assertEqual(ModelFile.ImportStatus.NONE, self._badge("Rel.B"))
        self.assertNotIn("Rel.B", self._pending())

        self.assertEqual([], self._ambiguous_warnings())

    def test_same_path_referenced_twice_is_one_match(self):
        """D-02, Pitfall 7: the same complete path referenced by two webhook
        events in one cycle is one candidate, not an ambiguity. Exactly one
        root is accepted and exactly one Timer is armed."""
        self._add_root(_pack("Rel.A", _leaf("ep.a.mkv")))
        imported_before = set(self.persist.imported_file_names)

        self.wm.enqueue_import("Sonarr", "ep.a.mkv")
        self.wm.enqueue_import("Sonarr", "ep.a.mkv")
        self.controller.process()

        self.assertEqual(imported_before | {"Rel.A"}, set(self.persist.imported_file_names))
        self.assertEqual(["Rel.A"], list(self._pending().keys()))
        self.assertEqual([], self._ambiguous_warnings())
