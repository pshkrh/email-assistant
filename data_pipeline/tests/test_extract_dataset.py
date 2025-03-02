"""
Unit tests for the extract_enron_dataset function.
"""

import os
import sys
import pytest
from pytest_mock import MockerFixture

# Add scripts folder to sys.path
scripts_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.append(scripts_folder)

# pylint: disable=wrong-import-position

from extract_dataset import extract_enron_dataset

# pylint: enable=wrong-import-position


@pytest.fixture
def setup_paths(tmp_path):
    """Fixture to create temporary paths for testing."""
    return {
        "archive_path": str(tmp_path / "emails.tar.gz"),
        "extract_to": str(tmp_path / "extracted_dataset"),
        "log_path": str(tmp_path / "logs" / "test_data_extraction_log.log"),
        "logger_name": "test_data_extraction_logger",
    }


# pylint: disable=redefined-outer-name
def test_extract_success(mocker: MockerFixture, setup_paths):
    """Test successful extraction of the dataset."""
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.listdir", return_value=[])
    mock_makedirs = mocker.patch("extract_dataset.os.makedirs")
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)
    mock_member1 = mocker.MagicMock()
    mock_member2 = mocker.MagicMock()
    mock_tar = mocker.MagicMock()
    mock_tar.getmembers.return_value = [mock_member1, mock_member2]
    mock_tar.extract = mocker.MagicMock()
    mock_tar.__enter__.return_value = mock_tar
    mocker.patch("tarfile.open", return_value=mock_tar)

    mock_progress_bar = mocker.MagicMock()
    mocker.patch("extract_dataset.tqdm", return_value=mock_progress_bar)
    mock_progress_bar.__enter__.return_value = mock_progress_bar

    result = extract_enron_dataset(
        setup_paths["archive_path"],
        setup_paths["extract_to"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["extract_to"]
    mock_makedirs.assert_called_once_with(setup_paths["extract_to"], exist_ok=True)
    mock_logger.info.assert_any_call("Extracting the dataset...")
    mock_logger.info.assert_any_call(
        "Extraction complete! Files are saved in %s ", setup_paths["extract_to"]
    )
    assert mock_tar.extract.call_count == 2  # Two members extracted
    mock_tar.extract.assert_any_call(mock_member1, path=setup_paths["extract_to"])
    mock_tar.extract.assert_any_call(mock_member2, path=setup_paths["extract_to"])

    assert mock_progress_bar.update.call_count == 2
    mock_progress_bar.update.assert_any_call(1)


def test_extract_with_real_tar(mocker: MockerFixture, tmp_path):
    """Test extraction using the real emails.tar.gz file."""
    real_archive_path = os.path.join(os.path.dirname(__file__), "data", "emails.tar.gz")
    extract_to = str(tmp_path / "extracted_dataset")
    log_path = str(tmp_path / "logs" / "test_data_extraction_log.log")
    logger_name = "test_data_extraction_logger"

    assert os.path.exists(
        real_archive_path
    ), f"Real tar file not found at {real_archive_path}"

    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)

    result = extract_enron_dataset(real_archive_path, extract_to, log_path, logger_name)

    assert result == extract_to
    assert os.path.exists(extract_to)
    assert len(os.listdir(extract_to)) > 0
    mock_logger.info.assert_any_call("Extracting the dataset...")
    mock_logger.info.assert_any_call(
        "Extraction complete! Files are saved in %s ", extract_to
    )


def test_already_extracted(mocker: MockerFixture, setup_paths):
    """Test skipping extraction if directory exists and is non-empty."""
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.listdir", return_value=["file1", "file2"])
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)

    result = extract_enron_dataset(
        setup_paths["archive_path"],
        setup_paths["extract_to"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.info.assert_called_once_with(
        "Dataset already extracted, skipping extraction."
    )
    assert not mocker.patch("tarfile.open").called


def test_tarfile_not_found(mocker: MockerFixture, setup_paths):
    """Test handling of missing tarfile."""
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.listdir", return_value=[])
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)
    mocker.patch("tarfile.open", side_effect=FileNotFoundError("No such file"))

    result = extract_enron_dataset(
        setup_paths["archive_path"],
        setup_paths["extract_to"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Error extracting dataset: No such file", exc_info=True
    )


def test_permission_denied(mocker: MockerFixture, setup_paths):
    """Test handling of permission denied error during directory creation."""
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.listdir", return_value=[])
    mocker.patch(
        "extract_dataset.os.makedirs", side_effect=PermissionError("Permission denied")
    )
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)

    result = extract_enron_dataset(
        setup_paths["archive_path"],
        setup_paths["extract_to"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Error extracting dataset: Permission denied", exc_info=True
    )


def test_empty_tarfile(mocker: MockerFixture, setup_paths):
    """Test handling of an empty tarfile."""
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.listdir", return_value=[])
    mocker.patch("extract_dataset.os.makedirs")
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)
    mock_tar = mocker.MagicMock()
    mock_tar.getmembers.return_value = []
    mocker.patch("tarfile.open", return_value=mock_tar)
    mock_tqdm = mocker.patch("extract_dataset.tqdm", return_value=mocker.MagicMock())

    result = extract_enron_dataset(
        setup_paths["archive_path"],
        setup_paths["extract_to"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["extract_to"]
    mock_logger.info.assert_any_call("Extracting the dataset...")
    mock_logger.info.assert_any_call(
        "Extraction complete! Files are saved in %s ", setup_paths["extract_to"]
    )
    mock_tqdm.return_value.update.assert_not_called()
