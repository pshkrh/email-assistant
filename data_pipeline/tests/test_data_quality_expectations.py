"""
Unit tests for the data_quality_expectations funtions.
"""

import os
import sys
import pandas as pd
from pytest_mock import MockerFixture

# Add scripts folder to sys.path
scripts_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.append(scripts_folder)

# pylint: disable=wrong-import-position

from data_quality_expectations import (
    define_expectations,
)  # Assume file is named data_quality_expectations.py

# pylint: enable=wrong-import-position


# pylint: disable=redefined-outer-name
def test_define_expectations_success(mocker: MockerFixture, setup_paths):
    """Test successful definition of expectation suite."""
    # Create a sample CSV with realistic email data
    initial_data = {
        "Message-ID": ["<123@example.com>", "<456@example.com>"],
        "Date": ["2023-01-01", "2023-01-02"],
        "From": ["sender@example.com", "sender2@example.com"],
        "To": ["recipient@example.com", "recipient2@example.com"],
        "Subject": ["Meeting", "Review"],
        "Cc": [None, "cc@example.com"],
        "Bcc": [None, None],
        "X-From": ["Sender Name", "Sender Two"],
        "X-To": ["Recipient Name", "Recipient Two"],
        "X-Cc": [None, None],
        "Body": ["Short body", "Please review this document ASAP."],
    }
    df = pd.DataFrame(initial_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_expectations.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mock_suite = mocker.MagicMock()
    mock_context.suites.add_or_update.return_value = mock_suite
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    result = define_expectations(
        setup_paths["csv_path"],
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == mock_suite
    mock_logger.info.assert_any_call("Setting up Expectations in Suite")
    mock_logger.info.assert_any_call("Created Expectation Suite successfully")
    mock_logger.error.assert_not_called()

    # Verify expectation calls (simplified checks due to mocking)
    assert mock_suite.add_expectation.call_count >= 10  # At least 10 expectations added


def test_define_expectations_missing_csv(mocker: MockerFixture, setup_paths):
    """Test handling of missing CSV file."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_expectations.create_logger", return_value=mock_logger)
    mocker.patch("pandas.read_csv", side_effect=FileNotFoundError("No such file"))
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    result = define_expectations(
        # pylint: disable=duplicate-code
        setup_paths["csv_path"],
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Error in Expectations: No such file", exc_info=True
    )


def test_define_expectations_empty_csv(mocker: MockerFixture, setup_paths, empty_csv):
    """Test handling of an empty CSV."""
    df = pd.DataFrame(empty_csv)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_expectations.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mock_suite = mocker.MagicMock()
    mock_context.suites.add_or_update.return_value = mock_suite
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    result = define_expectations(
        setup_paths["csv_path"],
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == mock_suite
    mock_logger.info.assert_any_call("Setting up Expectations in Suite")
    mock_logger.info.assert_any_call("Created Expectation Suite successfully")
    mock_logger.error.assert_not_called()


def test_define_expectations_anomalies(mocker: MockerFixture, setup_paths):
    """Test expectation suite with data containing anomalies."""
    initial_data = {
        "Message-ID": ["<123@example.com>", None],  # Null Message-ID
        "Date": ["2023-01-01", "1980-01-01"],  # Out-of-range date
        "From": ["sender@example.com", "invalid"],  # Invalid email
        "To": ["recipient@example.com", None],  # Null To
        "Subject": ["Meeting", None],  # Null Subject
        "Cc": [None, "cc@example.com"],
        "Bcc": [None, None],
        "X-From": ["Sender Name", None],  # Null X-From
        "X-To": ["Recipient Name", "Recipient Two"],
        "X-Cc": [None, None],
        "Body": ["Short body", None],  # Null Body
    }
    df = pd.DataFrame(initial_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_expectations.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mock_suite = mocker.MagicMock()
    mock_context.suites.add_or_update.return_value = mock_suite
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    result = define_expectations(
        setup_paths["csv_path"],
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == mock_suite
    mock_logger.info.assert_any_call("Setting up Expectations in Suite")
    mock_logger.info.assert_any_call("Created Expectation Suite successfully")
    mock_logger.error.assert_not_called()
