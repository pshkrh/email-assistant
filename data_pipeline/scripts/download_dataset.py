"""
Module for downloading the Enron dataset.

This script downloads the Enron dataset from a specified URL and saves it locally.
It ensures logging and handles errors gracefully.
"""

import os
import warnings
import requests
from tqdm import tqdm

from create_logger import create_logger

warnings.filterwarnings("ignore")

DATA_DIR = "dataset"


def download_enron_dataset(url, save_path, path, logger_name):
    """
    Downloads the Enron dataset from a given URL and saves it locally.

    Parameters:
        url (str): URL of the dataset.
        save_path (str): Path to save the downloaded file.
        path (str): Path for logging.
        logger_name (str): Name of the logger.
    """
    data_downloading_logger = create_logger(path, logger_name)
    try:
        chunk_size = 1024 * 1024

        # Check if dataset already exists
        if os.path.exists(save_path):
            data_downloading_logger.info(
                "Dataset archive already exists, skipping download."
            )
            return None

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        data_downloading_logger.info("Downloading the Enron dataset...")

        # Stream download
        with requests.get(url, stream=True, timeout=30) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            with open(save_path, "wb") as file, tqdm(
                total=total_size, unit="B", unit_scale=True, desc="Downloading"
            ) as progress_bar:
                for chunk in response.iter_content(chunk_size):
                    file.write(chunk)
                    progress_bar.update(len(chunk))
        data_downloading_logger.info("Dataset Downloaded Successfully at %s", save_path)
        return save_path
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Error downloading dataset: {e}"
        data_downloading_logger.error(error_message, exc_info=True)
        return None


if __name__ == "__main__":
    DATASET_URL = "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz"
    SAVE_PATH = "./data_pipeline/data/enron_mail_20150507.tar.gz"
    PATH = "./data_pipeline/logs/data_downloading_log.log"
    LOGGER_NAME = "data_downloading_logger"

    download_enron_dataset(DATASET_URL, SAVE_PATH, PATH, LOGGER_NAME)
