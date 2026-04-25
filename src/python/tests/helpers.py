"""
Importable helper functions for test setup.

These functions back the conftest.py pytest fixtures AND can be called
directly from unittest.TestCase.setUp() methods -- solving the problem
of conftest fixtures being unreachable by unittest-style tests.
"""

import logging
import sys
from unittest.mock import MagicMock

from common import Config


def create_test_logger(name: str) -> tuple:
    """Create a configured test logger with StreamHandler to stdout.

    Returns:
        (logger, handler) tuple. Caller is responsible for calling
        logger.removeHandler(handler) in tearDown.
    """
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger, handler


def create_mock_context(logger=None):
    """Create a MagicMock context with standard config attributes.

    Args:
        logger: Optional logger instance. Defaults to MagicMock() if not provided.

    Returns:
        MagicMock context with lftp, controller, general config and args populated.
    """
    context = MagicMock()
    context.logger = logger if logger is not None else MagicMock()

    # lftp config
    context.config.lftp.local_path = "/local/path"
    context.config.lftp.remote_address = "remote.server.com"
    context.config.lftp.remote_username = "user"
    context.config.lftp.remote_password = "password"  # Default test credential -- not a real secret (test container only)
    context.config.lftp.use_ssh_key = False
    context.config.lftp.remote_port = 22
    context.config.lftp.remote_path = "/remote/path"
    context.config.lftp.remote_path_to_scan_script = "/usr/bin/scanfs"
    context.config.lftp.use_temp_file = False
    context.config.lftp.num_max_parallel_downloads = 2
    context.config.lftp.num_max_parallel_files_per_download = 3
    context.config.lftp.num_max_connections_per_root_file = 4
    context.config.lftp.num_max_connections_per_dir_file = 2
    context.config.lftp.num_max_total_connections = 8

    # controller config
    context.config.controller.interval_ms_downloading_scan = 500
    context.config.controller.interval_ms_local_scan = 30000
    context.config.controller.interval_ms_remote_scan = 30000
    context.config.controller.use_local_path_as_extract_path = True
    context.config.controller.extract_path = "/extract/path"

    # general config
    context.config.general.verbose = False

    # args
    context.args.local_path_to_scanfs = "/local/bin/scanfs"

    return context


def create_mock_context_with_real_config(logger=None):
    """Create a MagicMock context with a REAL Config object.

    Use when tests need actual Config behavior (validation, defaults,
    serialization) rather than MagicMock attribute access.

    Args:
        logger: Optional logger instance. Defaults to MagicMock() if not provided.

    Returns:
        MagicMock context with context.config = Config().
    """
    context = MagicMock()
    context.config = Config()
    context.logger = logger if logger is not None else MagicMock()
    return context
