"""
Unit tests for the data_quality_validation funtions.
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
)  # Assume file is named dataframe.py

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


def test_process_emails_success(mocker: MockerFixture, setup_paths):
    """Test successful processing of emails into a DataFrame."""
    # Create a mock email structure
    os.makedirs(os.path.join(setup_paths["data_dir"], "person1"), exist_ok=True)
    email_path = os.path.join(setup_paths["data_dir"], "person1", "email1.txt")
    with open(email_path, "w", encoding="utf-8") as f:
        f.write("From: person1@example.com\nSubject: Test\n\nHi there.")

    mock_logger = mocker.MagicMock()
    mocker.patch("dataframe.create_logger", return_value=mock_logger)
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
    mock_logger.info.assert_any_call(f"Processing emails in: {setup_paths['data_dir']}")
    mock_logger.info.assert_any_call("Total emails processed: 1")
    mock_logger.info.assert_any_call("DataFrame created successfully.")
    mock_logger.info.assert_any_call(
        f"DataFrame saved to {setup_paths['csv_path']} successfully in process_enron_emails."
    )


def test_process_emails_with_real_data(mocker: MockerFixture, setup_paths):
    """Test processing real emails from /data_pipeline/tests/data/emails."""
    real_data_dir = os.path.join(os.path.dirname(__file__), "data", "emails")
    assert os.path.exists(
        real_data_dir
    ), f"Real email directory not found at {real_data_dir}"

    mock_logger = mocker.MagicMock()
    mocker.patch("dataframe.create_logger", return_value=mock_logger)

    result = process_enron_emails(
        real_data_dir,
        setup_paths["log_path"],
        setup_paths["logger_name"],
        setup_paths["csv_path"],
    )

    assert result == setup_paths["csv_path"]
    assert os.path.exists(setup_paths["csv_path"])
    df = pd.read_csv(setup_paths["csv_path"])
    assert len(df) > 0  # Assuming the folder has at least one email file
    mock_logger.info.assert_any_call(f"Processing emails in: {real_data_dir}")
    mock_logger.info.assert_any_call(f"Total emails processed: {len(df)}")
    mock_logger.info.assert_any_call("DataFrame created successfully.")
    mock_logger.info.assert_any_call(
        f"DataFrame saved to {setup_paths['csv_path']} successfully in process_enron_emails."
    )


def test_process_emails_directory_not_found(mocker: MockerFixture, setup_paths):
    """Test handling of non-existent data directory."""
    mock_logger = mocker.MagicMock()
    mocker.patch("dataframe.create_logger", return_value=mock_logger)
    mocker.patch("os.path.exists", return_value=False)

    result = process_enron_emails(
        setup_paths["data_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
        setup_paths["csv_path"],
    )

    assert isinstance(result, pd.DataFrame)
    assert result.empty
    mock_logger.error.assert_called_once_with(
        f"Directory {setup_paths['data_dir']} does not exist!"
    )


def test_process_emails_empty_directory(mocker: MockerFixture, setup_paths):
    """Test processing an empty directory."""
    os.makedirs(setup_paths["data_dir"], exist_ok=True)
    mock_logger = mocker.MagicMock()
    mocker.patch("dataframe.create_logger", return_value=mock_logger)
    mocker.patch("os.walk", return_value=[(setup_paths["data_dir"], [], [])])

    result = process_enron_emails(
        setup_paths["data_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
        setup_paths["csv_path"],
    )

    assert result == setup_paths["csv_path"]
    mock_logger.info.assert_any_call(f"Processing emails in: {setup_paths['data_dir']}")
    mock_logger.info.assert_any_call("Total emails processed: 0")
    mock_logger.info.assert_any_call("DataFrame created successfully.")
    mock_logger.info.assert_any_call(
        f"DataFrame saved to {setup_paths['csv_path']} successfully in process_enron_emails."
    )


if __name__ == "__main__":
    pytest.main()
