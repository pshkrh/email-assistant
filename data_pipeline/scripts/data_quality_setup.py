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
    """
    data_quality_logger = create_logger(log_path, logger_name)
    try:
        os.makedirs(context_root_dir, exist_ok=True)
        gx.get_context(context_root_dir=context_root_dir)
        data_quality_logger.info("Successfully created gx-context and logger")
        return context_root_dir
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Error creating gx context: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        return None


if __name__ == "__main__":
    PROJECT_ROOT_DIR = project_root()
    CONTEXT_ROOT_DIR = f"{PROJECT_ROOT_DIR}/data_pipeline/gx"
    DATA_QUALITY_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_quality_log.log"
    DATA_QUALITY_LOGGER_NAME = "data_quality_logger"
    ANOMALY_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_anomaly_log.log"
    ANOMALY_LOGGER_NAME = "data_anomaly_logger"
    CSV_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/data/enron_emails.csv"
    gx_context_root_dir = setup_gx_context_and_logger(
        CONTEXT_ROOT_DIR, DATA_QUALITY_PATH, DATA_QUALITY_LOGGER_NAME
    )
    suite = define_expectations(
        CSV_PATH, gx_context_root_dir, DATA_QUALITY_PATH, DATA_QUALITY_LOGGER_NAME
    )
    validation_results = validate_data(
        CSV_PATH,
        suite,
        gx_context_root_dir,
        DATA_QUALITY_PATH,
        DATA_QUALITY_LOGGER_NAME,
    )
    handle_anomalies(validation_results, ANOMALY_PATH, ANOMALY_LOGGER_NAME)
