"""
Unit tests for the data_quality_validation funtions.
"""

import os
import sys
import requests
import pytest
from pytest_mock import MockerFixture

# Add scripts folder to sys.path
scripts_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.append(scripts_folder)

# pylint: disable=wrong-import-position

from download_dataset import download_enron_dataset

# pylint: enable=wrong-import-position


@pytest.fixture
def setup_paths(tmp_path):
    """Fixture to create temporary paths for testing."""
    return {
        "save_path": str(tmp_path / "enron_mail_20150507.tar.gz"),
        "log_path": str(tmp_path / "logs" / "test_data_downloading_log.log"),
        "logger_name": "test_data_downloading_logger",
    }


# pylint: disable=redefined-outer-name
def test_download_success(mocker: MockerFixture, setup_paths):
    """Test if the dataset downloads successfully."""
    mocker.patch("os.path.exists", return_value=False)
    mock_makedirs = mocker.patch("download_dataset.os.makedirs")
    mock_logger = mocker.MagicMock()
    mocker.patch("download_dataset.create_logger", return_value=mock_logger)
    mock_response = mocker.MagicMock()
    mock_response.headers = {"content-length": "1024"}
    mock_response.iter_content.return_value = [b"data"] * 2
    mock_response.raise_for_status.return_value = None
    mocker.patch("requests.get", return_value=mock_response)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())

    result = download_enron_dataset(
        "https://example.com",
        setup_paths["save_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["save_path"]
    mock_makedirs.assert_called_once_with(
        os.path.dirname(setup_paths["save_path"]), exist_ok=True
    )
    mock_logger.info.assert_any_call("Downloading the Enron dataset...")
    mock_logger.info.assert_any_call(
        "Dataset Downloaded Successfully at %s", setup_paths["save_path"]
    )
    mock_open.assert_called_once_with(setup_paths["save_path"], "wb")


def test_file_exists(mocker: MockerFixture, setup_paths):
    """Test if function skips download when file already exists."""
    mocker.patch("os.path.exists", return_value=True)
    mock_logger = mocker.MagicMock()
    mocker.patch("download_dataset.create_logger", return_value=mock_logger)

    result = download_enron_dataset(
        "https://example.com",
        setup_paths["save_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.info.assert_called_once_with(
        "Dataset archive already exists, skipping download."
    )
    assert not mocker.patch("requests.get").called


def test_empty_url(mocker: MockerFixture, setup_paths):
    """Test if function handles empty URL errors."""
    mocker.patch("os.path.exists", return_value=False)
    mock_logger = mocker.MagicMock()
    mocker.patch("download_dataset.create_logger", return_value=mock_logger)

    result = download_enron_dataset(
        "",
        setup_paths["save_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    assert any(
        "Error downloading dataset: Invalid URL" in call.args[0]
        for call in mock_logger.error.call_args_list
    )


def test_zero_content_length(mocker: MockerFixture, setup_paths):
    """Test if function handles zero content length."""
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("download_dataset.os.makedirs")
    mock_logger = mocker.MagicMock()
    mocker.patch("download_dataset.create_logger", return_value=mock_logger)
    mock_response = mocker.MagicMock()
    mock_response.headers = {"content-length": "0"}
    mock_response.iter_content.return_value = []
    mock_response.raise_for_status.return_value = None
    mocker.patch("requests.get", return_value=mock_response)
    mocker.patch("builtins.open", mocker.mock_open())
    mock_tqdm = mocker.patch("download_dataset.tqdm", return_value=mocker.MagicMock())

    result = download_enron_dataset(
        "https://example.com",
        setup_paths["save_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["save_path"]
    mock_logger.info.assert_any_call("Downloading the Enron dataset...")
    mock_logger.info.assert_any_call(
        "Dataset Downloaded Successfully at %s", setup_paths["save_path"]
    )
    mock_tqdm.return_value.update.assert_not_called()


def test_permission_denied(mocker: MockerFixture, setup_paths):
    """Test if function handles permission denied errors."""
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch(
        "download_dataset.os.makedirs", side_effect=PermissionError("Permission denied")
    )
    mock_logger = mocker.MagicMock()
    mocker.patch("download_dataset.create_logger", return_value=mock_logger)

    result = download_enron_dataset(
        "https://example.com",
        setup_paths["save_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Error downloading dataset: Permission denied", exc_info=True
    )


def test_invalid_url(mocker: MockerFixture, setup_paths):
    """Test if function handles invalid URL errors."""
    mocker.patch("os.path.exists", return_value=False)
    mock_logger = mocker.MagicMock()
    mocker.patch("download_dataset.create_logger", return_value=mock_logger)
    mocker.patch(
        "requests.get",
        side_effect=requests.exceptions.MissingSchema("Invalid URL 'invalid-url'"),
    )

    result = download_enron_dataset(
        "invalid-url",
        setup_paths["save_path"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Error downloading dataset: Invalid URL 'invalid-url'", exc_info=True
    )


if __name__ == "__main__":
    pytest.main()
