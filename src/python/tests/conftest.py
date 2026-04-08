# Copyright 2017, Inderpreet Singh, All rights reserved.

"""
Shared pytest fixtures for SeedSyncarr tests.

These fixtures are automatically discovered by pytest for all tests
under the tests/ directory. They are OPTIONAL -- existing unittest.TestCase
tests continue to use their setUp() methods without modification.

New pytest-style tests can request these fixtures by name as function arguments.
"""

import logging
import sys

import pytest
from unittest.mock import MagicMock

from common import Config


@pytest.fixture
def test_logger(request):
    """Provides a configured logger for test output.

    Replaces the common setUp pattern:
        logger = logging.getLogger(ClassName.__name__)
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        handler.setFormatter(...)

    Usage in pytest-style tests:
        def test_something(test_logger):
            my_object.set_base_logger(test_logger)
    """
    logger = logging.getLogger(request.node.name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield logger
    logger.removeHandler(handler)


@pytest.fixture
def mock_context(test_logger):
    """Provides a MagicMock context with standard config attributes.

    All lftp, controller, and general config attributes are pre-populated
    with sensible defaults. Individual tests can override any attribute:

        def test_ssh_key_mode(mock_context):
            mock_context.config.lftp.use_ssh_key = True
            ...
    """
    context = MagicMock()
    context.logger = test_logger

    # lftp config
    context.config.lftp.local_path = "/local/path"
    context.config.lftp.remote_address = "remote.server.com"
    context.config.lftp.remote_username = "user"
    context.config.lftp.remote_password = "password"  # Default test credential — not a real secret (test container only)
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


@pytest.fixture
def mock_context_with_real_config(test_logger):
    """Provides a MagicMock context with a REAL Config object.

    Use this when tests need actual Config behavior (validation,
    defaults, serialization) rather than MagicMock attribute access.

        def test_autoqueue_config(mock_context_with_real_config):
            mock_context_with_real_config.config.autoqueue.enabled = True
            ...
    """
    context = MagicMock()
    context.config = Config()
    context.logger = test_logger
    return context
