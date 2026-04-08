# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest
from unittest.mock import MagicMock

from controller import ControllerJob


class TestControllerJob(unittest.TestCase):
    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.mock_controller = MagicMock()
        self.mock_auto_queue = MagicMock()
        self.job = ControllerJob(
            context=self.mock_context,
            controller=self.mock_controller,
            auto_queue=self.mock_auto_queue
        )

    def test_setup_starts_controller(self):
        self.job.setup()
        self.mock_controller.start.assert_called_once()

    def test_execute_processes_controller(self):
        self.job.execute()
        self.mock_controller.process.assert_called_once()

    def test_execute_processes_auto_queue(self):
        self.job.execute()
        self.mock_auto_queue.process.assert_called_once()

    def test_execute_calls_controller_before_auto_queue(self):
        call_order = []
        self.mock_controller.process.side_effect = lambda: call_order.append('controller')
        self.mock_auto_queue.process.side_effect = lambda: call_order.append('auto_queue')
        self.job.execute()
        self.assertEqual(['controller', 'auto_queue'], call_order)

    def test_cleanup_exits_controller(self):
        self.job.cleanup()
        self.mock_controller.exit.assert_called_once()
