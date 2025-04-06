"""
Module for data validation using Great Expectations.

This script validates email datasets against predefined data expectations,
ensuring data quality, consistency, and schema integrity.

Functions:
    validate_data(csv_path, suite, context_root_dir, log_path, logger_name)
"""

# Disabled duplicate-code as it is giving silly error like,
#  error_message = f"CSV file not found: {csv_path}"
#  data_quality_logger.error(error_message)
#  the above two lines are same
# pylint: disable=duplicate-code
import os
import pandas as pd
import great_expectations as gx

from create_logger import create_logger


def _setup_gx_validation(context, df, suite, logger):
    """Helper function to set up GX data source, asset, and validation."""
    logger.info("Setting up Validation Definition to run...")

    # Setup GX data source, asset, and batch definition
    try:
        data_source = context.data_sources.get(name="enron_data_source")
    except gx.exceptions.DataContextError:
        data_source = context.data_sources.add_pandas(name="enron_data_source")

    try:
        data_asset = data_source.get_asset(name="enron_email_data")
    except gx.exceptions.DataContextError:
        data_asset = data_source.add_dataframe_asset(name="enron_email_data")

    try:
        batch_definition = data_asset.get_batch_definition("enron_batch_definition")
    except gx.exceptions.DataContextError:
        batch_definition = data_asset.add_batch_definition_whole_dataframe(
            "enron_batch_definition"
        )

    batch_definition.get_batch(batch_parameters={"dataframe": df})

    validation_definition = gx.ValidationDefinition(
        data=batch_definition, suite=suite, name="enron_validation_definition"
    )

    validation_definition = context.validation_definitions.add_or_update(
        validation_definition
    )

    return validation_definition


def validate_data(csv_path, suite, context_root_dir, log_path, logger_name):
    """
    Performs data validation using Great Expectations.

    Parameters:
        csv_path (str): Path to the input CSV file.
        suite (gx.ExpectationSuite): Great Expectations validation suite.
        context_root_dir (str): Root directory of the Great Expectations context.
        log_path (str): Path for logging.
        logger_name (str): Name of the logger.

    Returns:
        dict: Validation results containing validation outcomes.

    Raises:
        ValueError: If input parameters are invalid.
        FileNotFoundError: If the CSV file doesn't exist.
        pd.errors.EmptyDataError: If the CSV file is empty or contains no data.
        gx.exceptions.DataContextError: If GX context or data setup fails.
        gx.exceptions.ValidationError: If validation run fails.
        Exception: For unexpected errors.
    """
    if not all([csv_path, suite, context_root_dir, log_path, logger_name]):
        error_message = "One or more input parameters are empty"
        raise ValueError(error_message)

    data_quality_logger = create_logger(log_path, logger_name)

    if not os.path.exists(csv_path):
        error_message = f"CSV file not found: {csv_path}"
        data_quality_logger.error(error_message)
        raise FileNotFoundError(error_message)

    if os.path.getsize(csv_path) == 0:
        error_message = f"CSV file is empty: {csv_path}"
        data_quality_logger.error(error_message)
        raise pd.errors.EmptyDataError(error_message)

    try:
        context = gx.get_context(context_root_dir=context_root_dir)
        df = pd.read_csv(csv_path)
        if df.empty:
            error_message = f"CSV file contains no data: {csv_path}"
            data_quality_logger.error(error_message)
            raise pd.errors.EmptyDataError(error_message)

        validation_definition = _setup_gx_validation(
            context, df, suite, data_quality_logger
        )

        validation_result = validation_definition.run(
            batch_parameters={"dataframe": df}
        )

        data_quality_logger.info("Validations ran successfully")
        return validation_result

    except FileNotFoundError:
        raise  # Re-raise without additional logging
    except pd.errors.EmptyDataError:
        raise  # Re-raise without additional logging
    except gx.exceptions.DataContextError as e:
        error_message = f"Error in Great Expectations data setup: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        raise
    except gx.exceptions.ValidationError as e:
        error_message = f"Validation run failed: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        raise
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Unexpected error in validation: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        raise


if __name__ == "__main__":
    # Example usage (not typically run standalone)
    from get_project_root import project_root
    from data_quality_expectations import define_expectations

    PROJECT_ROOT_DIR = project_root()
    CSV_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/data/enron_emails.csv"
    CONTEXT_ROOT_DIR = f"{PROJECT_ROOT_DIR}/data_pipeline/gx"
    LOG_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_quality_log.log"
    LOGGER_NAME = "data_quality_logger"

    try:
        SUITE = define_expectations(CSV_PATH, CONTEXT_ROOT_DIR, LOG_PATH, LOGGER_NAME)
        RESULT = validate_data(CSV_PATH, SUITE, CONTEXT_ROOT_DIR, LOG_PATH, LOGGER_NAME)
        print("Validation completed successfully:", RESULT.success)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error: {e}")
