"""
Module for extracting the Enron dataset.

This script extracts the Enron dataset from a compressed `.tar.gz` archive 
and saves it to the specified directory while logging the process.
"""

import os
import tarfile
import warnings
from tqdm import tqdm

from create_logger import create_logger
from get_project_root import project_root

warnings.filterwarnings("ignore")


def extract_enron_dataset(archive_path, extract_to, log_path, logger_name):
    """
    Extracts the Enron dataset from a compressed archive.

    Parameters:
        archive_path (str): Path to the compressed dataset file.
        extract_to (str): Directory where the extracted files will be stored.
        log_path (str): Path for logging.
        logger_name (str): Name of the logger.
    """
    data_extracting_logger = create_logger(log_path, logger_name)
    try:
        if os.path.exists(extract_to) and len(os.listdir(extract_to)) > 0:
            data_extracting_logger.info(
                "Dataset already extracted, skipping extraction."
            )
            return None

        os.makedirs(extract_to, exist_ok=True)
        data_extracting_logger.info("Extracting the dataset...")

        # Extract the tar.gz file
        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getmembers()
            with tqdm(total=len(members), desc="Extracting") as progress_bar:
                for member in members:
                    tar.extract(member, path=extract_to)
                    progress_bar.update(1)

        data_extracting_logger.info(
            "Extraction complete! Files are saved in %s ", extract_to
        )
        return extract_to
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Error extracting dataset: {e}"
        data_extracting_logger.error(error_message, exc_info=True)
        return None


if __name__ == "__main__":
    PROJECT_ROOT_DIR = project_root()
    EXTRACT_TO = "{PROJECT_ROOT_DIR}/data_pipeline/data/dataset"
    ARCHIVE_PATH = "{PROJECT_ROOT_DIR}/data_pipeline/data/enron_mail_20150507.tar.gz"
    LOG_PATH = "{PROJECT_ROOT_DIR}/data_pipeline/logs/data_extraction_log.log"
    LOGGER_NAME = "data_extraction_logger"

    extract_enron_dataset(ARCHIVE_PATH, EXTRACT_TO, LOG_PATH, LOGGER_NAME)
