import os
import base64
import time
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.cloud import logging as gcp_logging
from config import (
    IN_CLOUD_RUN,
    GCP_PROJECT_ID,
    GMAIL_API_CREDENTIALS,
    GMAIL_API_SECRET_ID,
)

if IN_CLOUD_RUN:
    from secret_manager import get_credentials_from_secret

# Initialize GCP Cloud Logging
gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("notification_sender")


def send_email_notification(error_type, error_message, request_id=None):
    """Send an email notification for a failure."""
    try:
        # Load credentials
        if IN_CLOUD_RUN:
            get_credentials_from_secret(
                GCP_PROJECT_ID, GMAIL_API_SECRET_ID, save_to_file=GMAIL_API_CREDENTIALS
            )

        creds_file = GMAIL_API_CREDENTIALS
        if not os.path.exists(creds_file):
            raise FileNotFoundError(f"Gmail API credentials not found at {creds_file}")

        service = build("gmail", "v1", credentials=creds_file)

        # Email details
        sender = os.getenv(
            "NOTIFICATION_SENDER_EMAIL",
            "gmail-sender@email-assistant-449706.iam.gserviceaccount.com",
        )
        recipient = os.getenv("NOTIFICATION_RECIPIENT_EMAIL", "shubhdesai4@gmail.com")
        subject = f"Alert: {error_type} Failure in Email Assistant"
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

        # Encode and send
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        gcp_logger.log_struct(
            {
                "message": f"Sent email notification for {error_type}",
                "request_id": request_id or "unknown",
                "recipient": recipient,
            },
            severity="INFO",
        )

    except Exception as e:
        gcp_logger.log_struct(
            {
                "message": f"Failed to send email notification for {error_type}",
                "error": str(e),
                "request_id": request_id or "unknown",
            },
            severity="ERROR",
        )
