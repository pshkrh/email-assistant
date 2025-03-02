"""
Unit tests for the data_quality_anomaly funtions.
"""

import os
import sys
from pytest_mock import MockerFixture
import pytest

# Add scripts folder to sys.path
scripts_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.append(scripts_folder)

# pylint: disable=wrong-import-position

from data_quality_anomaly import (
    send_email_notification,
    handle_anomalies,
)  # Adjusted to corrected filename

# pylint: enable=wrong-import-position


@pytest.fixture
def oauth_config():
    """Fixture for OAuth configuration."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "refresh_token": "test_refresh_token",
        "sender_email": "test@gmail.com",
    }


@pytest.fixture
def mock_logger(mocker):
    """Fixture for a mock logger."""
    return mocker.MagicMock()


# pylint: disable=redefined-outer-name
# Tests for send_email_notification
def test_send_email_notification_success_already_valid(
    mocker: MockerFixture, oauth_config, mock_logger
):
    """Test successful email sending with an already valid token."""
    mock_credentials = mocker.MagicMock()
    mock_smtp = mocker.patch("smtplib.SMTP")
    mock_server = mock_smtp.return_value.__enter__.return_value
    mocker.patch("data_quality_anomaly.Credentials", return_value=mock_credentials)
    mock_credentials.valid = True
    mock_credentials.token = "valid_token"
    mock_server.docmd.return_value = (235, b"2.7.0 Accepted")

    result = send_email_notification(
        subject="Test Subject",
        body="Test Body",
        to_email="recipient@example.com",
        oauth_config=oauth_config,
        data_anomaly_logger=mock_logger,
    )

    assert result is True
    mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.docmd.assert_called_once()
    mock_server.send_message.assert_called_once()
    mock_logger.error.assert_not_called()


def test_send_email_notification_success_refresh(
    mocker: MockerFixture, oauth_config, mock_logger
):
    """Test successful email sending with token refresh."""
    mock_credentials = mocker.MagicMock()
    mock_smtp = mocker.patch("smtplib.SMTP")
    mock_server = mock_smtp.return_value.__enter__.return_value
    mocker.patch("data_quality_anomaly.Credentials", return_value=mock_credentials)
    mock_request = mocker.patch("data_quality_anomaly.Request")
    mock_credentials.valid = False
    mock_credentials.token = None
    mock_credentials.refresh.side_effect = lambda req: setattr(
        mock_credentials, "token", "refreshed_token"
    ) or setattr(mock_credentials, "valid", True)
    mock_server.docmd.return_value = (235, b"2.7.0 Accepted")

    result = send_email_notification(
        subject="Test Subject",
        body="Test Body",
        to_email="recipient@example.com",
        oauth_config=oauth_config,
        data_anomaly_logger=mock_logger,
    )

    assert result is True
    mock_credentials.refresh.assert_called_once_with(mock_request.return_value)
    mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.docmd.assert_called_once()
    mock_server.send_message.assert_called_once()
    mock_logger.error.assert_not_called()


def test_send_email_notification_no_refresh_token(
    mocker: MockerFixture, oauth_config, mock_logger
):
    """Test failure when no refresh token is available."""
    oauth_config_no_refresh = oauth_config.copy()
    oauth_config_no_refresh["refresh_token"] = None
    mock_credentials = mocker.MagicMock()
    mocker.patch("data_quality_anomaly.Credentials", return_value=mock_credentials)
    mock_credentials.valid = False
    mock_credentials.token = None

    result = send_email_notification(
        subject="Test Subject",
        body="Test Body",
        to_email="recipient@example.com",
        oauth_config=oauth_config_no_refresh,
        data_anomaly_logger=mock_logger,
    )

    assert result is False
    mock_logger.error.assert_called_once_with(
        "OAuth token remains invalid after refresh attempt"
    )


def test_send_email_notification_refresh_failure(
    mocker: MockerFixture, oauth_config, mock_logger
):
    """Test failure when token refresh fails."""
    mock_credentials = mocker.MagicMock()
    mocker.patch("data_quality_anomaly.Credentials", return_value=mock_credentials)
    mocker.patch("data_quality_anomaly.Request")
    mock_credentials.valid = False
    mock_credentials.token = None
    mock_credentials.refresh.side_effect = Exception("Refresh failed")

    result = send_email_notification(
        subject="Test Subject",
        body="Test Body",
        to_email="recipient@example.com",
        oauth_config=oauth_config,
        data_anomaly_logger=mock_logger,
    )

    assert result is False
    mock_logger.error.assert_called_once_with(
        "Failed to send email: Refresh failed", exc_info=True
    )


def test_send_email_notification_smtp_failure(
    mocker: MockerFixture, oauth_config, mock_logger
):
    """Test failure during SMTP interaction."""
    mock_credentials = mocker.MagicMock()
    mocker.patch("data_quality_anomaly.Credentials", return_value=mock_credentials)
    mocker.patch("smtplib.SMTP", side_effect=Exception("SMTP connection failed"))
    mock_credentials.valid = True
    mock_credentials.token = "valid_token"

    result = send_email_notification(
        subject="Test Subject",
        body="Test Body",
        to_email="recipient@example.com",
        oauth_config=oauth_config,
        data_anomaly_logger=mock_logger,
    )

    assert result is False
    mock_logger.error.assert_called_once_with(
        "Failed to send email: SMTP connection failed", exc_info=True
    )


# Tests for handle_anomalies
def test_handle_anomalies_with_anomalies(mocker: MockerFixture, setup_paths):
    """Test handling anomalies with detected issues."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_anomaly.create_logger", return_value=mock_logger)
    mocker.patch("data_quality_anomaly.send_email_notification", return_value=True)

    validation_results = {
        "results": [
            {
                "success": False,
                "expectation_config": {
                    "type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "Body"},
                },
                "result": {
                    "unexpected_count": 5,
                    "unexpected_percent": 10.0,
                    "partial_unexpected_index_list": [1, 2, 3],
                },
            },
            {
                "success": True,
                "expectation_config": {
                    "type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "Message-ID"},
                },
                "result": {},
            },
        ]
    }

    handle_anomalies(
        validation_results, setup_paths["log_path"], setup_paths["logger_name"]
    )

    mock_logger.warning.assert_called_once_with("Anomalies detected:")
    mock_logger.info.assert_any_call(
        "Column: Body, Expectation: expect_column_values_to_not_be_null, "
        "Unexpected Count: 5, Unexpected Percent: 10.0, Partial Indexes: [1, 2, 3]"
    )
    mock_logger.info.assert_any_call("Email notification sent successfully.")
    mock_logger.error.assert_not_called()


