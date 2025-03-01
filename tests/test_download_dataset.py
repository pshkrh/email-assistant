import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tarfile
import urllib.request
import shutil
import stat

# Automatically detect and add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# Import functions from download_dataset.py
from data_pipeline.scripts.download_dataset import (
    download_enron_dataset,
    extract_enron_dataset,
    DATASET_URL,
    ARCHIVE_NAME,
    DATA_DIR
)


class TestDownloadDataset(unittest.TestCase):

    ### === TEST CASES FOR DOWNLOAD FUNCTION ===

    @patch("urllib.request.urlretrieve")
    def test_download_when_file_does_not_exist(self, mock_urlretrieve):
        """Test downloading when the dataset does not exist."""
        test_archive = "test_enron.tar.gz"
        if os.path.exists(test_archive):
            os.remove(test_archive)

        download_enron_dataset(DATASET_URL, test_archive)

        # Verify that urlretrieve was called
        mock_urlretrieve.assert_called_once_with(DATASET_URL, test_archive)
        self.assertTrue(mock_urlretrieve.called)

    @patch("urllib.request.urlretrieve")
    def test_skip_download_if_file_already_exists(self, mock_urlretrieve):
        """Test skipping download when dataset already exists."""
        test_archive = "test_enron.tar.gz"

        # Create a dummy file to simulate an existing dataset archive.
        with open(test_archive, "w") as f:
            f.write("Dummy Data")

        download_enron_dataset(DATASET_URL, test_archive)

        # Verify that no download was attempted.
        mock_urlretrieve.assert_not_called()
        os.remove(test_archive)  # Cleanup

    @patch("urllib.request.urlretrieve", side_effect=Exception("Download Failed"))
    def test_download_failure_handling(self, mock_urlretrieve):
        """Test handling of download failure due to network issues."""
        test_archive = "test_enron.tar.gz"

        with self.assertRaises(Exception) as context:
            download_enron_dataset(DATASET_URL, test_archive)

        self.assertEqual(str(context.exception), "Download Failed")

    @patch("urllib.request.urlretrieve", side_effect=ValueError("Invalid URL"))
    def test_download_invalid_url(self, mock_urlretrieve):
        """Test handling of invalid URL error."""
        invalid_url = "https://invalid-url.com/dataset.tar.gz"
        test_archive = "test_enron.tar.gz"

        with self.assertRaises(ValueError) as context:
            download_enron_dataset(invalid_url, test_archive)

        self.assertEqual(str(context.exception), "Invalid URL")

    @patch("urllib.request.urlretrieve", side_effect=TimeoutError("Connection Timed Out"))
    def test_download_timeout_error(self, mock_urlretrieve):
        """Test handling of download timeout error."""
        test_archive = "test_enron.tar.gz"

        with self.assertRaises(TimeoutError):
            download_enron_dataset(DATASET_URL, test_archive)

    @patch("urllib.request.urlretrieve")
    def test_successful_download(self, mock_urlretrieve):
        """Test when file is successfully downloaded (simulation)."""
        test_archive = "test_enron.tar.gz"

        if os.path.exists(test_archive):
            os.remove(test_archive)

        download_enron_dataset(DATASET_URL, test_archive)

        mock_urlretrieve.assert_called_once_with(DATASET_URL, test_archive)
        self.assertTrue(mock_urlretrieve.called)

    ### === TEST CASES FOR EXTRACTION FUNCTION ===

    def test_extract_tarfile_successfully(self):
        """Test extracting a valid tar.gz file."""
        test_tarfile = "test_archive.tar.gz"
        test_extract_path = "./tests/tmp_test_dataset"

        # Create a fake tar.gz file with a dummy file.
        with tarfile.open(test_tarfile, "w:gz") as tar:
            test_file = "dummy.txt"
            with open(test_file, "w") as f:
                f.write("This is a test file.")
            tar.add(test_file)
        os.remove(test_file)  # Remove original file

        extract_enron_dataset(test_tarfile, test_extract_path)
        self.assertTrue(os.path.exists(os.path.join(test_extract_path, "dummy.txt")))

        # Cleanup
        os.remove(test_tarfile)
        shutil.rmtree(test_extract_path, ignore_errors=True)

    def test_extract_tarfile_when_file_missing(self):
        """Test extraction when the tar.gz file is missing."""
        missing_tarfile = "missing_file.tar.gz"
        extract_path = "./tests/tmp_test_dataset"

        with self.assertRaises(FileNotFoundError):
            extract_enron_dataset(missing_tarfile, extract_path)

    def test_extract_tarfile_when_directory_already_exists(self):
        """Test extracting dataset when the target directory already exists."""
        test_tarfile = "test_archive.tar.gz"
        test_extract_path = "./tests/tmp_test_dataset"

        os.makedirs(test_extract_path, exist_ok=True)

        with tarfile.open(test_tarfile, "w:gz") as tar:
            test_file = "dummy.txt"
            with open(test_file, "w") as f:
                f.write("Test file content")
            tar.add(test_file)
        os.remove(test_file)

        extract_enron_dataset(test_tarfile, test_extract_path)
        self.assertTrue(os.path.exists(os.path.join(test_extract_path, "dummy.txt")))

        # Cleanup
        os.remove(test_tarfile)
        shutil.rmtree(test_extract_path, ignore_errors=True)

    def test_extract_corrupt_tarfile(self):
        """Test handling of a corrupt tar.gz file during extraction."""
        corrupt_tarfile = "corrupt.tar.gz"
        extract_path = "./tests/tmp_test_dataset"

        # Create a file that is not a valid tar.gz archive.
        with open(corrupt_tarfile, "w") as f:
            f.write("This is not a valid tar file")

        with self.assertRaises(tarfile.ReadError):
            extract_enron_dataset(corrupt_tarfile, extract_path)

        os.remove(corrupt_tarfile)

    def test_extraction_permission_error(self):
        """Test extracting tar.gz file into a directory where files cannot be written."""
        test_tarfile = "test_archive.tar.gz"
        test_extract_path = "./tests/read_only_dataset"

        # Create a fake tar.gz file with a dummy file.
        with tarfile.open(test_tarfile, "w:gz") as tar:
            test_file = "dummy.txt"
            with open(test_file, "w") as f:
                f.write("This is a test file.")
            tar.add(test_file)
        os.remove(test_file)  # Remove original file after adding to archive

        # Create the target directory
        os.makedirs(test_extract_path, exist_ok=True)

        # Lock a file inside the directory
        locked_file = os.path.join(test_extract_path, "locked_file.txt")
        lock = open(locked_file, "wb")  # Keep file open to lock it

        try:
            # Expect a PermissionError when extracting into a directory with a locked file
            with self.assertRaises(PermissionError):
                extract_enron_dataset(test_tarfile, test_extract_path)
        finally:
            lock.close()
            os.remove(locked_file)
            shutil.rmtree(test_extract_path, ignore_errors=True)
            os.remove(test_tarfile)


if __name__ == "__main__":
    unittest.main()
