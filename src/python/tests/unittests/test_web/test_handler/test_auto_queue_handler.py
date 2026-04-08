# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest
import json
from unittest.mock import MagicMock
from urllib.parse import quote

from controller import AutoQueuePersist, AutoQueuePattern
from web.handler.auto_queue import AutoQueueHandler


class TestAutoQueueHandlerGet(unittest.TestCase):
    def setUp(self):
        self.mock_persist = MagicMock(spec=AutoQueuePersist)
        self.handler = AutoQueueHandler(self.mock_persist)

    def test_get_returns_200(self):
        self.mock_persist.patterns = set()
        response = self.handler._AutoQueueHandler__handle_get_autoqueue()
        self.assertEqual(200, response.status_code)

    def test_get_empty_returns_empty_json_array(self):
        self.mock_persist.patterns = set()
        response = self.handler._AutoQueueHandler__handle_get_autoqueue()
        self.assertEqual([], json.loads(response.body))

    def test_get_returns_sorted_patterns(self):
        beta = AutoQueuePattern("beta")
        alpha = AutoQueuePattern("alpha")
        self.mock_persist.patterns = {beta, alpha}
        response = self.handler._AutoQueueHandler__handle_get_autoqueue()
        result = json.loads(response.body)
        self.assertEqual("alpha", result[0]["pattern"])
        self.assertEqual("beta", result[1]["pattern"])

    def test_get_multiple_patterns(self):
        p1 = AutoQueuePattern("cherry")
        p2 = AutoQueuePattern("apple")
        p3 = AutoQueuePattern("banana")
        self.mock_persist.patterns = {p1, p2, p3}
        response = self.handler._AutoQueueHandler__handle_get_autoqueue()
        result = json.loads(response.body)
        self.assertEqual(3, len(result))


class TestAutoQueueHandlerAdd(unittest.TestCase):
    def setUp(self):
        self.mock_persist = MagicMock(spec=AutoQueuePersist)
        self.handler = AutoQueueHandler(self.mock_persist)

    def test_add_new_pattern_returns_200(self):
        self.mock_persist.patterns = set()
        response = self.handler._AutoQueueHandler__handle_add_autoqueue(quote("newpattern"))
        self.assertEqual(200, response.status_code)
        self.assertIn("Added", response.body)

    def test_add_calls_persist_add_pattern(self):
        self.mock_persist.patterns = set()
        self.handler._AutoQueueHandler__handle_add_autoqueue(quote("newpattern"))
        self.mock_persist.add_pattern.assert_called_once()
        called_pattern = self.mock_persist.add_pattern.call_args[0][0]
        self.assertIsInstance(called_pattern, AutoQueuePattern)
        self.assertEqual("newpattern", called_pattern.pattern)

    def test_add_duplicate_returns_409(self):
        self.mock_persist.patterns = {AutoQueuePattern("existing")}
        response = self.handler._AutoQueueHandler__handle_add_autoqueue(quote("existing"))
        self.assertEqual(409, response.status_code)

    def test_add_blank_pattern_returns_400(self):
        self.mock_persist.patterns = set()
        self.mock_persist.add_pattern.side_effect = ValueError("Blank")
        response = self.handler._AutoQueueHandler__handle_add_autoqueue(quote("  "))
        self.assertEqual(400, response.status_code)

    def test_add_url_decodes_pattern(self):
        self.mock_persist.patterns = set()
        self.handler._AutoQueueHandler__handle_add_autoqueue(quote("my pattern/test"))
        called_pattern = self.mock_persist.add_pattern.call_args[0][0]
        self.assertEqual("my pattern/test", called_pattern.pattern)

    def test_add_special_characters(self):
        self.mock_persist.patterns = set()
        response = self.handler._AutoQueueHandler__handle_add_autoqueue(quote("file (2).txt"))
        self.assertEqual(200, response.status_code)


class TestAutoQueueHandlerRemove(unittest.TestCase):
    def setUp(self):
        self.mock_persist = MagicMock(spec=AutoQueuePersist)
        self.handler = AutoQueueHandler(self.mock_persist)

    def test_remove_existing_returns_200(self):
        self.mock_persist.patterns = {AutoQueuePattern("toremove")}
        response = self.handler._AutoQueueHandler__handle_remove_autoqueue(quote("toremove"))
        self.assertEqual(200, response.status_code)

    def test_remove_calls_persist_remove_pattern(self):
        self.mock_persist.patterns = {AutoQueuePattern("toremove")}
        self.handler._AutoQueueHandler__handle_remove_autoqueue(quote("toremove"))
        self.mock_persist.remove_pattern.assert_called_once()

    def test_remove_nonexistent_returns_404(self):
        self.mock_persist.patterns = set()
        response = self.handler._AutoQueueHandler__handle_remove_autoqueue(quote("nonexistent"))
        self.assertEqual(404, response.status_code)

    def test_remove_url_decodes_pattern(self):
        self.mock_persist.patterns = {AutoQueuePattern("my pattern")}
        response = self.handler._AutoQueueHandler__handle_remove_autoqueue(quote("my pattern"))
        self.assertEqual(200, response.status_code)
