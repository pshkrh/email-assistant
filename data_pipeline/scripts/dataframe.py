"""
Module for processing Enron email data.

This script extracts email metadata and body text from raw email files,
processes the data, and stores it in a structured CSV format.

Functions:
    extract_email_data(email_path, data_preprocessing_logger, header_keys)
    process_enron_emails(data_dir, path, logger_name, csv_path)
"""

import os
import sys
import email
import pandas as pd

from create_logger import create_logger
from get_project_root import project_root


# Extracts metadata and full email body from an email file.
def extract_email_data(email_path, data_preprocessing_logger, header_keys):
    """
    Extracts metadata and full email body from an email file.

    Parameters:
        email_path (str): Path to the email file.
        data_preprocessing_logger (Logger): Logger instance.
        header_keys (list): List of email header fields to extract.

    Returns:
        dict: Extracted email metadata and body.

    Raises:
        FileNotFoundError: If the email file doesn't exist.
        ValueError: If the file cannot be parsed as an email.
        Exception: For unexpected errors during processing.
    """
    if not os.path.exists(email_path):
        error_message = f"Email file not found: {email_path}"
        data_preprocessing_logger.error(error_message)
        raise FileNotFoundError(error_message)

    try:
        with open(email_path, "r", encoding="utf-8", errors="ignore") as f:
            msg = email.message_from_file(f)

        # Extract metadata
        email_data = {key: msg.get(key, None) for key in header_keys}

        # Extract the email body (handle multipart and plain text emails)
        body_parts = []
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":  # Extract plain text content
                    try:
                        body_parts.append(
                            part.get_payload(decode=True).decode(errors="ignore")
                        )
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass  # Skip problematic encodings
        else:
            try:
                body_parts.append(msg.get_payload(decode=True).decode(errors="ignore"))
            except Exception:  # pylint: disable=broad-exception-caught
                pass  # Skip problematic encodings

        # Join all body parts, keeping forwarded messages intact
        email_data["Body"] = "\n".join(body_parts).strip()
        return email_data
    except email.errors.MessageError as e:
        error_message = f"Error parsing email {email_path}: {e}"
        data_preprocessing_logger.error(error_message, exc_info=True)
        raise
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Unexpected error processing email {email_path}: {e}"
        data_preprocessing_logger.error(error_message, exc_info=True)
        raise


# Loop through all folders and extract emails into a DataFrame.
def process_enron_emails(data_dir, log_path, logger_name, csv_path):
    """
    Processes all email files in the dataset and extracts relevant information.

    Parameters:
        data_dir (str): Directory containing email files.
        log_path (str): Path for logging.
        logger_name (str): Name of the logger.
        csv_path (str): Path to save the processed emails as CSV.

    Returns:
        str: Path to the saved CSV file.

    Raises:
        ValueError: If input parameters are invalid.
        FileNotFoundError: If the data directory doesn't exist.
        OSError: If there's an error writing the CSV file.
        Exception: For unexpected errors during processing.
    """
    if not all([data_dir, log_path, logger_name, csv_path]):
        error_message = "One or more input parameters are empty"
        raise ValueError(error_message)

    data_preprocessing_logger = create_logger(log_path, logger_name)

    try:
        header_keys = [
            "Message-ID",
            "Date",
            "From",
            "To",
            "Subject",
            "Cc",
            "Bcc",
            "X-From",
            "X-To",
            "X-Cc",
        ]
        email_list = []
        total_files = 0

        if not os.path.exists(data_dir):
            # pylint: disable=logging-fstring-interpolation
            error_message = f"Directory {data_dir} does not exist!"
            data_preprocessing_logger.error(error_message)
            raise FileNotFoundError(error_message)
        # pylint: enable=logging-fstring-interpolation

        # pylint: disable=logging-fstring-interpolation
        data_preprocessing_logger.info(f"Processing emails in: {data_dir}")
        # pylint: enable=logging-fstring-interpolation

        for root, _, files in os.walk(data_dir):
            for file in files:
                total_files += 1
                email_data = extract_email_data(
                    os.path.join(root, file), data_preprocessing_logger, header_keys
                )
                email_list.append(email_data)
                if total_files % 10000 == 0:
                    sys.stdout.write(f"\rProcessed {total_files} emails so far")
                    sys.stdout.flush()

        # pylint: disable=logging-fstring-interpolation
        data_preprocessing_logger.info(f"Total emails processed: {total_files}")
        # pylint: enable=logging-fstring-interpolation

        # Convert to Pandas DataFrame
        df = pd.DataFrame(email_list)
        data_preprocessing_logger.info("DataFrame created successfully.")

        try:
            df.to_csv(csv_path, index=False)
        except OSError as e:
            error_message = f"Error saving DataFrame to {csv_path}: {e}"
            data_preprocessing_logger.error(error_message, exc_info=True)
            raise

        # pylint: disable=logging-fstring-interpolation
        data_preprocessing_logger.info(
            f"DataFrame saved to {csv_path} successfully in process_enron_emails."
        )
        # pylint: enable=logging-fstring-interpolation

        return csv_path
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Unexpected error in process_enron_emails function: {e}"
        data_preprocessing_logger.error(error_message, exc_info=True)
        raise


if __name__ == "__main__":
    PROJECT_ROOT_DIR = project_root()
    # Path to the extracted dataset
    MAILDIR_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/data/dataset/maildir"
    CSV_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/data/enron_emails.csv"
    LOG_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_preprocessing_log.log"
    LOGGER_NAME = "data_preprocessing_logger"

    try:
        RESULT = process_enron_emails(MAILDIR_PATH, LOG_PATH, LOGGER_NAME, CSV_PATH)
        print(f"Emails processed and saved to: {RESULT}")
    except ValueError as e:
        print(f"Input error: {e}")
    except FileNotFoundError as e:
        print(f"File error: {e}")
    except OSError as e:
        print(f"System error: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Unexpected error: {e}")
