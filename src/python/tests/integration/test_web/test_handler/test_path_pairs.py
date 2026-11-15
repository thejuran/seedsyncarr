import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock

from webtest import TestApp

from common import PathPair, PathPairsConfig, overrides
from web import WebAppBuilder
from tests.integration.test_web.test_web_app import BaseTestWebApp


class TestPathPairsHandler(BaseTestWebApp):
    @overrides(BaseTestWebApp)
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp(prefix="test_path_pairs_web_")
        self.path = os.path.join(self.tmp, "path_pairs.json")
        self.path_pairs = PathPairsConfig.from_legacy("/remote/files", "/local/files")
        builder = WebAppBuilder(
            self.context,
            self.controller,
            self.auto_queue_persist,
            MagicMock(),
            path_pairs=self.path_pairs,
            path_pairs_path=self.path,
        )
        self.test_app = TestApp(builder.build())

    @overrides(BaseTestWebApp)
    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def test_list(self):
        resp = self.test_app.get("/server/pathpairs")
        self.assertEqual(200, resp.status_int)
        pairs = json.loads(resp.text)["path_pairs"]
        self.assertEqual(1, len(pairs))
        self.assertEqual(PathPair.LEGACY_ID, pairs[0]["id"])

    def test_create_update_delete(self):
        resp = self.test_app.post_json(
            "/server/pathpairs/create",
            {
                "name": "movies",
                "remote_path": "/remote/movies",
                "local_path": "/local/movies",
            },
        )
        self.assertEqual(201, resp.status_int)
        pair_id = json.loads(resp.text)["id"]
        self.assertEqual(2, len(PathPairsConfig.from_file(self.path).pairs))

        resp = self.test_app.post_json(
            "/server/pathpairs/update/" + pair_id, {"enabled": False}
        )
        self.assertEqual(200, resp.status_int)
        self.assertFalse(PathPairsConfig.from_file(self.path).get_pair(pair_id).enabled)

        resp = self.test_app.post("/server/pathpairs/delete/" + pair_id)
        self.assertEqual(200, resp.status_int)
        self.assertEqual(1, len(PathPairsConfig.from_file(self.path).pairs))

    def test_bad_requests(self):
        resp = self.test_app.post_json(
            "/server/pathpairs/create", {"name": "x"}, expect_errors=True
        )
        self.assertEqual(400, resp.status_int)
        resp = self.test_app.post_json(
            "/server/pathpairs/create",
            {"name": "Default", "remote_path": "/r", "local_path": "/l"},
            expect_errors=True,
        )
        self.assertEqual(409, resp.status_int)
        resp = self.test_app.post("/server/pathpairs/delete/nope", expect_errors=True)
        self.assertEqual(404, resp.status_int)
        resp = self.test_app.post_json(
            "/server/pathpairs/update/nope", {"enabled": False}, expect_errors=True
        )
        self.assertEqual(404, resp.status_int)
