"""
Module for handling data anomalies and sending notifications.

This module includes:
- `send_email_notification`: Sends email alerts using OAuth2 authentication.
- `handle_anomalies`: Logs detected anomalies and sends alerts if necessary.

Usage:
    Call `handle_anomalies` after validation to log and notify anomalies.

Functions:
    send_email_notification(subject, body, to_email, oauth_config, logger):
        Sends an email alert about detected anomalies.
    
    handle_anomalies(validation_results, log_path, logger_name):
        Logs anomalies and triggers email alerts when required.

"""

import smtplib
from email.mime.text import MIMEText
import base64
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from create_logger import create_logger
from dotenv import load_dotenv

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

dotenv_path = os.path.join(ROOT_DIR, ".env")

load_dotenv(dotenv_path=dotenv_path)


def send_email_notification(subject, body, to_email, oauth_config, data_anomaly_logger):
    """
    Sends an email notification using OAuth2 authentication.

    Parameters:
        subject (str): Email subject.
        body (str): Email body content.
        to_email (str): Recipient email address.
        oauth_config (dict): OAuth credentials for authentication.
        data_anomaly_logger (Logger): Logger for recording email status.

    Returns:
        bool: True if email is sent successfully, False otherwise.
    """
    try:
        creds = Credentials(
            token=None,
            refresh_token=oauth_config["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=oauth_config["client_id"],
            client_secret=oauth_config["client_secret"],
        )
        if not creds.valid or creds.token is None:
            if creds.refresh_token:
                creds.refresh(Request())
            else:
                data_anomaly_logger.error("No valid token or refresh token available")
                return False

        if not creds.valid or creds.token is None:
            data_anomaly_logger.error(
                "OAuth token remains invalid after refresh attempt"
            )
            return False

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = oauth_config["sender_email"]
        msg["To"] = to_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            auth_string = (
                f"user={oauth_config['sender_email']}\1auth=Bearer {creds.token}\1\1"
            )
            server.docmd(
                "AUTH", "XOAUTH2 " + base64.b64encode(auth_string.encode()).decode()
            )
            server.send_message(msg)
        return True
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Failed to send email: {e}"
        data_anomaly_logger.error(error_message, exc_info=True)
        return False


def handle_anomalies(validation_results, log_path, logger_name):
    """
    Handles detected anomalies by logging details and sending email notifications.

    Parameters:
        validation_results (dict): Validation results containing anomaly details.
        log_path (str): Path for logging.
        logger_name (str): Name of the logger.
    """
    data_anomaly_logger = create_logger(log_path, logger_name)
    try:
        anomalies = [
            result for result in validation_results["results"] if not result["success"]
        ]
        if anomalies:
            anomaly_details = []
            data_anomaly_logger.warning("Anomalies detected:")

            # Log detected anomalies
            for anomaly in anomalies:
                anomaly_info = {
                    "column": anomaly["expectation_config"]["kwargs"]["column"],
                    "expectation": anomaly["expectation_config"]["type"],
                    "unexpected_count": anomaly["result"].get("unexpected_count"),
                    "unexpected_percent": anomaly["result"].get("unexpected_percent"),
                    "partial_indexes": anomaly["result"].get(
                        "partial_unexpected_index_list", []
                    ),
                }
                detail = (
                    f"Column: {anomaly_info['column']}, "
                    f"Expectation: {anomaly_info['expectation']}, "
                    f"Unexpected Count: {anomaly_info['unexpected_count']}, "
                    f"Unexpected Percent: {anomaly_info['unexpected_percent']}, "
                    f"Partial Indexes: {anomaly_info['partial_indexes']}"
                )
                data_anomaly_logger.info(detail)
                anomaly_details.append(detail)

            oauth_config = {
                "client_id": os.getenv("google_client_id"),
                "client_secret": os.getenv("google_client_secret"),
                "refresh_token": os.getenv("google_refresh_token"),
                "sender_email": os.getenv("sender_email"),
            }

            # Send email notification
            email_body = "Anomalies detected in email dataset:\n\n" + "\n".join(
                anomaly_details
            )
            is_email_sent = send_email_notification(
                subject="Email Dataset Anomalies Detected",
                body=email_body,
                to_email=os.getenv("receiver_email"),
                oauth_config=oauth_config,
                data_anomaly_logger=data_anomaly_logger,
            )
            if not is_email_sent:
                data_anomaly_logger.error("Email Sending Unsuccessful....")
                return
            data_anomaly_logger.info("Email notification sent successfully.")
        else:
            data_anomaly_logger.info("No anomalies detected.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = f"Error in Anomaly Handling: {e}"
        data_anomaly_logger.error(error_message, exc_info=True)
