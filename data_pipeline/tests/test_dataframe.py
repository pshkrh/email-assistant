"""
Unit tests for the process_enron_emails functions.
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
from dataframe import (
    extract_email_data,
    process_enron_emails,
)  # Updated import to match file name

# pylint: enable=wrong-import-position


@pytest.fixture
def setup_paths(tmp_path):
    """Fixture to create temporary paths for testing."""
    return {
        "data_dir": str(tmp_path / "emails"),
        "csv_path": str(tmp_path / "enron_emails.csv"),
        "log_path": str(tmp_path / "logs" / "test_data_preprocessing_log.log"),
        "logger_name": "test_data_preprocessing_logger",
    }


@pytest.fixture
def header_keys():
    """Fixture for email header keys."""
    return [
        "Message-ID",
        "Date",
        "From",
        "To",
        "Subject",
        "Cc",
        "Bcc",
        "X-From",
        "X-To",
        "X-Cc",
    ]


# pylint: disable=redefined-outer-name
def test_extract_email_data_success(mocker: MockerFixture, tmp_path, header_keys):
    """Test successful extraction of email data."""
    email_path = str(tmp_path / "test_email.txt")
    with open(email_path, "w", encoding="utf-8") as f:
        f.write("From: test@example.com\nSubject: Test Email\n\nHello, this is a test.")

    mock_logger = mocker.MagicMock()
    result = extract_email_data(email_path, mock_logger, header_keys)

    assert result is not None
    assert result["From"] == "test@example.com"
    assert result["Subject"] == "Test Email"
    assert result["Body"] == "Hello, this is a test."
    for key in header_keys:
        assert key in result
    mock_logger.error.assert_not_called()


def test_extract_email_data_file_not_found(
    mocker: MockerFixture, tmp_path, header_keys
):
    """Test raising FileNotFoundError when email file is missing."""
    email_path = str(tmp_path / "nonexistent_email.txt")
    mock_logger = mocker.MagicMock()

    with pytest.raises(FileNotFoundError) as exc_info:
        extract_email_data(email_path, mock_logger, header_keys)
    assert str(exc_info.value) == f"Email file not found: {email_path}"


def test_process_emails_success(mocker: MockerFixture, setup_paths):
    """Test successful processing of emails into a DataFrame."""
    # Create a mock email structure
    os.makedirs(os.path.join(setup_paths["data_dir"], "person1"), exist_ok=True)
    email_path = os.path.join(setup_paths["data_dir"], "person1", "email1.txt")
    with open(email_path, "w", encoding="utf-8") as f:
        f.write("From: person1@example.com\nSubject: Test\n\nHi there.")

    mock_logger = mocker.MagicMock()
    mocker.patch(
        "dataframe.create_logger", return_value=mock_logger
    )  # Updated module name
    mocker.patch(
        "os.walk",
        return_value=[
            (setup_paths["data_dir"], ["person1"], []),
            (os.path.join(setup_paths["data_dir"], "person1"), [], ["email1.txt"]),
        ],
    )

    result = process_enron_emails(
        setup_paths["data_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
        setup_paths["csv_path"],
    )

    assert result == setup_paths["csv_path"]
    assert os.path.exists(setup_paths["csv_path"])
    df = pd.read_csv(setup_paths["csv_path"])
    assert len(df) == 1
    assert df["From"].iloc[0] == "person1@example.com"
    # pylint: disable=logging-fstring-interpolation
    mock_logger.info.assert_any_call(f"Processing emails in: {setup_paths['data_dir']}")
    mock_logger.info.assert_any_call("Total emails processed: 1")
    mock_logger.info.assert_any_call("DataFrame created successfully.")
    mock_logger.info.assert_any_call(
        f"DataFrame saved to {setup_paths['csv_path']} successfully in process_enron_emails."
    )
    # pylint: enable=logging-fstring-interpolation


def test_process_emails_directory_not_found(mocker: MockerFixture, setup_paths):
    """Test raising FileNotFoundError for non-existent data directory."""
    mock_logger = mocker.MagicMock()
    mocker.patch(
        "dataframe.create_logger", return_value=mock_logger
    )  # Updated module name
    mocker.patch("os.path.exists", return_value=False)

    with pytest.raises(FileNotFoundError) as exc_info:
        process_enron_emails(
            setup_paths["data_dir"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
            setup_paths["csv_path"],
        )
    # pylint: disable=logging-fstring-interpolation
    assert str(exc_info.value) == f"Directory {setup_paths['data_dir']} does not exist!"
    # pylint: enable=logging-fstring-interpolation


def test_process_emails_invalid_input(mocker: MockerFixture, setup_paths):
    """Test raising ValueError for invalid input."""
    mock_logger = mocker.MagicMock()
    mocker.patch(
        "dataframe.create_logger", return_value=mock_logger
    )  # Updated module name

    with pytest.raises(ValueError) as exc_info:
        process_enron_emails(
            "",
            setup_paths["log_path"],
            setup_paths["logger_name"],
            setup_paths["csv_path"],
        )
    assert str(exc_info.value) == "One or more input parameters are empty"


if __name__ == "__main__":
    pytest.main()
