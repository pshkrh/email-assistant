"""
Module for data validation using Great Expectations.

This script validates email datasets against predefined data expectations,
ensuring data quality, consistency, and schema integrity.

Functions:
    validate_data(csv_path, suite, context_root_dir, path, logger_name)
"""

import pandas as pd
import great_expectations as gx

from create_logger import create_logger


def validate_data(csv_path, suite, context_root_dir, path, logger_name):
    """
    Performs data validation using Great Expectations.

    Parameters:
        csv_path (str): Path to the input CSV file.
        suite (str): Name of the Great Expectations validation suite.
        context_root_dir (str): Root directory of the Great Expectations context.
        path (str): Path for logging.
        logger_name (str): Name of the logger.

    Returns:
        validation_result (dict): Validation results containing validation outcomes.
    """
    context = gx.get_context(context_root_dir=context_root_dir)
    data_quality_logger = create_logger(path, logger_name)
    try:
        df = pd.read_csv(csv_path)
        data_quality_logger.info("Setting up Validation Definition to run...")
        try:
            data_source = context.data_sources.get(name="enron_data_source")
        except Exception:  # pylint: disable=broad-exception-caught
            data_source = context.data_sources.add_pandas(name="enron_data_source")
        try:
            data_asset = data_source.get_asset(name="enron_email_data")
        except Exception:  # pylint: disable=broad-exception-caught
            data_asset = data_source.add_dataframe_asset(name="enron_email_data")
        try:
            batch_definition = data_asset.get_batch_definition("enron_batch_definition")
        except Exception:  # pylint: disable=broad-exception-caught
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

        validation_result = validation_definition.run(
            batch_parameters={"dataframe": df}
        )

        data_quality_logger.info("Validations ran successfully")

        return validation_result
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Error in Validation: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        return None
