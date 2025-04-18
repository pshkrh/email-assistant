"""
Notification Module

This module handles email notifications for system errors and important alerts.
It supports different environments including Cloud Run and GitHub Actions.
"""

import os
import base64
import time
import json
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from google.cloud import logging as gcp_logging
from google.oauth2.credentials import Credentials

from config import (
    IN_CLOUD_RUN,
    GCP_PROJECT_ID,
    GMAIL_NOTIFICATION_SECRET_ID,
)

# Import secrets manager if in Cloud Run
if IN_CLOUD_RUN:
    from secret_manager import get_credentials_from_secret

    # Initialize GCP Cloud Logging
    gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
    gcp_logger = gcp_client.logger("notification_sender")

# Check if running in GitHub Actions
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


def send_email_notification(error_type, error_message, request_id=None):
    """
    Send an email notification for a failure or alert.

    Args:
        error_type (str): Type of error or alert
        error_message (str): Detailed error message
        request_id (str, optional): Unique identifier for request correlation

    Raises:
        Exception: If email sending fails
    """
    try:
        # Load credentials based on environment
        if IN_CLOUD_RUN:
            # Get credentials from GCP Secret Manager
            creds_dict = get_credentials_from_secret(
                GCP_PROJECT_ID, GMAIL_NOTIFICATION_SECRET_ID
            )
            credentials = Credentials.from_authorized_user_info(creds_dict)
        elif IN_GITHUB_ACTIONS:
            # In GitHub Actions, use base64-encoded credentials
            creds_b64 = os.getenv("GCP_GMAIL_SA_KEY_JSON")
            creds_json = base64.b64decode(creds_b64).decode("utf-8")
            creds_dict = json.loads(creds_json)

            credentials = Credentials.from_authorized_user_info(
                creds_dict, scopes=["https://www.googleapis.com/auth/gmail.send"]
            )
        else:
            # Local development not supported for notifications
            raise NotImplementedError(
                "Local credential loading not supported in production"
            )

        # Build Gmail service
        service = build("gmail", "v1", credentials=credentials)

        # Get email details from environment variables or use defaults
        sender = os.getenv(
            "NOTIFICATION_SENDER_EMAIL",
            "shubhdesai111@gmail.com",
        )
        recipient = os.getenv("NOTIFICATION_RECIPIENT_EMAIL", "shubhdesai4@gmail.com")
        subject = f"Alert: {error_type} Failure in Email Assistant"

        # Format the email body
        body = f"""
        Error Type: {error_type}
        Request ID: {request_id or 'unknown'}
        Error Message: {error_message}
        Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
        Project: {GCP_PROJECT_ID}
        """

        # Create MIME message
        message = MIMEText(body)
        message["to"] = recipient
        message["from"] = sender
        message["subject"] = subject

        # Encode and send the message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        # Log successful notification
        if IN_CLOUD_RUN:
            gcp_logger.log_struct(
                {
                    "message": f"Sent email notification for {error_type}",
                    "request_id": request_id or "unknown",
                    "recipient": recipient,
                },
                severity="INFO",
            )

    except Exception as e:
        # Log notification failure
        if IN_CLOUD_RUN:
            gcp_logger.log_struct(
                {
                    "message": f"Failed to send email notification for {error_type}",
                    "error": str(e),
                    "request_id": request_id or "unknown",
                },
                severity="ERROR",
            )
        raise  # Re-raise the exception for caller handling
