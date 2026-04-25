"""
Shared pytest fixtures for SeedSyncarr tests.

These fixtures are automatically discovered by pytest for all tests
under the tests/ directory. They are OPTIONAL -- existing unittest.TestCase
tests continue to use their setUp() methods without modification.

New pytest-style tests can request these fixtures by name as function arguments.
"""

import logging

import pytest
from tests.helpers import create_test_logger, create_mock_context, create_mock_context_with_real_config


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
    logger, handler = create_test_logger(request.node.name)
    yield logger
    logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


@pytest.fixture
def mock_context(test_logger):
    """Provides a MagicMock context with standard config attributes.

    All lftp, controller, and general config attributes are pre-populated
    with sensible defaults. Individual tests can override any attribute:

        def test_ssh_key_mode(mock_context):
            mock_context.config.lftp.use_ssh_key = True
            ...
    """
    return create_mock_context(logger=test_logger)


@pytest.fixture
def mock_context_with_real_config(test_logger):
    """Provides a MagicMock context with a REAL Config object.

    Use this when tests need actual Config behavior (validation,
    defaults, serialization) rather than MagicMock attribute access.

        def test_autoqueue_config(mock_context_with_real_config):
            mock_context_with_real_config.config.autoqueue.enabled = True
            ...
    """
    return create_mock_context_with_real_config(logger=test_logger)
