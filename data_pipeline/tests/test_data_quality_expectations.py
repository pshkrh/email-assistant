"""
Unit tests for the data_quality_expectations funtions.
"""

import os
import sys
import pandas as pd
import pytest
from pytest_mock import MockerFixture

# Add scripts folder to sys.path
scripts_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.append(scripts_folder)

# pylint: disable=wrong-import-position
from data_quality_expectations import define_expectations

# pylint: enable=wrong-import-position


@pytest.fixture
def setup_paths(tmp_path):
    """Fixture to create temporary paths for testing."""
    return {
        "csv_path": str(tmp_path / "enron_emails.csv"),
        "context_root_dir": str(tmp_path / "gx"),
        "log_path": str(tmp_path / "logs" / "data_quality_log.log"),
        "logger_name": "test_data_quality_logger",
    }


@pytest.fixture
def empty_csv():
    """Fixture for an empty CSV structure."""
    return {
        "Message-ID": [],
        "Date": [],
        "From": [],
        "To": [],
        "Subject": [],
        "Cc": [],
        "Bcc": [],
        "X-From": [],
        "X-To": [],
        "X-Cc": [],
        "Body": [],
    }


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
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    with pytest.raises(FileNotFoundError) as exc_info:
        define_expectations(
            # pylint: disable=duplicate-code
            setup_paths["csv_path"],
            setup_paths["context_root_dir"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == f"CSV file not found: {setup_paths['csv_path']}"
    mock_logger.error.assert_called_once_with(
        f"CSV file not found: {setup_paths['csv_path']}"
    )


def test_define_expectations_empty_csv(mocker: MockerFixture, setup_paths):
    """Test handling of an empty CSV."""
    with open(setup_paths["csv_path"], "w", encoding="utf-8") as f:
        f.write("")  # Create a truly empty file

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_expectations.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    with pytest.raises(pd.errors.EmptyDataError) as exc_info:
        define_expectations(
            setup_paths["csv_path"],
            setup_paths["context_root_dir"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == f"CSV file is empty: {setup_paths['csv_path']}"
    mock_logger.error.assert_called_once_with(
        f"CSV file is empty: {setup_paths['csv_path']}"
    )


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


def test_define_expectations_invalid_input(mocker: MockerFixture, setup_paths):
    """Test raising ValueError for invalid input."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_expectations.create_logger", return_value=mock_logger)

    with pytest.raises(ValueError) as exc_info:
        define_expectations(
            "",
            setup_paths["context_root_dir"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == "One or more input parameters are empty"


if __name__ == "__main__":
    pytest.main()
