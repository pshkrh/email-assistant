"""
Test module for extract_dataset.py
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
    """Fixture to set up temporary paths for testing."""
    return {
        "archive_path": str(tmp_path / "emails.tar.gz"),
        "extract_to": str(tmp_path / "extracted_dataset"),
        "log_path": str(tmp_path / "logs" / "test_data_extraction_log.log"),
        "logger_name": "test_data_extraction_logger",
    }


# pylint: disable=redefined-outer-name
def test_extract_success(mocker: MockerFixture, setup_paths):
    """Test successful extraction of the dataset."""
    # Archive exists, extraction directory doesn't yet exist
    mocker.patch(
        "os.path.exists", side_effect=[True, False]
    )  # Archive: True, extract_to: False
    mocker.patch("os.listdir", return_value=[])  # extract_to is empty
    mock_makedirs = mocker.patch("extract_dataset.os.makedirs")
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)
    mock_member1 = mocker.MagicMock(name="member1")
    mock_member2 = mocker.MagicMock(name="member2")
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
        "Extraction complete! Files are saved in %s", setup_paths["extract_to"]
    )
    assert mock_tar.extract.call_count == 2
    assert mock_progress_bar.update.call_count == 2


def test_already_extracted(mocker: MockerFixture, setup_paths):
    """Test skipping extraction when dataset is already extracted."""
    mocker.patch(
        "os.path.exists", side_effect=[True, True]
    )  # Both archive and extract_to exist
    mocker.patch("os.listdir", return_value=["file1", "file2"])  # extract_to has files
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)

    result = extract_enron_dataset(
        setup_paths["archive_path"],
        setup_paths["extract_to"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == setup_paths["extract_to"]
    mock_logger.info.assert_called_once_with(
        "Dataset already extracted, skipping extraction."
    )


def test_invalid_input(mocker: MockerFixture):
    """Test raising ValueError for invalid input."""
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)

    with pytest.raises(ValueError) as exc_info:
        extract_enron_dataset("", "some/path", "log.log", "logger")
    assert str(exc_info.value) == "One or more input parameters are empty"


def test_tarfile_not_found(mocker: MockerFixture, setup_paths):
    """Test raising FileNotFoundError when archive is missing."""
    mocker.patch("os.path.exists", return_value=False)  # Archive doesn't exist
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)

    with pytest.raises(FileNotFoundError) as exc_info:
        extract_enron_dataset(
            setup_paths["archive_path"],
            setup_paths["extract_to"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert (
        str(exc_info.value) == f"Archive file not found: {setup_paths['archive_path']}"
    )


def test_permission_denied(mocker: MockerFixture, setup_paths):
    """Test raising PermissionError during directory creation."""
    mocker.patch(
        "os.path.exists", side_effect=[True, False]
    )  # Archive exists, extract_to doesn't
    mocker.patch("os.listdir", return_value=[])  # extract_to is empty
    mocker.patch(
        "extract_dataset.os.makedirs", side_effect=PermissionError("Permission denied")
    )
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)

    with pytest.raises(PermissionError) as exc_info:
        extract_enron_dataset(
            setup_paths["archive_path"],
            setup_paths["extract_to"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == "Permission denied"


def test_empty_tarfile(mocker: MockerFixture, setup_paths):
    """Test extraction with an empty tarfile."""
    mocker.patch(
        "os.path.exists", side_effect=[True, False]
    )  # Archive exists, extract_to doesn't
    mocker.patch("os.listdir", return_value=[])  # extract_to is empty
    mocker.patch("extract_dataset.os.makedirs")
    mock_logger = mocker.MagicMock()
    mocker.patch("extract_dataset.create_logger", return_value=mock_logger)
    mock_tar = mocker.MagicMock()
    mock_tar.getmembers.return_value = []  # Empty tarfile
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
    mock_logger.info.assert_any_call("Extracting the dataset...")
    mock_logger.info.assert_any_call(
        "Extraction complete! Files are saved in %s", setup_paths["extract_to"]
    )
    mock_progress_bar.update.assert_not_called()


if __name__ == "__main__":
    pytest.main()
