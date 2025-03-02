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
    """
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
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Error processing email {email_path}: {e}"
        data_preprocessing_logger.error(error_message, exc_info=True)
        return None


# Loop through all folders and extract emails into a DataFrame.
def process_enron_emails(data_dir, path, logger_name, csv_path):
    """
    Processes all email files in the dataset and extracts relevant information.

    Parameters:
        data_dir (str): Directory containing email files.
        path (str): Path for logging.
        logger_name (str): Name of the logger.
        csv_path (str): Path to save the processed emails as CSV.

    Returns:
        str: Path to the saved CSV file.
    """
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

        data_preprocessing_logger = create_logger(path, logger_name)

        if not os.path.exists(data_dir):
            # pylint: disable=logging-fstring-interpolation
            data_preprocessing_logger.error(f"Directory {data_dir} does not exist!")
            # pylint: disable=logging-fstring-interpolation
            return pd.DataFrame()
        # pylint: disable=logging-fstring-interpolation
        data_preprocessing_logger.info(f"Processing emails in: {data_dir}")
        # pylint: disable=logging-fstring-interpolation

        for root, _, files in os.walk(data_dir):

            for file in files:
                total_files += 1
                try:
                    email_data = extract_email_data(
                        os.path.join(root, file), data_preprocessing_logger, header_keys
                    )
                    email_list.append(email_data)
                    if total_files % 10000 == 0:
                        sys.stdout.write(f"\rProcessed {total_files} emails so far")
                        sys.stdout.flush()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    error_message = f"Error processing {os.path.join(root, file)}: {e}"
                    data_preprocessing_logger.error(error_message, exc_info=True)
        # pylint: disable=logging-fstring-interpolation
        data_preprocessing_logger.info(f"Total emails processed: {total_files}")
        # pylint: disable=logging-fstring-interpolation

        # Convert to Pandas DataFrame
        df = pd.DataFrame(email_list)
        data_preprocessing_logger.info("DataFrame created successfully.")

        df.to_csv(csv_path, index=False)
        # pylint: disable=logging-fstring-interpolation
        data_preprocessing_logger.info(
            f"DataFrame saved to {csv_path} successfully in process_enron_emails."
        )
        # pylint: disable=logging-fstring-interpolation

        return csv_path
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Error in process_enron_emails function: {e}"
        data_preprocessing_logger.error(error_message, exc_info=True)
        return None


if __name__ == "__main__":
    # Path to the extracted dataset
    MAILDIR_PATH = "./data_pipeline/data/dataset/maildir"

    CSV_PATH = "./data_pipeline/data/enron_emails.csv"

    PATH = "./data_pipeline/logs/data_preprocessing_log.log"
    LOGGER_NAME = "data_preprocessing_logger"

    # Process all emails
    df_enron = process_enron_emails(MAILDIR_PATH, PATH, LOGGER_NAME, CSV_PATH)
