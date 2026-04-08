import unittest

from controller.memory_monitor import MemoryMonitor, MemoryStats


class TestMemoryMonitor(unittest.TestCase):
    def test_initialization(self):
        monitor = MemoryMonitor()
        self.assertIsNotNone(monitor)
        self.assertEqual([], monitor.get_stats_history())
        self.assertIsNone(monitor.get_latest_stats())

    def test_custom_log_interval(self):
        monitor = MemoryMonitor(log_interval_seconds=10)
        self.assertIsNotNone(monitor)

    def test_register_data_source(self):
        monitor = MemoryMonitor()
        test_size = 42
        monitor.register_data_source('test_source', lambda: test_size)
        # Collect stats and verify the source was called
        stats = monitor.collect_stats()
        # Since 'test_source' is not a standard field, it won't be in the main stats
        # but the callback should have been called successfully
        self.assertIsNotNone(stats)

    def test_register_stream_queue(self):
        monitor = MemoryMonitor()
        monitor.register_stream_queue('test_queue', lambda: {'size': 10, 'dropped': 5, 'maxsize': 100})
        stats = monitor.collect_stats()
        self.assertEqual({'size': 10, 'dropped': 5, 'maxsize': 100}, stats.stream_queues_stats['test_queue'])

    def test_collect_stats(self):
        monitor = MemoryMonitor()
        monitor.register_data_source('downloaded_files', lambda: 10)
        monitor.register_data_source('extracted_files', lambda: 5)
        monitor.register_data_source('model_files', lambda: 20)

        stats = monitor.collect_stats()
        self.assertIsInstance(stats, MemoryStats)
        self.assertIsInstance(stats.timestamp, float)
        self.assertIsInstance(stats.process_memory_mb, float)
        self.assertEqual(10, stats.downloaded_files_count)
        self.assertEqual(5, stats.extracted_files_count)
        self.assertEqual(20, stats.model_files_count)

    def test_stats_history(self):
        monitor = MemoryMonitor()
        self.assertEqual([], monitor.get_stats_history())

        stats1 = monitor.collect_stats()
        self.assertEqual(1, len(monitor.get_stats_history()))
        self.assertEqual(stats1, monitor.get_latest_stats())

        stats2 = monitor.collect_stats()
        self.assertEqual(2, len(monitor.get_stats_history()))
        self.assertEqual(stats2, monitor.get_latest_stats())

    def test_get_process_memory_mb(self):
        monitor = MemoryMonitor()
        memory = monitor.get_process_memory_mb()
        # Should return a non-negative number
        self.assertGreaterEqual(memory, 0.0)

    def test_log_stats_if_due_first_call(self):
        monitor = MemoryMonitor(log_interval_seconds=1)
        # First call should always log
        result = monitor.log_stats_if_due()
        self.assertTrue(result)

    def test_log_stats_if_due_respects_interval(self):
        monitor = MemoryMonitor(log_interval_seconds=60)
        # First call logs
        self.assertTrue(monitor.log_stats_if_due())
        # Immediate second call should not log (interval not passed)
        self.assertFalse(monitor.log_stats_if_due())

    def test_force_log_stats(self):
        monitor = MemoryMonitor(log_interval_seconds=60)
        # First call logs
        monitor.log_stats_if_due()
        # Second call doesn't log
        self.assertFalse(monitor.log_stats_if_due())
        # Force log should log regardless
        monitor.force_log_stats()
        # Stats history should have 2 entries now
        self.assertEqual(2, len(monitor.get_stats_history()))

    def test_data_source_callback_exception(self):
        monitor = MemoryMonitor()

        def failing_callback():
            raise Exception("Test exception")

        monitor.register_data_source('failing', failing_callback)
        # Should not raise, just log and continue
        stats = monitor.collect_stats()
        self.assertIsNotNone(stats)

    def test_stream_queue_callback_exception(self):
        monitor = MemoryMonitor()

        def failing_callback():
            raise Exception("Test exception")

        monitor.register_stream_queue('failing', failing_callback)
        # Should not raise, just log and continue
        stats = monitor.collect_stats()
        self.assertIsNotNone(stats)
        # Should have error stats
        self.assertEqual({'size': -1, 'dropped': -1, 'maxsize': -1}, stats.stream_queues_stats['failing'])

    def test_detect_growth_trend_insufficient_data(self):
        monitor = MemoryMonitor()
        monitor.register_data_source('downloaded_files', lambda: 10)
        # Only one sample
        monitor.collect_stats()
        result = monitor.detect_growth_trend('downloaded_files', window_size=5)
        self.assertIsNone(result)

    def test_detect_growth_trend_with_data(self):
        counter = [0]
        monitor = MemoryMonitor()
        monitor.register_data_source('downloaded_files', lambda: counter[0])

        # Collect 10 samples with increasing values
        for i in range(10):
            counter[0] = i * 10
            monitor.collect_stats()

        # Should detect positive growth
        growth = monitor.detect_growth_trend('downloaded_files', window_size=5)
        self.assertIsNotNone(growth)
        self.assertGreater(growth, 0)

    def test_detect_growth_trend_stable(self):
        monitor = MemoryMonitor()
        monitor.register_data_source('downloaded_files', lambda: 100)

        # Collect 10 samples with stable values
        for _ in range(10):
            monitor.collect_stats()

        # Should detect no growth
        growth = monitor.detect_growth_trend('downloaded_files', window_size=5)
        self.assertIsNotNone(growth)
        self.assertEqual(0, growth)

    def test_detect_growth_trend_unknown_source(self):
        monitor = MemoryMonitor()
        for _ in range(10):
            monitor.collect_stats()

        result = monitor.detect_growth_trend('unknown_source', window_size=5)
        self.assertIsNone(result)

    def test_max_history_size(self):
        monitor = MemoryMonitor()
        # The default max history size is 100
        for _ in range(150):
            monitor.collect_stats()

        history = monitor.get_stats_history()
        self.assertEqual(100, len(history))