def test_handle_anomalies_no_anomalies(mocker: MockerFixture, setup_paths):
    """Test handling when no anomalies are detected."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_anomaly.create_logger", return_value=mock_logger)

    validation_results = {
        "results": [
            {
                "success": True,
                "expectation_config": {
                    "type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "Body"},
                },
                "result": {},
            }
        ]
    }

    handle_anomalies(
        validation_results, setup_paths["log_path"], setup_paths["logger_name"]
    )

    mock_logger.info.assert_called_once_with("No anomalies detected.")
    mock_logger.warning.assert_not_called()
    mock_logger.error.assert_not_called()


def test_handle_anomalies_logger_failure(mocker: MockerFixture, setup_paths):
    """Test handling logger creation failure."""
    mocker.patch(
        "data_quality_anomaly.create_logger",
        side_effect=Exception("Logger creation failed"),
    )
    validation_results = {"results": []}

    with pytest.raises(Exception, match="Logger creation failed"):
        handle_anomalies(
            validation_results, setup_paths["log_path"], setup_paths["logger_name"]
        )


def test_handle_anomalies_for_email_failure(mocker: MockerFixture, setup_paths):
    """Test handling email sending failure."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_anomaly.create_logger", return_value=mock_logger)
    mocker.patch("data_quality_anomaly.send_email_notification", return_value=False)

    validation_results = {
        "results": [
            {
                "success": False,
                "expectation_config": {
                    "type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "Subject"},
                },
                "result": {
                    "unexpected_count": 2,
                    "unexpected_percent": 5.0,
                    "partial_unexpected_index_list": [0, 1],
                },
            }
        ]
    }

    handle_anomalies(
        validation_results, setup_paths["log_path"], setup_paths["logger_name"]
    )

    mock_logger.warning.assert_called_once_with("Anomalies detected:")
    mock_logger.info.assert_any_call(
        "Column: Subject, Expectation: expect_column_values_to_not_be_null, "
        "Unexpected Count: 2, Unexpected Percent: 5.0, Partial Indexes: [0, 1]"
    )

    assert "Email Sending Unsuccessful...." in [
        call.args[0] for call in mock_logger.error.call_args_list
    ]


def test_handle_anomalies_email_exception(mocker: MockerFixture, setup_paths):
    """Test handling when email sending raises an exception."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_anomaly.create_logger", return_value=mock_logger)
    mocker.patch(
        "data_quality_anomaly.send_email_notification",
        side_effect=Exception("Email send failed"),
    )

    validation_results = {
        "results": [
            {
                "success": False,
                "expectation_config": {
                    "type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "Subject"},
                },
                "result": {
                    "unexpected_count": 2,
                    "unexpected_percent": 5.0,
                    "partial_unexpected_index_list": [0, 1],
                },
            }
        ]
    }

    handle_anomalies(
        validation_results, setup_paths["log_path"], setup_paths["logger_name"]
    )

    mock_logger.warning.assert_called_once_with("Anomalies detected:")
    mock_logger.info.assert_any_call(
        "Column: Subject, Expectation: expect_column_values_to_not_be_null, "
        "Unexpected Count: 2, Unexpected Percent: 5.0, Partial Indexes: [0, 1]"
    )
    mock_logger.error.assert_called_once_with(
        "Error in Anomaly Handling: Email send failed", exc_info=True
    )


if __name__ == "__main__":
    pytest.main(["-v"])
