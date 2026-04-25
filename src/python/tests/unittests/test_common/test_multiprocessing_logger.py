import unittest
import logging
import sys
import time
import multiprocessing

from testfixtures import LogCapture
import timeout_decorator

from common import MultiprocessingLogger


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

    @timeout_decorator.timeout(5)
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

    @timeout_decorator.timeout(5)
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

    @timeout_decorator.timeout(5)
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
