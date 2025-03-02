"""
Unit tests for the data_quality_setup funtions.
"""

import os
import sys
import warnings
import pytest
import pandas as pd
from pytest_mock import MockerFixture

warnings.simplefilter("always")


# Add scripts folder to sys.path
scripts_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.append(scripts_folder)

# pylint: disable=wrong-import-position

from data_quality_setup import (
    setup_gx_context_and_logger,
)  # Assume the file is named data_quality_setup.py

# pylint: enable=wrong-import-position


@pytest.fixture
def setup_paths(tmp_path):
    """Fixture to create temporary paths for testing."""
    return {
        "context_root_dir": str(tmp_path / "gx"),
        "log_path": str(tmp_path / "logs" / "test_data_quality_log.log"),
        "logger_name": "test_data_quality_logger",
    }


# pylint: disable=redefined-outer-name
def test_setup_gx_context_and_logger_success(mocker: MockerFixture, setup_paths):
    """Test successful setup of Great Expectations context and logger."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_setup.create_logger", return_value=mock_logger)
    mock_makedirs = mocker.patch("os.makedirs")
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    result = setup_gx_context_and_logger(
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["context_root_dir"]
    mock_makedirs.assert_called_once_with(
        setup_paths["context_root_dir"], exist_ok=True
    )
    mock_logger.info.assert_called_once_with(
        "Successfully created gx-context and logger"
    )
    mock_logger.error.assert_not_called()


def test_setup_gx_context_and_logger_dir_creation_failure(
    mocker: MockerFixture, setup_paths
):
    """Test failure in directory creation."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_setup.create_logger", return_value=mock_logger)
    mocker.patch("os.makedirs", side_effect=PermissionError("Permission denied"))

    result = setup_gx_context_and_logger(
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Error creating gx context: Permission denied", exc_info=True
    )


def test_setup_gx_context_and_logger_gx_context_failure(
    mocker: MockerFixture, setup_paths
):
    """Test failure in Great Expectations context creation."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_setup.create_logger", return_value=mock_logger)
    mocker.patch("os.makedirs")
    mocker.patch(
        "great_expectations.get_context", side_effect=Exception("GX context error")
    )

    result = setup_gx_context_and_logger(
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Error creating gx context: GX context error", exc_info=True
    )


def test_setup_gx_context_and_logger_existing_dir(mocker: MockerFixture, setup_paths):
    """Test setup when the context directory already exists."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_setup.create_logger", return_value=mock_logger)
    mock_makedirs = mocker.patch("os.makedirs")
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)
    mocker.patch("os.path.exists", return_value=True)

    result = setup_gx_context_and_logger(
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["context_root_dir"]
    mock_makedirs.assert_called_once_with(
        setup_paths["context_root_dir"], exist_ok=True
    )
    mock_logger.info.assert_called_once_with(
        "Successfully created gx-context and logger"
    )
    mock_logger.error.assert_not_called()


# Placeholder test for full pipeline (requires external scripts)
def test_full_pipeline_placeholder(mocker: MockerFixture, setup_paths, tmp_path):
    """Placeholder test for the full pipeline - requires external scripts."""
    # Mock setup
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_setup.create_logger", return_value=mock_logger)
    mocker.patch("os.makedirs")
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    # Mock external functions (replace with real imports if provided)
    mock_suite = mocker.MagicMock()
    mocker.patch("data_quality_setup.define_expectations", return_value=mock_suite)
    mock_validation_results = mocker.MagicMock()
    mocker.patch(
        "data_quality_setup.validate_data", return_value=mock_validation_results
    )
    mocker.patch("data_quality_setup.handle_anomalies")

    # Create a dummy CSV
    csv_path = str(tmp_path / "enron_emails.csv")
    pd.DataFrame(
        {
            "Message-ID": ["<123@example.com>"],
            "Date": ["Mon, 2 Jan 02 14:30:00 -0800 (PST)"],
            "From": ["sender@example.com"],
            "To": ["recipient@example.com"],
            "Subject": ["Test Email"],
            "Body": ["Hello"],
        }
    ).to_csv(csv_path, index=False)

    context_root_dir = setup_gx_context_and_logger(
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )
    assert context_root_dir == setup_paths["context_root_dir"]

    # Placeholder assertions - expand with real suite/validation logic if provided
    mock_logger.info.assert_called_once_with(
        "Successfully created gx-context and logger"
    )


if __name__ == "__main__":
    pytest.main()
