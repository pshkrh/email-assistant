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

    Returns:
        str: Path where dataset was extracted

    Raises:
        ValueError: If input parameters are invalid
        FileNotFoundError: If the archive file doesn't exist
        tarfile.TarError: If there's an error with the tar file
        OSError: If directory creation or file extraction fails
        Exception: For unexpected errors
    """
    data_extracting_logger = create_logger(log_path, logger_name)

    # Validate inputs
    if not all([archive_path, extract_to, log_path, logger_name]):
        error_msg = "One or more input parameters are empty"
        data_extracting_logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Check if archive exists
        if not os.path.exists(archive_path):
            error_msg = f"Archive file not found: {archive_path}"
            data_extracting_logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Check if dataset already extracted
        if os.path.exists(extract_to) and len(os.listdir(extract_to)) > 0:
            data_extracting_logger.info(
                "Dataset already extracted, skipping extraction."
            )
            return extract_to  # Return path since it exists

        # Create extraction directory
        try:
            os.makedirs(extract_to, exist_ok=True)
        except OSError as e:
            data_extracting_logger.error("Failed to create extraction directory: %s", e)
            raise

        data_extracting_logger.info("Extracting the dataset...")

        # Extract the tar.gz file
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getmembers()
                with tqdm(total=len(members), desc="Extracting") as progress_bar:
                    for member in members:
                        try:
                            tar.extract(member, path=extract_to)
                            progress_bar.update(1)
                        except (OSError, tarfile.TarError) as e:
                            data_extracting_logger.error(
                                "Error extracting member %s: %s", member.name, e
                            )
                            raise
        except tarfile.TarError as e:
            data_extracting_logger.error("Error with tar file: %s", e)
            raise

        data_extracting_logger.info(
            "Extraction complete! Files are saved in %s", extract_to
        )
        return extract_to

    except Exception as e:
        data_extracting_logger.error(
            "Unexpected error extracting dataset: %s", e, exc_info=True
        )
        raise  # Re-raise the original exception


if __name__ == "__main__":
    PROJECT_ROOT_DIR = project_root()
    EXTRACT_TO = f"{PROJECT_ROOT_DIR}/data_pipeline/data/dataset"
    ARCHIVE_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/data/enron_mail_20150507.tar.gz"
    LOG_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_extraction_log.log"
    LOGGER_NAME = "data_extraction_logger"

    try:
        RESULT = extract_enron_dataset(ARCHIVE_PATH, EXTRACT_TO, LOG_PATH, LOGGER_NAME)
        print(f"Dataset extracted successfully to: {RESULT}")
    except ValueError as e:
        print(f"Input error: {e}")
    except FileNotFoundError as e:
        print(f"File error: {e}")
    except tarfile.TarError as e:
        print(f"Tar file error: {e}")
    except OSError as e:
        print(f"System error: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Unexpected error: {e}")
