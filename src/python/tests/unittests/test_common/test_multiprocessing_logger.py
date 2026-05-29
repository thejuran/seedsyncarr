import unittest
import logging
import sys
import time
import multiprocessing

from testfixtures import LogCapture
import pytest

from common import MultiprocessingLogger


class _ListenerSentinelError(RuntimeError):
    """Uniquely-named exception raised by the failing handler under test."""


class _RaisingHandler(logging.Handler):
    """A logging.Handler whose emit() always raises a sentinel exception.

    Used to drive the listener thread's outer ``except Exception`` branch
    (multiprocessing_logger.py:78-83) when ``handle(record)`` is invoked.
    """

    SENTINEL_MESSAGE = "boom from raising handler"

    def emit(self, record: logging.LogRecord) -> None:
        raise _ListenerSentinelError(_RaisingHandler.SENTINEL_MESSAGE)


class TestMultiprocessingLogger(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger(TestMultiprocessingLogger.__name__)
        self._test_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self._test_handler)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        self._test_handler.setFormatter(formatter)

    def tearDown(self):
        self.logger.removeHandler(self._test_handler)

    def _drive_record_in_process(self, mp_logger: MultiprocessingLogger,
                                 child_name: str, level: int, message: str):
        """Enqueue a single real log record onto the listener's queue from THIS process.

        ``get_process_safe_logger()`` strips the root logger's handlers and attaches a
        ``QueueHandler`` to the MultiprocessingLogger's internal queue. Calling it
        in-process (rather than from a spawned child) routes a real record onto the
        queue without depending on the multiprocessing start method (``spawn`` on
        macOS cannot pickle local-closure process targets). We snapshot and restore
        the root logger's handler list + level via ``addCleanup`` so this drive does
        not leak QueueHandlers into other tests.
        """
        root_logger = logging.getLogger()
        saved_handlers = root_logger.handlers[:]
        saved_level = root_logger.level

        def _restore():
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            for handler in saved_handlers:
                root_logger.addHandler(handler)
            root_logger.setLevel(saved_level)

        self.addCleanup(_restore)

        # get_process_safe_logger() returns the (now queue-backed) root logger
        process_logger = mp_logger.get_process_safe_logger().getChild(child_name)
        process_logger.log(level, message)

    @pytest.mark.timeout(5)
    def test_listener_captures_handler_exception_and_shuts_down(self):
        # Attach a handler that raises onto the child logger the listener routes to:
        # the listener calls self.logger.getChild(record.name).handle(record), where
        # record.name == "process_1" and self.logger == TestMultiprocessingLogger.MPLogger.
        failing_child = self.logger.getChild("MPLogger").getChild("process_1")
        raising_handler = _RaisingHandler()
        failing_child.addHandler(raising_handler)
        self.addCleanup(failing_child.removeHandler, raising_handler)

        mp_logger = MultiprocessingLogger(self.logger)
        mp_logger.start()
        try:
            self._drive_record_in_process(mp_logger, "process_1", logging.ERROR,
                                          "trigger handler raise")
            time.sleep(0.2)  # let the listener drain and hit the except branch
        finally:
            mp_logger.stop()

        # The listener's outer except stashed the exception and set shutdown.
        # Prove it via the PUBLIC API: propagate_exception() re-raises the sentinel.
        with self.assertRaises(_ListenerSentinelError):
            mp_logger.propagate_exception()

    @pytest.mark.timeout(5)
    def test_propagate_exception_reraises_captured(self):
        failing_child = self.logger.getChild("MPLogger").getChild("process_1")
        raising_handler = _RaisingHandler()
        failing_child.addHandler(raising_handler)
        self.addCleanup(failing_child.removeHandler, raising_handler)

        mp_logger = MultiprocessingLogger(self.logger)
        mp_logger.start()
        try:
            self._drive_record_in_process(mp_logger, "process_1", logging.ERROR,
                                          "trigger handler raise")
            time.sleep(0.2)
        finally:
            mp_logger.stop()

        with self.assertRaises(_ListenerSentinelError) as ctx:
            mp_logger.propagate_exception()
        # Same exception type AND message that the failing handler raised.
        self.assertEqual(str(ctx.exception), _RaisingHandler.SENTINEL_MESSAGE)

    @pytest.mark.timeout(5)
    def test_propagate_exception_second_call_is_noop(self):
        failing_child = self.logger.getChild("MPLogger").getChild("process_1")
        raising_handler = _RaisingHandler()
        failing_child.addHandler(raising_handler)
        self.addCleanup(failing_child.removeHandler, raising_handler)

        mp_logger = MultiprocessingLogger(self.logger)
        mp_logger.start()
        try:
            self._drive_record_in_process(mp_logger, "process_1", logging.ERROR,
                                          "trigger handler raise")
            time.sleep(0.2)
        finally:
            mp_logger.stop()

        # First call re-raises (clears the stashed exc_info to None at line 45)...
        with self.assertRaises(_ListenerSentinelError):
            mp_logger.propagate_exception()
        # ...so the second call is a no-op (returns None, does not raise).
        self.assertIsNone(mp_logger.propagate_exception())

    @pytest.mark.timeout(5)
    def test_main_logger_receives_records(self):
        def process_1(_mp_logger: MultiprocessingLogger):
            logger = _mp_logger.get_process_safe_logger().getChild("process_1")
            logger.debug("Debug line")
            time.sleep(0.1)
            logger.info("Info line")
            time.sleep(0.1)
            logger.warning("Warning line")
            time.sleep(0.1)
            logger.error("Error line")

        mp_logger = MultiprocessingLogger(self.logger)
        p_1 = multiprocessing.Process(target=process_1,
                                      args=(mp_logger,))

        with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
            p_1.start()
            mp_logger.start()
            p_1.join(timeout=2)
            time.sleep(0.2)
            mp_logger.stop()

            log_capture.check(
                ("process_1", "DEBUG", "Debug line"),
                ("process_1", "INFO", "Info line"),
                ("process_1", "WARNING", "Warning line"),
                ("process_1", "ERROR", "Error line")
            )

    @pytest.mark.timeout(5)
    def test_children_names(self):
        def process_1(_mp_logger: MultiprocessingLogger):
            logger = _mp_logger.get_process_safe_logger().getChild("process_1")
            logger.debug("Debug line")
            logger.getChild("child_1").debug("Debug line")
            logger.getChild("child_1_1").debug("Debug line")

        mp_logger = MultiprocessingLogger(self.logger)
        p_1 = multiprocessing.Process(target=process_1,
                                      args=(mp_logger,))

        with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
            p_1.start()
            mp_logger.start()
            p_1.join(timeout=2)
            time.sleep(0.2)
            mp_logger.stop()

            log_capture.check(
                ("process_1", "DEBUG", "Debug line"),
                ("process_1.child_1", "DEBUG", "Debug line"),
                ("process_1.child_1_1", "DEBUG", "Debug line"),
            )

    @pytest.mark.timeout(5)
    def test_logger_levels(self):
        def process_1(_mp_logger: MultiprocessingLogger):
            logger = _mp_logger.get_process_safe_logger().getChild("process_1")
            logger.debug("Debug line")
            logger.info("Info line")
            logger.warning("Warning line")
            logger.error("Error line")

        # Debug level
        self.logger.setLevel(logging.DEBUG)
        with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
            mp_logger = MultiprocessingLogger(self.logger)
            p_1 = multiprocessing.Process(target=process_1,
                                          args=(mp_logger,))
            p_1.start()
            mp_logger.start()
            p_1.join(timeout=2)
            time.sleep(0.2)
            mp_logger.stop()

            log_capture.check(
                ("process_1", "DEBUG", "Debug line"),
                ("process_1", "INFO", "Info line"),
                ("process_1", "WARNING", "Warning line"),
                ("process_1", "ERROR", "Error line")
            )

        # Info level
        self.logger.setLevel(logging.INFO)
        with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
            mp_logger = MultiprocessingLogger(self.logger)
            p_1 = multiprocessing.Process(target=process_1,
                                          args=(mp_logger,))
            p_1.start()
            mp_logger.start()
            p_1.join(timeout=2)
            time.sleep(0.2)
            mp_logger.stop()

            log_capture.check(
                ("process_1", "INFO", "Info line"),
                ("process_1", "WARNING", "Warning line"),
                ("process_1", "ERROR", "Error line")
            )

        # Warning level
        self.logger.setLevel(logging.WARNING)
        with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
            mp_logger = MultiprocessingLogger(self.logger)
            p_1 = multiprocessing.Process(target=process_1,
                                          args=(mp_logger,))
            p_1.start()
            mp_logger.start()
            p_1.join(timeout=2)
            time.sleep(0.2)
            mp_logger.stop()

            log_capture.check(
                ("process_1", "WARNING", "Warning line"),
                ("process_1", "ERROR", "Error line")
            )

        # Error level
        self.logger.setLevel(logging.ERROR)
        with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
            mp_logger = MultiprocessingLogger(self.logger)
            p_1 = multiprocessing.Process(target=process_1,
                                          args=(mp_logger,))
            p_1.start()
            mp_logger.start()
            p_1.join(timeout=2)
            time.sleep(0.2)
            mp_logger.stop()

            log_capture.check(
                ("process_1", "ERROR", "Error line")
            )
