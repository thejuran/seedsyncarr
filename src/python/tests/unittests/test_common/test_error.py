# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest

from common import AppError, ServiceExit, ServiceRestart


class TestAppError(unittest.TestCase):

    def test_is_exception_subclass(self):
        self.assertTrue(issubclass(AppError, Exception))

    def test_can_be_raised_and_caught(self):
        with self.assertRaises(AppError):
            raise AppError("test")

    def test_message(self):
        try:
            raise AppError("test message")
        except AppError as e:
            self.assertEqual("test message", str(e))


class TestServiceExit(unittest.TestCase):

    def test_is_app_error_subclass(self):
        self.assertTrue(issubclass(ServiceExit, AppError))

    def test_is_exception_subclass(self):
        self.assertTrue(issubclass(ServiceExit, Exception))

    def test_caught_by_app_error_handler(self):
        with self.assertRaises(AppError):
            raise ServiceExit("exit")

    def test_caught_by_exception_handler(self):
        with self.assertRaises(Exception):
            raise ServiceExit("exit")

    def test_is_not_service_restart(self):
        self.assertFalse(issubclass(ServiceExit, ServiceRestart))


class TestServiceRestart(unittest.TestCase):

    def test_is_app_error_subclass(self):
        self.assertTrue(issubclass(ServiceRestart, AppError))

    def test_is_exception_subclass(self):
        self.assertTrue(issubclass(ServiceRestart, Exception))

    def test_caught_by_app_error_handler(self):
        with self.assertRaises(AppError):
            raise ServiceRestart("restart")

    def test_is_not_service_exit(self):
        self.assertFalse(issubclass(ServiceRestart, ServiceExit))

    def test_message_preserved(self):
        try:
            raise ServiceRestart("restart requested")
        except ServiceRestart as e:
            self.assertEqual("restart requested", str(e))
