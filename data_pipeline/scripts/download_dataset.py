"""
Module for downloading the Enron dataset.

This script downloads the Enron dataset from a specified URL and saves it locally.
It ensures logging and handles errors gracefully.
"""

import os
import warnings
import requests
from tqdm import tqdm
from requests.exceptions import RequestException, Timeout, HTTPError

from create_logger import create_logger
from get_project_root import project_root

warnings.filterwarnings("ignore")

DATA_DIR = "dataset"


def download_enron_dataset(url, save_path, log_path, logger_name):
    """
    Downloads the Enron dataset from a given URL and saves it locally.

    Parameters:
        url (str): URL of the dataset.
        save_path (str): Path to save the downloaded file.
        log_path (str): Path for logging.
        logger_name (str): Name of the logger.

    Returns:
        str: Path where dataset was saved

    Raises:
        ValueError: If input parameters are invalid
        OSError: If directory creation fails
        Timeout: If download times out
        HTTPError: If an HTTP error occurs
        RequestException: If a network error occurs
        IOError: If file writing fails
        Exception: For unexpected errors
    """
    data_downloading_logger = create_logger(log_path, logger_name)

    # Validate inputs
    if not all([url, save_path, log_path, logger_name]):
        error_msg = "One or more input parameters are empty"
        data_downloading_logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        chunk_size = 1024 * 1024

        # Check if dataset already exists
        if os.path.exists(save_path):
            data_downloading_logger.info(
                "Dataset archive already exists, skipping download."
            )
            return save_path  # Return path instead of None since it exists

        # Create directory if it doesn't exist
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
        except OSError as e:
            data_downloading_logger.error("Failed to create directory: %s", e)
            raise

        data_downloading_logger.info("Downloading the Enron dataset...")

        # Stream download with specific exception handling
        try:
            with requests.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))

                with open(save_path, "wb") as file, tqdm(
                    total=total_size, unit="B", unit_scale=True, desc="Downloading"
                ) as progress_bar:
                    try:
                        for chunk in response.iter_content(chunk_size):
                            if chunk:  # filter out keep-alive chunks
                                file.write(chunk)
                                progress_bar.update(len(chunk))
                    except IOError as e:
                        data_downloading_logger.error("Error writing to file: %s", e)
                        raise

        except Timeout as e:
            data_downloading_logger.error("Download timed out after 30 seconds: %s", e)
            raise
        except HTTPError as e:
            data_downloading_logger.error("HTTP error occurred: %s", e)
            raise
        except RequestException as e:
            data_downloading_logger.error("Network error occurred: %s", e)
            raise

        data_downloading_logger.info("Dataset Downloaded Successfully at %s", save_path)
        return save_path

    except Exception as e:  # pylint: disable=broad-exception-caught
        data_downloading_logger.error(
            "Unexpected error downloading dataset: %s", e, exc_info=True
        )
        # Clean up partial download if it exists
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
                data_downloading_logger.info("Cleaned up partial download file")
            except OSError as cleanup_error:
                data_downloading_logger.error(
                    "Failed to clean up partial file: %s", cleanup_error
                )
        raise  # Re-raise the original exception


if __name__ == "__main__":
    DATASET_URL = "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz"
    PROJECT_ROOT_DIR = project_root()
    SAVE_PATH = os.path.join(
        PROJECT_ROOT_DIR, "data_pipeline", "data", "enron_mail_20150507.tar.gz"
    )
    LOG_PATH = os.path.join(
        PROJECT_ROOT_DIR, "data_pipeline", "logs", "data_downloading_log.log"
    )
    LOGGER_NAME = "data_downloading_logger"

    try:
        download_enron_dataset(DATASET_URL, SAVE_PATH, LOG_PATH, LOGGER_NAME)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Download failed: {e}")
