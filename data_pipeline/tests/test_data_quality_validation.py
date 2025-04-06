"""
Unit tests for the data_quality_validation funtions.
"""

import os
import sys
import pandas as pd
import pytest
import great_expectations as gx
from pytest_mock import MockerFixture

# Add scripts folder to sys.path
scripts_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
sys.path.append(scripts_folder)

# pylint: disable=wrong-import-position
from data_quality_validation import validate_data

# pylint: enable=wrong-import-position


@pytest.fixture
def setup_paths(tmp_path):
    """Fixture to create temporary paths for testing."""
    return {
        "csv_path": str(tmp_path / "enron_emails.csv"),
        "context_root_dir": str(tmp_path / "gx"),
        "log_path": str(tmp_path / "logs" / "data_quality_log.log"),
        "logger_name": "test_data_quality_logger",
    }


@pytest.fixture
def sample_email_data():
    """Fixture for sample email data."""
    return {
        "Message-ID": ["<123@example.com>"],
        "Date": ["2023-01-01"],
        "From": ["sender@example.com"],
        "To": ["recipient@example.com"],
        "Subject": ["Meeting"],
        "Cc": [None],
        "Bcc": [None],
        "X-From": ["Sender Name"],
        "X-To": ["Recipient Name"],
        "X-Cc": [None],
        "Body": ["Hello"],
    }


@pytest.fixture
def empty_csv():
    """Fixture for an empty CSV structure."""
    return {
        "Message-ID": [],
        "Date": [],
        "From": [],
        "To": [],
        "Subject": [],
        "Cc": [],
        "Bcc": [],
        "X-From": [],
        "X-To": [],
        "X-Cc": [],
        "Body": [],
    }


@pytest.fixture
def mock_suite():
    """Fixture for a mock expectation suite."""
    return gx.ExpectationSuite(name="mock_suite")


# pylint: disable=redefined-outer-name
def test_validate_data_success(
    mocker: MockerFixture, sample_email_data, setup_paths, mock_suite
):
    """Test successful validation of data."""
    df = pd.DataFrame(sample_email_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mock_validation_result = mocker.MagicMock()

    mocker.patch("great_expectations.get_context", return_value=mock_context)
    mock_data_source = mocker.MagicMock()
    mock_data_asset = mocker.MagicMock()
    mock_batch_def = mocker.MagicMock()

    mock_context.data_sources.get.side_effect = gx.exceptions.DataContextError("mock")
    mock_context.data_sources.add_pandas.return_value = mock_data_source
    mock_data_source.get_asset.side_effect = gx.exceptions.DataContextError("mock")
    mock_data_source.add_dataframe_asset.return_value = mock_data_asset
    mock_data_asset.get_batch_definition.side_effect = gx.exceptions.DataContextError(
        "mock"
    )
    mock_data_asset.add_batch_definition_whole_dataframe.return_value = mock_batch_def
    mock_batch_def.get_batch.return_value = "mock_batch"

    mock_validation_def = mocker.MagicMock()
    mocker.patch(
        "great_expectations.ValidationDefinition", return_value=mock_validation_def
    )
    mock_context.validation_definitions.add_or_update.return_value = mock_validation_def
    mock_validation_def.run.return_value = mock_validation_result

    result = validate_data(
        setup_paths["csv_path"],
        mock_suite,
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result == mock_validation_result
    mock_logger.info.assert_any_call("Setting up Validation Definition to run...")
    mock_logger.info.assert_any_call("Validations ran successfully")
    mock_logger.error.assert_not_called()


def test_validate_data_missing_csv(mocker: MockerFixture, setup_paths, mock_suite):
    """Test handling of missing CSV file."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    with pytest.raises(FileNotFoundError) as exc_info:
        validate_data(
            setup_paths["csv_path"],
            mock_suite,
            setup_paths["context_root_dir"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == f"CSV file not found: {setup_paths['csv_path']}"
    mock_logger.error.assert_called_once_with(
        f"CSV file not found: {setup_paths['csv_path']}"
    )


def test_validate_data_empty_csv(mocker: MockerFixture, setup_paths, mock_suite):
    """Test validation with an empty CSV."""
    with open(setup_paths["csv_path"], "w", encoding="utf-8") as f:
        f.write("")  # Create a truly empty file

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    with pytest.raises(pd.errors.EmptyDataError) as exc_info:
        validate_data(
            setup_paths["csv_path"],
            mock_suite,
            setup_paths["context_root_dir"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == f"CSV file is empty: {setup_paths['csv_path']}"
    mock_logger.error.assert_called_once_with(
        f"CSV file is empty: {setup_paths['csv_path']}"
    )


def test_validate_data_validation_run_failure(
    mocker: MockerFixture, setup_paths, mock_suite, sample_email_data
):
    """Test failure during validation run."""
    df = pd.DataFrame(sample_email_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()

    mocker.patch("great_expectations.get_context", return_value=mock_context)
    mock_data_source = mocker.MagicMock()
    mock_data_asset = mocker.MagicMock()
    mock_batch_def = mocker.MagicMock()

    mock_context.data_sources.get.side_effect = gx.exceptions.DataContextError("mock")
    mock_context.data_sources.add_pandas.return_value = mock_data_source
    mock_data_source.get_asset.side_effect = gx.exceptions.DataContextError("mock")
    mock_data_source.add_dataframe_asset.return_value = mock_data_asset
    mock_data_asset.get_batch_definition.side_effect = gx.exceptions.DataContextError(
        "mock"
    )
    mock_data_asset.add_batch_definition_whole_dataframe.return_value = mock_batch_def
    mock_batch_def.get_batch.return_value = "mock_batch"

    mock_validation_def = mocker.MagicMock()
    mocker.patch(
        "great_expectations.ValidationDefinition", return_value=mock_validation_def
    )
    mock_context.validation_definitions.add_or_update.return_value = mock_validation_def
    mock_validation_def.run.side_effect = gx.exceptions.ValidationError(
        "Validation run error"
    )

    with pytest.raises(gx.exceptions.ValidationError) as exc_info:
        validate_data(
            setup_paths["csv_path"],
            mock_suite,
            setup_paths["context_root_dir"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == "Validation run error"
    mock_logger.error.assert_called_once_with(
        "Validation run failed: Validation run error", exc_info=True
    )


def test_validate_data_invalid_input(mocker: MockerFixture, setup_paths, mock_suite):
    """Test raising ValueError for invalid input."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)

    with pytest.raises(ValueError) as exc_info:
        validate_data(
            "",
            mock_suite,
            setup_paths["context_root_dir"],
            setup_paths["log_path"],
            setup_paths["logger_name"],
        )
    assert str(exc_info.value) == "One or more input parameters are empty"


if __name__ == "__main__":
    pytest.main()
