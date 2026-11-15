import json
import logging
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from common import PathPair, PathPairsConfig
from web.handler.path_pairs import PathPairsHandler


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="test_path_pairs_handler_")
        self.path = os.path.join(self.tmp, "path_pairs.json")
        self.config = PathPairsConfig.from_legacy("/remote/files", "/local/files")
        context = MagicMock()
        context.logger = logging.getLogger("test_path_pairs_handler")
        self.handler = PathPairsHandler(self.config, self.path, context)
        self.list = self.handler._PathPairsHandler__handle_list
        self.create = self.handler._PathPairsHandler__handle_create
        self.update = self.handler._PathPairsHandler__handle_update
        self.delete = self.handler._PathPairsHandler__handle_delete

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def body(**kwargs):
        data = {
            "name": "movies",
            "remote_path": "/remote/movies",
            "local_path": "/local/movies",
        }
        data.update(kwargs)
        return data

    def call(self, fn, data, *args):
        with patch("web.handler.path_pairs.request") as req:
            req.json = data
            return fn(*args)

    def saved(self):
        return PathPairsConfig.from_file(self.path)


class TestList(_Base):
    def test_lists_pairs(self):
        response = self.list()
        self.assertEqual(200, response.status_code)
        pairs = json.loads(response.body)["path_pairs"]
        self.assertEqual(["Default"], [p["name"] for p in pairs])


class TestCreate(_Base):
    def test_creates_and_saves(self):
        response = self.call(self.create, self.body())
        self.assertEqual(201, response.status_code)
        body = json.loads(response.body)
        self.assertEqual("movies", body["name"])
        self.assertTrue(body["enabled"])
        self.assertTrue(body["auto_queue"])
        self.assertTrue(body["restart_required"])
        self.assertEqual({"Default", "movies"}, {p.name for p in self.saved().pairs})

    def test_trims_values(self):
        self.call(
            self.create,
            self.body(name="  movies ", remote_path=" /r/m ", local_path=" /l/m "),
        )
        pair = self.config.pairs[1]
        self.assertEqual(
            ("movies", "/r/m", "/l/m"), (pair.name, pair.remote_path, pair.local_path)
        )

    def test_invalid_bodies(self):
        cases = [
            None,
            [],
            {},
            self.body(name=""),
            self.body(name="   "),
            self.body(name=5),
            self.body(name="x" * 65),
            self.body(remote_path=None),
            self.body(local_path="relative/path"),
            self.body(local_path="/l\x00x"),
            self.body(enabled="yes"),
            self.body(auto_queue=1),
            self.body(unknown="x"),
        ]
        for data in cases:
            with self.subTest(data=data):
                self.assertEqual(400, self.call(self.create, data).status_code)
        self.assertEqual(1, len(self.config.pairs))
        self.assertFalse(os.path.exists(self.path))

    def test_duplicate_name_local_and_remote_rejected(self):
        for data in (
            self.body(name="Default"),
            self.body(local_path="/local/files/"),
            self.body(remote_path="/remote/files"),
        ):
            with self.subTest(data=data):
                self.assertEqual(409, self.call(self.create, data).status_code)
        self.assertEqual(1, len(self.config.pairs))

    def test_save_failure_rolls_back(self):
        with patch.object(PathPairsConfig, "to_file", side_effect=OSError("disk full")):
            response = self.call(self.create, self.body())
        self.assertEqual(500, response.status_code)
        self.assertEqual(1, len(self.config.pairs))


class TestUpdate(_Base):
    def setUp(self):
        super().setUp()
        self.call(self.create, self.body())
        self.pair = [p for p in self.config.pairs if p.name == "movies"][0]

    def test_partial_update(self):
        response = self.call(self.update, {"enabled": False}, self.pair.id)
        self.assertEqual(200, response.status_code)
        updated = self.config.get_pair(self.pair.id)
        self.assertFalse(updated.enabled)
        self.assertEqual("/local/movies", updated.local_path)
        self.assertFalse(self.saved().get_pair(self.pair.id).enabled)

    def test_full_update(self):
        data = self.body(
            name="films",
            remote_path="/remote/films",
            local_path="/local/films",
            auto_queue=False,
        )
        self.assertEqual(200, self.call(self.update, data, self.pair.id).status_code)
        updated = self.config.get_pair(self.pair.id)
        self.assertEqual(
            ("films", "/remote/films", "/local/films", False),
            (updated.name, updated.remote_path, updated.local_path, updated.auto_queue),
        )

    def test_keeping_own_values_is_not_a_conflict(self):
        self.assertEqual(
            200, self.call(self.update, self.body(), self.pair.id).status_code
        )

    def test_unknown_pair(self):
        self.assertEqual(
            404, self.call(self.update, {"enabled": False}, "nope").status_code
        )

    def test_conflicts_with_other_pair(self):
        for data in (
            {"name": "Default"},
            {"local_path": "/local/files"},
            {"remote_path": "/remote/files"},
        ):
            with self.subTest(data=data):
                self.assertEqual(
                    409, self.call(self.update, data, self.pair.id).status_code
                )

    def test_invalid_body(self):
        self.assertEqual(400, self.call(self.update, None, self.pair.id).status_code)
        self.assertEqual(
            400, self.call(self.update, {"enabled": "x"}, self.pair.id).status_code
        )

    def test_legacy_pair_paths_come_from_settings(self):
        response = self.call(
            self.update, {"local_path": "/elsewhere"}, PathPair.LEGACY_ID
        )
        self.assertEqual(409, response.status_code)
        self.assertEqual(
            "/local/files", self.config.get_pair(PathPair.LEGACY_ID).local_path
        )

    def test_legacy_pair_other_fields_can_change(self):
        response = self.call(
            self.update, {"name": "Main", "auto_queue": False}, PathPair.LEGACY_ID
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("Main", self.config.get_pair(PathPair.LEGACY_ID).name)

    def test_save_failure_rolls_back(self):
        with patch.object(PathPairsConfig, "to_file", side_effect=OSError("disk full")):
            response = self.call(self.update, {"enabled": False}, self.pair.id)
        self.assertEqual(500, response.status_code)
        self.assertTrue(self.config.get_pair(self.pair.id).enabled)


class TestDelete(_Base):
    def setUp(self):
        super().setUp()
        self.call(self.create, self.body())
        self.pair = [p for p in self.config.pairs if p.name == "movies"][0]

    def test_deletes_and_saves(self):
        response = self.delete(self.pair.id)
        self.assertEqual(200, response.status_code)
        self.assertTrue(json.loads(response.body)["restart_required"])
        self.assertIsNone(self.config.get_pair(self.pair.id))
        self.assertIsNone(self.saved().get_pair(self.pair.id))

    def test_unknown_pair(self):
        self.assertEqual(404, self.delete("nope").status_code)

    def test_save_failure_rolls_back(self):
        with patch.object(PathPairsConfig, "to_file", side_effect=OSError("disk full")):
            response = self.delete(self.pair.id)
        self.assertEqual(500, response.status_code)
        self.assertIsNotNone(self.config.get_pair(self.pair.id))


class TestRoutes(_Base):
    def test_routes_are_registered(self):
        web_app = MagicMock()
        self.handler.add_routes(web_app)
        self.assertEqual(
            ["/server/pathpairs"],
            [c.args[0] for c in web_app.add_handler.call_args_list],
        )
        self.assertEqual(
            [
                "/server/pathpairs/create",
                "/server/pathpairs/update/<pair_id>",
                "/server/pathpairs/delete/<pair_id>",
            ],
            [c.args[0] for c in web_app.add_post_handler.call_args_list],
        )
