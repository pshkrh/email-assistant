"""
Unit tests for the clean_and_parse_dates funtion.
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
from clean_and_parse_dates import clean_and_parse_dates

# pylint: enable=wrong-import-position


@pytest.fixture
def setup_paths(tmp_path):
    """Fixture to create temporary paths for testing."""
    return {
        "csv_path": str(tmp_path / "enron_emails.csv"),
        "log_path": str(tmp_path / "logs" / "test_data_preprocessing_log.log"),
        "logger_name": "test_data_preprocessing_logger",
    }


@pytest.fixture
def header_keys():
    """Fixture for HEADER_KEYS excluding Date, which is processed separately."""
    return [
        "Message-ID",
        "From",
        "To",
        "Subject",
        "Cc",
        "Bcc",
        "X-From",
        "X-To",
        "X-Cc",
    ]


@pytest.fixture
def sample_email_data():
    """Fixture for sample email data."""
    data = {
        "Message-ID": ["<123@example.com>"],
        "Date": ["Wed, 2 Jan 2002 14:30:00 -0800 (PST)"],
        "From": ["sender@example.com"],
        "To": ["recipient@example.com"],
        "Subject": ["Test Email"],
        "Cc": [None],
        "Bcc": [None],
        "X-From": ["Sender Name"],
        "X-To": ["Recipient Name"],
        "X-Cc": [None],
        "Body": ["This is a test email."],
    }
    return data


# pylint: disable=redefined-outer-name
def test_clean_and_parse_dates_success(
    mocker: MockerFixture, sample_email_data, setup_paths, header_keys
):
    """Test successful cleaning and parsing of dates."""
    df = pd.DataFrame(sample_email_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("clean_and_parse_dates.create_logger", return_value=mock_logger)

    result = clean_and_parse_dates(
        setup_paths["csv_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["csv_path"]
    processed_df = pd.read_csv(setup_paths["csv_path"])

    # Check preserved columns
    for key in header_keys:
        assert key in processed_df.columns
        assert (
            processed_df[key].iloc[0] == sample_email_data[key][0]
            if sample_email_data[key][0] is not None
            else "nan"
        )

    # Check date-related columns
    assert processed_df["Date"].iloc[0] == "2002-01-02"  # Parsed date
    assert processed_df["Day"].iloc[0] == "Wednesday"
    assert processed_df["Time"].iloc[0] == "22:30:00"  # UTC adjusted from -0800
    assert processed_df["Original_Timezone"].iloc[0] == " (PST)"

    # Check logging
    mock_logger.info.assert_any_call("Created Original_Timezone in Dataframe")
    mock_logger.info.assert_any_call("Cleaned Date in Dataframe")
    mock_logger.info.assert_any_call("Converted to datetime format in Dataframe")
    mock_logger.info.assert_any_call("Created Day in Dataframe")
    mock_logger.info.assert_any_call("Created Time in Dataframe")
    mock_logger.info.assert_any_call("Created Date in Dataframe")
    mock_logger.info.assert_any_call("Droped Temporary Columns from Dataframe")
    mock_logger.info.assert_any_call(
        "DataFrame saved to enron_emails.csv successfully."
    )


def test_clean_and_parse_dates_invalid_date(
    mocker: MockerFixture, setup_paths, header_keys, sample_email_data
):
    """Test handling of invalid date formats."""
    initial_data = {
        "Message-ID": ["<456@example.com>"],
        "Date": ["Invalid Date String"],
        "From": ["sender2@example.com"],
        "To": ["recipient2@example.com"],
        "Subject": ["Test 2"],
        "Cc": sample_email_data["Cc"],
        "Bcc": sample_email_data["Bcc"],
        "X-From": ["Sender Two"],
        "X-To": ["Recipient Two"],
        "X-Cc": sample_email_data["X-Cc"],
        "Body": ["Test body."],
    }
    df = pd.DataFrame(initial_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("clean_and_parse_dates.create_logger", return_value=mock_logger)

    result = clean_and_parse_dates(
        setup_paths["csv_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["csv_path"]
    processed_df = pd.read_csv(setup_paths["csv_path"])

    # Check preserved columns
    for key in header_keys:
        assert key in processed_df.columns
        assert (
            processed_df[key].iloc[0] == initial_data[key][0]
            if initial_data[key][0] is not None
            else "nan"
        )
    # Check date-related columns with invalid date
    assert pd.isna(processed_df["Date"].iloc[0])
    assert pd.isna(processed_df["Day"].iloc[0])
    assert pd.isna(processed_df["Time"].iloc[0])
    assert pd.isna(processed_df["Original_Timezone"].iloc[0])

    mock_logger.info.assert_any_call("Converted to datetime format in Dataframe")


def test_clean_and_parse_dates_missing_csv(mocker: MockerFixture, setup_paths):
    """Test handling of missing CSV file."""
    mock_logger = mocker.MagicMock()
    mocker.patch("clean_and_parse_dates.create_logger", return_value=mock_logger)

    with pytest.raises(FileNotFoundError) as exc_info:
        clean_and_parse_dates(
            setup_paths["csv_path"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == f"CSV file not found: {setup_paths['csv_path']}"
    mock_logger.error.assert_called_once_with(
        f"CSV file not found: {setup_paths['csv_path']}"
    )


def test_clean_and_parse_dates_empty_csv(mocker: MockerFixture, setup_paths):
    """Test processing an empty CSV."""
    with open(setup_paths["csv_path"], "w", encoding="utf-8") as f:
        f.write("")  # Create a truly empty file

    mock_logger = mocker.MagicMock()
    mocker.patch("clean_and_parse_dates.create_logger", return_value=mock_logger)

    with pytest.raises(pd.errors.EmptyDataError) as exc_info:
        clean_and_parse_dates(
            setup_paths["csv_path"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == f"CSV file is empty: {setup_paths['csv_path']}"
    mock_logger.error.assert_called_once_with(
        f"CSV file is empty: {setup_paths['csv_path']}"
    )


def test_clean_and_parse_dates_multiple_emails(
    mocker: MockerFixture, setup_paths, header_keys
):
    """Test processing multiple emails with various date formats."""
    initial_data = {
        "Message-ID": ["<1@example.com>", "<2@example.com>"],
        "Date": [
            "Tue, 15 May 01 09:15:00 -0700 (PDT)",  # 2-digit year
            "Wed, 05 December 1999 12:00:00 +0000 (GMT)",  # 4-digit year
        ],
        "From": ["a@example.com", "b@example.com"],
        "To": ["c@example.com", "d@example.com"],
        "Subject": ["Meeting", "Report"],
        "Cc": [None, None],
        "Bcc": [None, None],
        "X-From": ["A", "B"],
        "X-To": ["C", "D"],
        "X-Cc": [None, None],
        "Body": ["Body 1", "Body 2"],
    }
    df = pd.DataFrame(initial_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("clean_and_parse_dates.create_logger", return_value=mock_logger)

    result = clean_and_parse_dates(
        setup_paths["csv_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["csv_path"]
    processed_df = pd.read_csv(setup_paths["csv_path"])

    # Check preserved columns
    for key in header_keys:
        assert key in processed_df.columns
        assert (
            processed_df[key].iloc[0] == initial_data[key][0]
            if initial_data[key][0] is not None
            else "nan"
        )
        assert (
            processed_df[key].iloc[1] == initial_data[key][1]
            if initial_data[key][1] is not None
            else "nan"
        )

    # Check date parsing
    assert processed_df["Date"].iloc[0] == "2001-05-15"
    assert processed_df["Day"].iloc[0] == "Tuesday"
    assert processed_df["Time"].iloc[0] == "16:15:00"  # UTC from -0700
    assert processed_df["Original_Timezone"].iloc[0] == " (PDT)"

    assert processed_df["Date"].iloc[1] == "1999-12-05"
    assert processed_df["Day"].iloc[1] == "Sunday"
    assert processed_df["Time"].iloc[1] == "12:00:00"  # UTC no adjustment
    assert processed_df["Original_Timezone"].iloc[1] == " (GMT)"

    mock_logger.info.assert_any_call("Converted to datetime format in Dataframe")


def test_clean_and_parse_dates_invalid_input(mocker: MockerFixture, setup_paths):
    """Test raising ValueError for invalid input."""
    mock_logger = mocker.MagicMock()
    mocker.patch("clean_and_parse_dates.create_logger", return_value=mock_logger)

    with pytest.raises(ValueError) as exc_info:
        clean_and_parse_dates("", setup_paths["log_path"], setup_paths["logger_name"])
    assert str(exc_info.value) == "One or more input parameters are empty"


if __name__ == "__main__":
    pytest.main()
