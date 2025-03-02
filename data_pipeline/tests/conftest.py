"""
Fixtures for unit tests in the data pipeline.

This module provides reusable pytest fixtures for testing data preprocessing
functions, including sample email data, logging paths, and header keys.
"""

import pytest
import pandas as pd


@pytest.fixture
def setup_paths(tmp_path):
    """Fixture to create temporary paths for testing."""
    return {
        "csv_path": str(tmp_path / "enron_emails.csv"),
        "log_path": str(tmp_path / "logs" / "test_data_preprocessing_log.log"),
        "logger_name": "test_data_preprocessing_logger",
        "context_root_dir": str(tmp_path / "gx"),
    }


@pytest.fixture
def header_keys():
    """Fixture for HEADER_KEYS used in extract_email_data."""
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
def empty_csv():
    """Fixture for empty csv."""
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


@pytest.fixture
def sample_email_data():
    """Fixture to provide sample email data for testing."""
    return pd.DataFrame(
        {
            "Message-ID": ["<123@example.com>"],
            "Date": ["Mon, 2 Jan 02 14:30:00 -0800 (PST)"],
            "From": ["sender@example.com"],
            "To": ["recipient@example.com"],
            "Subject": ["Test Email"],
            "Cc": [None],
            "Bcc": [None],
            "X-From": ["Sender Name"],
            "X-To": ["Recipient Name"],
            "X-Cc": [None],
            "Body": ["Hello, this is a test."],
        }
    )
