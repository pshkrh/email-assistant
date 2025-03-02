"""
Unit tests for the create_logger funtion.
"""

import os
import sys
import logging
from pytest_mock import MockerFixture
import pytest

# Add scripts folder to sys.path
scripts_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.append(scripts_folder)

# pylint: disable=wrong-import-position

from create_logger import create_logger

# pylint: enable=wrong-import-position


@pytest.fixture
def temp_log_path(tmp_path):
    """Fixture to provide a temporary log file path."""
    return str(tmp_path / "logs" / "test_logger.log")


@pytest.fixture(autouse=True)
def reset_logging():
    """Fixture to reset logging handlers between tests."""
    logging.getLogger("test_logger").handlers = []
    logging.getLogger("logger1").handlers = []
    logging.getLogger("logger2").handlers = []


# pylint: disable=redefined-outer-name
def test_create_logger_success(temp_log_path):
    """Test successful creation of a logger with correct configuration."""
    logger = create_logger(temp_log_path, "test_logger")

    # Verify logger properties
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1

    # Verify handler
    handler = logger.handlers[0]
    assert isinstance(handler, logging.FileHandler)
    assert handler.baseFilename == os.path.abspath(temp_log_path)

    # Verify formatter
    formatter = handler.formatter
    assert isinstance(formatter, logging.Formatter)
    log_output = formatter.format(
        logging.LogRecord("", logging.DEBUG, "", 0, "Test", None, None)
    )
    assert "DEBUG - Test" in log_output

    assert callable(formatter.converter)

    # Test logging
    logger.debug("Test message")
    with open(temp_log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "DEBUG - Test message" in log_content


def test_create_logger_directory_creation(mocker: MockerFixture, temp_log_path):
    """Test directory creation when it doesn't exist."""
    # Mock os.path.exists to simulate non-existent directory
    mocker.patch("os.path.exists", return_value=False)
    mock_makedirs = mocker.patch("os.makedirs")
    # Mock FileHandler to avoid file creation
    mock_file_handler = mocker.patch("logging.FileHandler")

    logger = create_logger(temp_log_path, "test_logger")

    # Verify directory creation was attempted
    mock_makedirs.assert_called_once_with(os.path.dirname(temp_log_path), exist_ok=True)
    assert logger.name == "test_logger"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    mock_file_handler.assert_called_once_with(temp_log_path)


def test_create_logger_existing_directory(temp_log_path):
    """Test logger creation with an existing directory."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(temp_log_path), exist_ok=True)

    logger = create_logger(temp_log_path, "test_logger")

    # Verify logger works with pre-existing directory
    assert logger.name == "test_logger"
    assert len(logger.handlers) == 1
    logger.debug("Existing dir test")
    with open(temp_log_path, "r", encoding="utf-8") as f:
        assert "Existing dir test" in f.read()


def test_create_logger_permission_denied(mocker: MockerFixture, temp_log_path):
    """Test handling of permission denied during directory creation."""
    mocker.patch("os.makedirs", side_effect=PermissionError("Permission denied"))

    with pytest.raises(PermissionError, match="Permission denied"):
        create_logger(temp_log_path, "test_logger")


def test_create_logger_file_creation_failure(mocker: MockerFixture, temp_log_path):
    """Test handling of file creation failure."""
    mocker.patch("logging.FileHandler", side_effect=OSError("File creation failed"))

    with pytest.raises(OSError, match="File creation failed"):
        create_logger(temp_log_path, "test_logger")


def test_create_logger_multiple_calls_same_name(temp_log_path):
    """Test creating multiple loggers with the same name adds handlers."""
    logger1 = create_logger(temp_log_path, "test_logger")
    logger2 = create_logger(temp_log_path, "test_logger")

    # Verify they're the same logger instance
    assert logger1 is logger2
    # Expect 2 handlers since create_logger adds a new one each call
    assert len(logger1.handlers) == 2
    logger1.debug("First message")
    logger2.debug("Second message")
    with open(temp_log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "First message" in log_content
        assert "Second message" in log_content


def test_create_logger_different_names(temp_log_path):
    """Test creating loggers with different names."""
    logger1 = create_logger(temp_log_path, "logger1")
    logger2 = create_logger(f"{temp_log_path}_2", "logger2")

    # Verify they're different loggers
    assert logger1 is not logger2
    assert logger1.name == "logger1"
    assert logger2.name == "logger2"
    assert logger1.handlers[0].baseFilename != logger2.handlers[0].baseFilename
    assert len(logger1.handlers) == 1
    assert len(logger2.handlers) == 1


if __name__ == "__main__":
    pytest.main(["-v"])
