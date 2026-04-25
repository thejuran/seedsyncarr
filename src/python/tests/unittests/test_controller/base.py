import unittest
from unittest.mock import MagicMock, patch

from controller import Controller
from controller.controller_persist import ControllerPersist
from model import ModelFile


class BaseControllerTestCase(unittest.TestCase):
    """Base class that patches all 6 Controller internal dependencies."""

    def setUp(self):
        self.mock_context = MagicMock()
        self.mock_context.logger = MagicMock()
        self.persist = ControllerPersist(max_tracked_files=100)

        # Start patches for all 6 internal dependencies
        self.patcher_mb = patch('controller.controller.ModelBuilder')
        self.patcher_lftp = patch('controller.controller.LftpManager')
        self.patcher_sm = patch('controller.controller.ScanManager')
        self.patcher_fom = patch('controller.controller.FileOperationManager')
        self.patcher_mpl = patch('controller.controller.MultiprocessingLogger')
        self.patcher_mm = patch('controller.controller.MemoryMonitor')

        self.mock_model_builder_cls = self.patcher_mb.start()
        self.mock_lftp_manager_cls = self.patcher_lftp.start()
        self.mock_scan_manager_cls = self.patcher_sm.start()
        self.mock_file_op_manager_cls = self.patcher_fom.start()
        self.mock_mp_logger_cls = self.patcher_mpl.start()
        self.mock_memory_monitor_cls = self.patcher_mm.start()

        # Get mock instances (return values of mock classes)
        self.mock_model_builder = self.mock_model_builder_cls.return_value
        self.mock_lftp_manager = self.mock_lftp_manager_cls.return_value
        self.mock_scan_manager = self.mock_scan_manager_cls.return_value
        self.mock_file_op_manager = self.mock_file_op_manager_cls.return_value
        self.mock_mp_logger = self.mock_mp_logger_cls.return_value
        self.mock_memory_monitor = self.mock_memory_monitor_cls.return_value
        # Create mock WebhookManager (not patched, passed as parameter)
        self.mock_webhook_manager = MagicMock()
        # Default: process returns empty list (no imports)
        self.mock_webhook_manager.process.return_value = []
        # Default: auto-delete disabled (prevents Timer with MagicMock delay)
        self.mock_context.config.autodelete.enabled = False

        self.controller = Controller(context=self.mock_context, persist=self.persist, webhook_manager=self.mock_webhook_manager)

    def tearDown(self):
        self.patcher_mb.stop()
        self.patcher_lftp.stop()
        self.patcher_sm.stop()
        self.patcher_fom.stop()
        self.patcher_mpl.stop()
        self.patcher_mm.stop()

    def _make_controller_started(self):
        """Helper: set __started flag and configure no-op model update mocks."""
        self.controller._Controller__started = True
        self.mock_scan_manager.pop_latest_results.return_value = (None, None, None)
        self.mock_lftp_manager.status.return_value = None
        self.mock_file_op_manager.pop_extract_statuses.return_value = None
        self.mock_file_op_manager.pop_completed_extractions.return_value = []
        self.mock_model_builder.has_changes.return_value = False

    def _add_file_to_model(self, name, is_dir=False, state=ModelFile.State.DEFAULT,
                           remote_size=None, local_size=None):
        """Helper: create a ModelFile, set properties, add to controller's model."""
        f = ModelFile(name, is_dir)
        if state != ModelFile.State.DEFAULT:
            f.state = state
        if remote_size is not None:
            f.remote_size = remote_size
        if local_size is not None:
            f.local_size = local_size
        self.controller._Controller__model.add_file(f)
        return f

    def _queue_and_process_command(self, action, filename, callbacks=None):
        """Helper: create command, optionally add callbacks, queue, and process."""
        cmd = Controller.Command(action, filename)
        if callbacks:
            for cb in callbacks:
                cmd.add_callback(cb)
        self.controller.queue_command(cmd)
        self.controller.process()
        return cmd
