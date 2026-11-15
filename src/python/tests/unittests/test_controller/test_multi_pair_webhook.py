"""A webhook name that exists in two path pairs must not credit or delete either."""

import logging

from controller import Controller
from controller.multi_controller import WebhookFanout
from controller.webhook_manager import WebhookManager
from model import ModelFile
from tests.unittests.test_controller.test_auto_delete import BaseAutoDeleteTestCase


# Pair ids of the two controllers built in TestSameNameInTwoPairs, in order
PAIRS = ("tv", "movies")


def _leaf(name, size=50, pair_id=None):
    f = ModelFile(name, False, pair_id=pair_id)
    f.remote_size = size
    f.local_size = size
    return f


def _pack(name, *children, pair_id=None):
    root = ModelFile(name, True, pair_id=pair_id)
    root.remote_size = 100
    root.local_size = 100
    for child in children:
        root.add_child(child)
    return root


class TestMatchesWebhookName(BaseAutoDeleteTestCase):
    def setUp(self):
        super().setUp()
        self.controller._Controller__model.add_file(_pack("Rel.A", _leaf("Ep.One.mkv")))
        self.controller._Controller__model.add_file(_leaf("Single.mkv"))

    def test_matches_a_root_case_insensitively(self):
        self.assertTrue(self.controller.matches_webhook_name("single.MKV"))

    def test_matches_a_child(self):
        self.assertTrue(self.controller.matches_webhook_name("ep.one.mkv"))

    def test_does_not_match_an_unknown_name(self):
        self.assertFalse(self.controller.matches_webhook_name("other.mkv"))


class TestSameNameInTwoPairs(BaseAutoDeleteTestCase):
    """Two real controllers and managers behind a real fan-out."""

    def setUp(self):
        super().setUp()
        self.managers = [
            WebhookManager(self.mock_context),
            WebhookManager(self.mock_context),
        ]
        self.controllers = [
            Controller(
                context=self.mock_context,
                persist=self.persist,
                webhook_manager=self.managers[0],
                pair_id="tv",
            ),
            Controller(
                context=self.mock_context,
                persist=self.persist,
                webhook_manager=self.managers[1],
                pair_id="movies",
            ),
        ]
        self.fanout = WebhookFanout(
            self.managers,
            [c.matches_webhook_name for c in self.controllers],
            logging.getLogger("t"),
        )

    def tearDown(self):
        for controller in self.controllers:
            for timer in list(controller._Controller__pending_auto_deletes.values()):
                timer.cancel()
            controller._Controller__pending_auto_deletes.clear()
        super().tearDown()

    def _add(self, index, root):
        self.controllers[index]._Controller__model.add_file(root)
        self.persist.downloaded_file_names.add(root.name)

    def _pending(self, index):
        return dict(self.controllers[index]._Controller__pending_auto_deletes)

    def _badge(self, index, name):
        return self.controllers[index]._Controller__model.get_file(name).import_status

    def test_same_name_in_both_pairs_credits_and_arms_neither(self):
        self._add(0, _leaf("Same.mkv", pair_id=PAIRS[0]))
        self._add(1, _leaf("Same.mkv", pair_id=PAIRS[1]))
        self.fanout.enqueue_import("Sonarr", "Same.mkv", "prov")
        for controller in self.controllers:
            controller._Controller__check_webhook_imports()
        for index in (0, 1):
            self.assertEqual({}, self._pending(index))
            self.assertEqual(
                ModelFile.ImportStatus.NONE, self._badge(index, "Same.mkv")
            )

    def test_child_name_in_both_pairs_is_ambiguous_too(self):
        self._add(
            0, _pack("Rel.A", _leaf("sample.mkv", pair_id=PAIRS[0]), pair_id=PAIRS[0])
        )
        self._add(
            1, _pack("Rel.B", _leaf("sample.mkv", pair_id=PAIRS[1]), pair_id=PAIRS[1])
        )
        self.fanout.enqueue_import("Sonarr", "sample.mkv", "prov")
        for controller in self.controllers:
            controller._Controller__check_webhook_imports()
        for index, name in ((0, "Rel.A"), (1, "Rel.B")):
            self.assertEqual({}, self._pending(index))
            self.assertEqual(ModelFile.ImportStatus.NONE, self._badge(index, name))

    def test_name_in_one_pair_credits_only_that_pair(self):
        self._add(0, _leaf("Only.mkv", pair_id=PAIRS[0]))
        self._add(1, _leaf("Other.mkv", pair_id=PAIRS[1]))
        self.fanout.enqueue_import("Sonarr", "Only.mkv", "prov")
        for controller in self.controllers:
            controller._Controller__check_webhook_imports()
        self.assertEqual(ModelFile.ImportStatus.IMPORTED, self._badge(0, "Only.mkv"))
        self.assertEqual(ModelFile.ImportStatus.NONE, self._badge(1, "Other.mkv"))
        self.assertEqual({"Only.mkv"}, set(self._pending(0)))
        self.assertEqual({}, self._pending(1))
