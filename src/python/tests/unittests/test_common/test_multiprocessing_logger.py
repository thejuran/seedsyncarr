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
        """Enqueue a single real log record directly onto the listener's queue.

        The listener consumes ``LogRecord`` objects off the MultiprocessingLogger's
        internal ``multiprocessing.Queue`` and routes each via
        ``self.logger.getChild(record.name).handle(record)`` — keyed on ``record.name``.
        We build a real record with ``name == child_name`` (exactly what a child
        ``QueueHandler`` would have enqueued) and put it on that queue directly.

        This deliberately does NOT go through ``get_process_safe_logger()``: that helper
        installs a ``QueueHandler`` on the global ROOT logger (after closing + stripping
        root's existing handlers). Driving records through root meant (a) the listener
        could propagate a handled record back up to root's QueueHandler and re-enqueue it
        (a feedback-loop / duplicate window), and (b) restoring the snapshotted root
        handlers re-added them in a *closed* state, leaking broken handlers into other
        tests in the same worker. Enqueueing the record directly avoids touching root
        entirely, so neither hazard exists.
        """
        queue = mp_logger._MultiprocessingLogger__queue
        record = logging.LogRecord(
            name=child_name, level=level, pathname=__file__, lineno=0,
            msg=message, args=(), exc_info=None,
        )
        queue.put(record)

    @staticmethod
    def _wait_for_listener_shutdown(mp_logger: MultiprocessingLogger,
                                    timeout: float = 2.0) -> None:
        """Block until the listener self-shuts-down after catching a handler exception.

        The listener polls every ``__LISTENER_SLEEP_INTERVAL_IN_SECS`` (0.1s) and, on
        catching an exception in handle(record), sets ``__listener_shutdown``. A fixed
        ``time.sleep`` here would race the poll on a loaded CI runner (the assertion could
        fire before the listener has drained the queue, leaving ``__listener_exc_info``
        None and failing ``assertRaises`` spuriously). Polling the observable shutdown
        flag with a generous deadline is deterministic instead.
        """
        deadline = time.monotonic() + timeout
        shutdown = mp_logger._MultiprocessingLogger__listener_shutdown
        while not shutdown.is_set():
            if time.monotonic() > deadline:
                raise AssertionError(
                    "Listener did not shut down within {}s after handler exception".format(timeout))
            time.sleep(0.01)

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
            self._wait_for_listener_shutdown(mp_logger)
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
            self._wait_for_listener_shutdown(mp_logger)
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
            self._wait_for_listener_shutdown(mp_logger)
        finally:
            mp_logger.stop()

        # First call re-raises (clears the stashed exc_info to None at line 45)...
        with self.assertRaises(_ListenerSentinelError):
            mp_logger.propagate_exception()
        # ...so the second call is a no-op (returns None, does not raise).
        self.assertIsNone(mp_logger.propagate_exception())

    @pytest.mark.timeout(5)
    def test_inner_queue_empty_does_not_terminate_listener(self):
        # The inner `except queue.Empty: break` (line 77) exits only the drain loop;
        # the outer `while not __listener_shutdown` (line 70) keeps running across
        # the 0.1s sleep cycle. Prove survival: send a record, let the queue empty
        # (sleep past __LISTENER_SLEEP_INTERVAL_IN_SECS=0.1), then send MORE records
        # and assert the LATER batch is still received.
        mp_logger = MultiprocessingLogger(self.logger)
        mp_logger.start()
        try:
            with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
                # First batch
                self._drive_record_in_process(mp_logger, "process_1", logging.INFO,
                                              "before empty cycle")
                # Let the listener drain, hit queue.Empty (inner break), and loop
                # back through the outer while across the 0.1s sleep interval.
                time.sleep(0.3)
                # Second batch AFTER the listener has gone through an empty cycle.
                self._drive_record_in_process(mp_logger, "process_1", logging.INFO,
                                              "after empty cycle")
                time.sleep(0.3)

                log_capture.check(
                    ("process_1", "INFO", "before empty cycle"),
                    ("process_1", "INFO", "after empty cycle"),
                )
        finally:
            mp_logger.stop()

        # Listener never captured an exception during a clean empty-queue cycle.
        self.assertIsNone(mp_logger.propagate_exception())

    @pytest.mark.timeout(5)
    def test_clean_shutdown_joins_without_error(self):
        # NON-HOLLOW: prove the listener was actually PROCESSING records before stop().
        # Enqueue a real record and assert it was RECEIVED via LogCapture BEFORE
        # calling stop(); a no-op stop() against an idle listener cannot satisfy this.
        mp_logger = MultiprocessingLogger(self.logger)
        mp_logger.start()
        try:
            with LogCapture("TestMultiprocessingLogger.MPLogger.process_1") as log_capture:
                self._drive_record_in_process(mp_logger, "process_1", logging.INFO,
                                              "processed before shutdown")
                time.sleep(0.2)  # let the listener drain it
                # Assert-received BEFORE shutdown: proves the listener thread was alive
                # and handling records (the test is not hollow).
                log_capture.check(
                    ("process_1", "INFO", "processed before shutdown"),
                )
            # THEN clean shutdown: stop() must join without raising.
            mp_logger.stop()  # join completes; if it raised, the test fails here
        except BaseException:
            # Ensure the listener thread is not left running on unexpected failure.
            mp_logger.stop()
            raise

        # No handler exception occurred during a clean run -> propagate is a no-op.
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
