"""
Module for setting up Great Expectations context and logging.

This script initializes the Great Expectations environment, defines validation
expectations, validates data, and handles anomalies detected in the dataset.

Functions:
    setup_gx_context_and_logger(context_root_dir, log_path, logger_name)
"""

import os
import great_expectations as gx

from data_quality_expectations import define_expectations
from data_quality_validation import validate_data
from data_quality_anomaly import handle_anomalies

from create_logger import create_logger
from get_project_root import project_root


def setup_gx_context_and_logger(context_root_dir, log_path, logger_name):
    """
    Sets up Great Expectations validation environment and logging.

    Parameters:
        context_root_dir (str): Root directory for Great Expectations.
        log_path (str): Path for logging.
        logger_name (str): Logger name.

    Returns:
        str: Path to the initialized context.

    Raises:
        ValueError: If input parameters are invalid.
        OSError: If directory creation fails.
        gx.exceptions.DataContextError: If Great Expectations context initialization fails.
        Exception: For unexpected errors.
    """
    if not all([context_root_dir, log_path, logger_name]):
        error_message = "One or more input parameters are empty"
        raise ValueError(error_message)

    data_quality_logger = create_logger(log_path, logger_name)

    try:
        os.makedirs(context_root_dir, exist_ok=True)
    except OSError as e:
        error_message = f"Failed to create directory {context_root_dir}: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        raise

    try:
        gx.get_context(context_root_dir=context_root_dir)
        data_quality_logger.info("Successfully created gx-context and logger")
        return context_root_dir
    except gx.exceptions.DataContextError as e:
        error_message = f"Error initializing Great Expectations context: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        raise
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Unexpected error in setting up gx context: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        raise


if __name__ == "__main__":
    PROJECT_ROOT_DIR = project_root()
    CONTEXT_ROOT_DIR = f"{PROJECT_ROOT_DIR}/data_pipeline/gx"
    DATA_QUALITY_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_quality_log.log"
    DATA_QUALITY_LOGGER_NAME = "data_quality_logger"
    ANOMALY_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_anomaly_log.log"
    ANOMALY_LOGGER_NAME = "data_anomaly_logger"
    CSV_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/data/enron_emails.csv"

    try:
        GX_CONTEXT_ROOT_DIR = setup_gx_context_and_logger(
            CONTEXT_ROOT_DIR, DATA_QUALITY_PATH, DATA_QUALITY_LOGGER_NAME
        )
        suite = define_expectations(
            CSV_PATH, GX_CONTEXT_ROOT_DIR, DATA_QUALITY_PATH, DATA_QUALITY_LOGGER_NAME
        )
        validation_results = validate_data(
            CSV_PATH,
            suite,
            GX_CONTEXT_ROOT_DIR,
            DATA_QUALITY_PATH,
            DATA_QUALITY_LOGGER_NAME,
        )
        handle_anomalies(validation_results, ANOMALY_PATH, ANOMALY_LOGGER_NAME)
        print("Data quality setup and validation completed successfully.")
    except ValueError as e:
        print(f"Input error: {e}")
    except OSError as e:
        print(f"System error: {e}")
    except gx.exceptions.DataContextError as e:
        print(f"Great Expectations error: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Unexpected error: {e}")
