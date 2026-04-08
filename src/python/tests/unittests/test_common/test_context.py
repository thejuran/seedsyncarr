# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest
import logging
import collections
from unittest.mock import MagicMock

from common import overrides, Context, Args


class TestArgs(unittest.TestCase):

    def test_default_values_are_none(self):
        args = Args()
        self.assertIsNone(args.local_path_to_scanfs)
        self.assertIsNone(args.html_path)
        self.assertIsNone(args.debug)
        self.assertIsNone(args.exit)

    def test_as_dict_returns_ordered_dict(self):
        args = Args()
        self.assertIsInstance(args.as_dict(), collections.OrderedDict)

    def test_as_dict_key_order(self):
        args = Args()
        self.assertEqual(
            list(args.as_dict().keys()),
            ["local_path_to_scanfs", "html_path", "debug", "exit"]
        )

    def test_as_dict_converts_values_to_strings(self):
        args = Args()
        args.local_path_to_scanfs = "/path"
        args.html_path = "/html"
        args.debug = True
        args.exit = False
        dct = args.as_dict()
        self.assertEqual("/path", dct["local_path_to_scanfs"])
        self.assertEqual("/html", dct["html_path"])
        self.assertEqual("True", dct["debug"])
        self.assertEqual("False", dct["exit"])

    def test_as_dict_none_values_become_none_string(self):
        args = Args()
        dct = args.as_dict()
        self.assertEqual("None", dct["local_path_to_scanfs"])
        self.assertEqual("None", dct["html_path"])
        self.assertEqual("None", dct["debug"])
        self.assertEqual("None", dct["exit"])


class TestContext(unittest.TestCase):

    @overrides(unittest.TestCase)
    def setUp(self):
        self.logger = logging.getLogger("TestContext")
        self.web_access_logger = logging.getLogger("TestContext.web")
        self.config = MagicMock()
        self.args = Args()
        self.status = MagicMock()
        self.context = Context(self.logger, self.web_access_logger,
                               self.config, self.args, self.status)

    def test_constructor_stores_logger(self):
        self.assertIs(self.logger, self.context.logger)

    def test_constructor_stores_web_access_logger(self):
        self.assertIs(self.web_access_logger, self.context.web_access_logger)

    def test_constructor_stores_config(self):
        self.assertIs(self.config, self.context.config)

    def test_constructor_stores_args(self):
        self.assertIs(self.args, self.context.args)

    def test_constructor_stores_status(self):
        self.assertIs(self.status, self.context.status)

    def test_create_child_context_returns_new_object(self):
        child = self.context.create_child_context("child")
        self.assertIsNot(self.context, child)

    def test_create_child_context_has_child_logger(self):
        child = self.context.create_child_context("child")
        self.assertIsNot(self.context.logger, child.logger)
        self.assertEqual("TestContext.child", child.logger.name)

    def test_create_child_context_shares_config(self):
        child = self.context.create_child_context("child")
        self.assertIs(self.context.config, child.config)

    def test_create_child_context_shares_args(self):
        child = self.context.create_child_context("child")
        self.assertIs(self.context.args, child.args)

    def test_create_child_context_shares_status(self):
        child = self.context.create_child_context("child")
        self.assertIs(self.context.status, child.status)

    def test_create_child_context_shares_web_access_logger(self):
        child = self.context.create_child_context("child")
        self.assertIs(self.context.web_access_logger, child.web_access_logger)

    def test_print_to_log_calls_logger_debug(self):
        # Replace logger with a mock to capture debug calls
        mock_logger = MagicMock()
        self.context.logger = mock_logger
        # Set up config mock
        self.config.as_dict.return_value = {"Section": {"key": "value"}}
        # Set up args
        self.args.local_path_to_scanfs = "/path"
        self.args.html_path = "/html"
        self.args.debug = False
        self.args.exit = False
        # Call print_to_log
        self.context.print_to_log()
        # Verify logger.debug was called
        self.assertTrue(mock_logger.debug.called)
        # At least 3 calls: "Config:", one config line, "Args:"
        self.assertGreaterEqual(mock_logger.debug.call_count, 3)
