"""
Module for defining data validation expectations using Great Expectations.

This module sets up expectations for email datasets, ensuring data integrity
and consistency in key columns like Message-ID, Date, From, To, and Body.

Functions:
    define_expectations(csv_path, context_root_dir, log_path, logger_name)
"""

import os
import great_expectations as gx
import pandas as pd

from create_logger import create_logger


def define_expectations(csv_path, context_root_dir, log_path, logger_name):
    """
    Defines data validation expectations for the dataset.

    Parameters:
        csv_path (str): Path to the dataset.
        context_root_dir (str): Root directory for Great Expectations context.
        log_path (str): Path for logging.
        logger_name (str): Name of the logger.

    Returns:
        gx.ExpectationSuite: Configured expectation suite.

    Raises:
        ValueError: If input parameters are invalid.
        FileNotFoundError: If the CSV file doesn't exist.
        pd.errors.EmptyDataError: If the CSV file is empty or contains no data.
        gx.exceptions.ExpectationSuiteError: If suite creation fails.
        Exception: For unexpected errors.
    """
    if not all([csv_path, context_root_dir, log_path, logger_name]):
        raise ValueError("One or more input parameters are empty")

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
        data_quality_logger.info("Setting up Expectations in Suite")

        df = pd.read_csv(csv_path)
        if df.empty:
            error_message = f"CSV file contains no data: {csv_path}"
            data_quality_logger.error(error_message)
            raise pd.errors.EmptyDataError(error_message)

        suite = gx.ExpectationSuite(name="enron_expectation_suite")
        suite = context.suites.add_or_update(suite)

        # Define schema expectations
        not_null_columns = ["Message-ID", "From", "Body"]
        for column in not_null_columns:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
            )

        email_regex = {
            "From": (r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
            "To": (
                r"^(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
                r"(?:,\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})*$"
            ),
            "Cc": (
                r"^(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
                r"(?:,\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})*$"
            ),
            "Bcc": (
                r"^(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
                r"(?:,\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})*$"
            ),
        }
        for column, regex in email_regex.items():
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToMatchRegex(
                    column=column, regex=regex, mostly=0.95
                )
            )

        # Allow 5% null as body text is more important
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="Date", mostly=0.95)
        )

        # Allow 10% null as body text and from is important
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="X-From", mostly=0.90)
        )

        # Uniqueness check
        suite.add_expectation(
            gx.expectations.ExpectColumnUniqueValueCountToBeBetween(
                column="Message-ID", min_value=len(df), max_value=len(df)
            )
        )

        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeInSet(
                column="Date",
                value_set=(
                    pd.date_range("1980-01-01", pd.Timestamp.now(), freq="D")
                    .strftime("%Y-%m-%d")
                    .tolist()
                ),
            )
        )

        # Thread Integrity (Summary Task)
        # Expect Subject to be non-null for thread context
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="Subject", mostly=0.95)
        )

        # Action Item Potential
        # Expect Body to contain actionable phrases/words for some emails
        action_phrases = (
            r"(?i)\bmeeting\b|\bplease\b|\bneed\b|\baction\b|\bdo\b|\bsend\b|"
            r"\breview\b|\burgent\b|\basap\b|\brespond\b|\bconfirm\b|\bfollow-up\b|"
            r"\bcomplete\b|\bcheck\b"
        )

        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToMatchRegex(
                column="Body",
                regex=action_phrases,
                mostly=0.50,
            )
        )

        # Reply Feasibility
        # Expect To to be present for drafting replies
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(
                column="To",
                mostly=0.95,
            )
        )

        data_quality_logger.info("Created Expectation Suite successfully")
        return suite

    except FileNotFoundError:
        raise  # Re-raise without additional logging
    except pd.errors.EmptyDataError:
        raise  # Re-raise without additional logging
    except gx.exceptions.ExpectationSuiteError as e:
        error_message = f"Error creating expectation suite: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        raise
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Unexpected error in defining expectations: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        raise


if __name__ == "__main__":
    # Example usage (not typically run standalone)
    from get_project_root import project_root

    PROJECT_ROOT_DIR = project_root()
    CSV_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/data/enron_emails.csv"
    CONTEXT_ROOT_DIR = f"{PROJECT_ROOT_DIR}/data_pipeline/gx"
    LOG_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_quality_log.log"
    LOGGER_NAME = "data_quality_logger"

    try:
        SUITE = define_expectations(CSV_PATH, CONTEXT_ROOT_DIR, LOG_PATH, LOGGER_NAME)
        print("Expectation suite defined successfully.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error: {e}")
