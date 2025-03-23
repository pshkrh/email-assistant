"""
Module for cleaning and processing email date fields.

This script reads a CSV file containing email data, processes the 'Date' column by:
- Removing timezone abbreviations
- Standardizing date formats
- Converting to datetime format
- Extracting day, time, and date components

The cleaned data is saved back to the same CSV file.

Usage:
    This module is typically used within a data pipeline to preprocess email datasets.

Functions:
    clean_and_parse_dates(csv_path, path, logger_name):
        Cleans and processes the 'Date' column in a DataFrame.

"""

import re
import pandas as pd

from create_logger import create_logger
from get_project_root import project_root


def clean_and_parse_dates(csv_path, log_path, logger_name):
    """
    Cleans and processes the 'Date' column in the DataFrame by:
    - Removing timezone abbreviations
    - Standardizing date formats
    - Converting to datetime format
    - Extracting day, time, and date components

    Parameters:
        csv_path (str): Path to csv.
        log_path (str): Path for logging.
        logger_name (str): Name of the logger.

    Returns:
        CSV PATH: CSV PATH to cleaned and parsed csv with date-related columns.
    """

    data_preprocessing_logger = create_logger(log_path, logger_name)
    try:

        df = pd.read_csv(csv_path)

        # Remove timezone abbreviation from 'Date' column
        df["Original_Timezone"] = df["Date"].str.extract(
            r"(\s\([A-Za-z]{3,4}\))$", expand=False
        )

        data_preprocessing_logger.info("Created Original_Timezone in Dataframe")

        df["Date"] = df["Date"].str.replace(r"\s\([A-Za-z]{3,4}\)$", "", regex=True)

        # Function to expand 2-digit years to 4-digit format
        def expand_two_digit_years(match_obj):
            """Expands 2-digit years in date strings."""
            prefix = "20" if int(match_obj.group(2)) < 50 else "19"
            return (
                f"{match_obj.group(1)}{prefix}{match_obj.group(2)}{match_obj.group(3)}"
            )

        # Function to clean and standardize date strings
        def clean_date_string(date_str):
            if pd.isna(date_str):
                return date_str

            # Add leading zero to single-digit day if missing
            date_str = re.sub(r"(\w{3},\s)(\d{1})(\s)", r"\g<1>0\2\3", date_str)

            # Expand 2-digit years
            date_str = re.sub(
                r"(\s)(\d{1,2})(\s\d{2}:\d{2}:\d{2})", expand_two_digit_years, date_str
            )

            return date_str

        df["Cleaned_Date"] = df["Date"].apply(clean_date_string)

        data_preprocessing_logger.info("Cleaned Date in Dataframe")

        df["Parsed_Date"] = pd.to_datetime(
            df["Cleaned_Date"], errors="coerce", utc=True
        )

        data_preprocessing_logger.info("Converted to datetime format in Dataframe")

        df["Day"] = df["Parsed_Date"].dt.day_name()
        data_preprocessing_logger.info("Created Day in Dataframe")

        df["Time"] = df["Parsed_Date"].dt.time
        data_preprocessing_logger.info("Created Time in Dataframe")

        df["Date"] = df["Parsed_Date"].dt.date
        data_preprocessing_logger.info("Created Date in Dataframe")

        df.drop(columns=["Parsed_Date", "Cleaned_Date"], inplace=True)
        data_preprocessing_logger.info("Droped Temporary Columns from Dataframe")

        df.to_csv(csv_path, index=False)

        data_preprocessing_logger.info(
            "DataFrame saved to enron_emails.csv successfully."
        )

        return csv_path
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Error in cleaning and parsing dates: {e}"
        data_preprocessing_logger.error(error_message, exc_info=True)
        return None


if __name__ == "__main__":

    PROJECT_ROOT_DIR = project_root()

    CSV_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/data/enron_emails.csv"

    LOG_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_preprocessing_log.log"
    LOGGER_NAME = "data_preprocessing_logger"

    CSV_PATH = clean_and_parse_dates(LOG_PATH, LOGGER_NAME, CSV_PATH)
