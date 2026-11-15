import json
import os
import shutil
import tempfile
import unittest

from common import PathPair, PathPairsConfig, PersistError


class TestPathPair(unittest.TestCase):
    def test_defaults_and_generated_id(self):
        a = PathPair("a", "/r", "/l")
        b = PathPair("b", "/r", "/l")
        self.assertTrue(a.enabled)
        self.assertTrue(a.auto_queue)
        self.assertNotEqual(a.id, b.id)

    def test_dict_round_trip(self):
        pair = PathPair("tv", "/r/tv", "/l/tv", enabled=False, auto_queue=False)
        self.assertEqual(pair, PathPair.from_dict(pair.to_dict()))

    def test_from_dict_rejects_bad_input(self):
        good = PathPair("tv", "/r", "/l").to_dict()
        for key in ("id", "name", "remote_path", "local_path"):
            missing = dict(good)
            del missing[key]
            with self.assertRaises(KeyError):
                PathPair.from_dict(missing)
            wrong_type = dict(good, **{key: 5})
            with self.assertRaises(TypeError):
                PathPair.from_dict(wrong_type)
            blank = dict(good, **{key: "  "})
            with self.assertRaises(ValueError):
                PathPair.from_dict(blank)
        with self.assertRaises(TypeError):
            PathPair.from_dict(dict(good, enabled="yes"))
        with self.assertRaises(TypeError):
            PathPair.from_dict(dict(good, auto_queue=1))


class TestPathPairsConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="test_path_pairs_")
        self.path = os.path.join(self.tmp, "path_pairs.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty(self):
        self.assertEqual([], PathPairsConfig().pairs)

    def test_add_get_update_remove(self):
        config = PathPairsConfig()
        pair = PathPair("tv", "/r/tv", "/l/tv")
        config.add_pair(pair)
        self.assertEqual(pair, config.get_pair(pair.id))
        updated = PathPair("tv2", "/r/tv2", "/l/tv2", pair_id=pair.id)
        config.update_pair(updated)
        self.assertEqual([updated], config.pairs)
        config.remove_pair(pair.id)
        self.assertEqual([], config.pairs)
        self.assertIsNone(config.get_pair(pair.id))

    def test_duplicates_rejected(self):
        config = PathPairsConfig()
        pair = PathPair("tv", "/r", "/l")
        config.add_pair(pair)
        with self.assertRaises(ValueError):
            config.add_pair(PathPair("other", "/r", "/l", pair_id=pair.id))
        with self.assertRaises(ValueError):
            config.add_pair(PathPair("tv", "/r2", "/l2"))
        other = PathPair("movies", "/r2", "/l2")
        config.add_pair(other)
        with self.assertRaises(ValueError):
            config.update_pair(PathPair("tv", "/r2", "/l2", pair_id=other.id))
        # keeping its own name is fine
        config.update_pair(PathPair("movies", "/r3", "/l3", pair_id=other.id))

    def test_missing_ids_raise(self):
        config = PathPairsConfig()
        with self.assertRaises(ValueError):
            config.update_pair(PathPair("x", "/r", "/l"))
        with self.assertRaises(ValueError):
            config.remove_pair("nope")

    def test_returns_copies(self):
        config = PathPairsConfig()
        pair = PathPair("tv", "/r", "/l")
        config.add_pair(pair)
        config.pairs[0].name = "mutated"
        config.get_pair(pair.id).name = "mutated"
        pair.name = "mutated"
        self.assertEqual("tv", config.pairs[0].name)

    def test_file_round_trip(self):
        config = PathPairsConfig()
        config.add_pair(PathPair("tv", "/r/tv", "/l/tv", auto_queue=False))
        config.add_pair(PathPair("movies", "/r/movies", "/l/movies", enabled=False))
        config.to_file(self.path)
        self.assertEqual(config.pairs, PathPairsConfig.from_file(self.path).pairs)
        with open(self.path) as f:
            self.assertEqual(1, json.load(f)["version"])

    def test_from_legacy(self):
        config = PathPairsConfig.from_legacy("/remote/files", "/local/files")
        pairs = config.pairs
        self.assertEqual(1, len(pairs))
        self.assertEqual("Default", pairs[0].name)
        self.assertEqual(PathPair.LEGACY_ID, pairs[0].id)
        self.assertEqual("/remote/files", pairs[0].remote_path)
        self.assertEqual("/local/files", pairs[0].local_path)
        self.assertTrue(pairs[0].enabled)
        self.assertTrue(pairs[0].auto_queue)

    def test_from_str_errors(self):
        pair = PathPair("tv", "/r", "/l").to_dict()
        bad = [
            "not json",
            "[]",
            json.dumps({"version": 99, "path_pairs": []}),
            json.dumps({"version": "1", "path_pairs": []}),
            json.dumps({"path_pairs": {}}),
            json.dumps({"path_pairs": ["x"]}),
            json.dumps({"path_pairs": [{"id": "a"}]}),
            json.dumps({"path_pairs": [pair, pair]}),
        ]
        for content in bad:
            with self.subTest(content=content):
                with self.assertRaises(PersistError):
                    PathPairsConfig.from_str(content)

    def test_from_str_without_version_or_pairs(self):
        self.assertEqual([], PathPairsConfig.from_str("{}").pairs)


class TestPathPairsConfigSyncLegacy(unittest.TestCase):
    def test_updates_changed_paths(self):
        config = PathPairsConfig.from_legacy("/r", "/l")
        self.assertTrue(config.sync_legacy("/r2", "/l2"))
        pair = config.get_pair(PathPair.LEGACY_ID)
        self.assertEqual(("/r2", "/l2"), (pair.remote_path, pair.local_path))

    def test_unchanged_returns_false(self):
        config = PathPairsConfig.from_legacy("/r", "/l")
        self.assertFalse(config.sync_legacy("/r", "/l"))

    def test_creates_pair_when_empty(self):
        config = PathPairsConfig()
        self.assertTrue(config.sync_legacy("/r", "/l"))
        self.assertEqual(PathPair.LEGACY_ID, config.pairs[0].id)

    def test_does_not_add_a_legacy_pair_next_to_others(self):
        config = PathPairsConfig()
        config.add_pair(PathPair("movies", "/r", "/l"))
        self.assertFalse(config.sync_legacy("/r2", "/l2"))
        self.assertEqual(1, len(config.pairs))


class TestPathPairId(unittest.TestCase):
    def test_id_must_be_safe_as_a_file_name(self):
        good = PathPair("tv", "/r", "/l").to_dict()
        for bad in ("../x", "a/b", "a b", "", "x" * 65, "a.b"):
            with self.subTest(id=bad):
                with self.assertRaises(ValueError):
                    PathPair.from_dict(dict(good, id=bad))
        for ok in ("default", "a-b_c", "0f8fad5b-d9cb-469f-a165-70867728950e"):
            PathPair.from_dict(dict(good, id=ok))
