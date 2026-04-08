# Copyright 2017, Inderpreet Singh, All rights reserved.

import unittest

from web.utils import StreamQueue, DEFAULT_QUEUE_MAXSIZE


class TestStreamQueue(unittest.TestCase):
    def test_basic_put_get(self):
        queue = StreamQueue()
        queue.put("event1")
        queue.put("event2")
        self.assertEqual("event1", queue.get_next_event())
        self.assertEqual("event2", queue.get_next_event())
        self.assertIsNone(queue.get_next_event())

    def test_default_maxsize(self):
        queue = StreamQueue()
        self.assertEqual(DEFAULT_QUEUE_MAXSIZE, queue.get_maxsize())

    def test_custom_maxsize(self):
        queue = StreamQueue(maxsize=50)
        self.assertEqual(50, queue.get_maxsize())

    def test_get_queue_size(self):
        queue = StreamQueue()
        self.assertEqual(0, queue.get_queue_size())
        queue.put("event1")
        self.assertEqual(1, queue.get_queue_size())
        queue.put("event2")
        self.assertEqual(2, queue.get_queue_size())
        queue.get_next_event()
        self.assertEqual(1, queue.get_queue_size())

    def test_get_dropped_count_initially_zero(self):
        queue = StreamQueue()
        self.assertEqual(0, queue.get_dropped_count())

    def test_overflow_drops_oldest(self):
        queue = StreamQueue(maxsize=3)
        queue.put("event1")
        queue.put("event2")
        queue.put("event3")
        self.assertEqual(3, queue.get_queue_size())
        self.assertEqual(0, queue.get_dropped_count())

        # Add fourth event, should drop event1
        queue.put("event4")
        self.assertEqual(1, queue.get_dropped_count())
        # Queue should still be at max size
        self.assertEqual(3, queue.get_queue_size())
        # event1 should be gone, event2 should be first
        self.assertEqual("event2", queue.get_next_event())
        self.assertEqual("event3", queue.get_next_event())
        self.assertEqual("event4", queue.get_next_event())
        self.assertIsNone(queue.get_next_event())

    def test_multiple_overflows(self):
        queue = StreamQueue(maxsize=2)
        queue.put("event1")
        queue.put("event2")
        # Now overflow multiple times
        queue.put("event3")  # drops event1
        queue.put("event4")  # drops event2
        queue.put("event5")  # drops event3
        self.assertEqual(3, queue.get_dropped_count())
        # Only event4 and event5 should remain
        self.assertEqual("event4", queue.get_next_event())
        self.assertEqual("event5", queue.get_next_event())
        self.assertIsNone(queue.get_next_event())

    def test_unlimited_queue(self):
        # maxsize=0 means unlimited
        queue = StreamQueue(maxsize=0)
        self.assertEqual(0, queue.get_maxsize())
        # Add many events
        for i in range(100):
            queue.put("event{}".format(i))
        self.assertEqual(100, queue.get_queue_size())
        self.assertEqual(0, queue.get_dropped_count())

    def test_get_next_event_on_empty(self):
        queue = StreamQueue()
        self.assertIsNone(queue.get_next_event())
        self.assertIsNone(queue.get_next_event())

    def test_fifo_order(self):
        queue = StreamQueue()
        events = ["first", "second", "third", "fourth"]
        for event in events:
            queue.put(event)
        for expected in events:
            self.assertEqual(expected, queue.get_next_event())
