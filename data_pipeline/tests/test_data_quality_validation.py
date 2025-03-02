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

from data_quality_validation import (
    validate_data,
)

# pylint: enable=wrong-import-position


@pytest.fixture
def mock_suite():
    """Fixture for a mock expectation suite."""
    return "mock_suite"


# pylint: disable=redefined-outer-name
def test_validate_data_success(
    mocker: MockerFixture, sample_email_data, setup_paths, mock_suite
):
    """Test successful validation of data."""
    # Create a sample CSV with realistic email data
    initial_data = {
        "Message-ID": sample_email_data["Message-ID"],
        "Date": ["2023-01-01"],
        "From": sample_email_data["From"],
        "To": sample_email_data["To"],
        "Subject": ["Meeting"],
        "Cc": sample_email_data["Cc"],
        "Bcc": sample_email_data["Bcc"],
        "X-From": sample_email_data["X-From"],
        "X-To": sample_email_data["To"],
        "X-Cc": sample_email_data["X-Cc"],
        "Body": sample_email_data["Body"],
    }
    df = pd.DataFrame(initial_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mock_validation_result = mocker.MagicMock()

    # Simplified mocking
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    mock_data_source = mock_context.data_sources.add_pandas.return_value
    mock_data_asset = mock_data_source.add_dataframe_asset.return_value
    mock_batch_def = mock_data_asset.add_batch_definition_whole_dataframe.return_value
    mock_batch_def.get_batch.return_value = "mock_batch"

    mocker.patch(
        "great_expectations.ValidationDefinition",
        return_value=mocker.MagicMock(
            run=lambda batch_parameters: mock_validation_result
        ),
    )
    mock_context.validation_definitions.add_or_update.return_value.run.return_value = (
        mock_validation_result
    )

    result = validate_data(
        setup_paths["csv_path"],
        mock_suite,
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert (
        result == mock_validation_result
    ), f"Expected {mock_validation_result}, got {result}"
    mock_logger.info.assert_any_call("Setting up Validation Definition to run...")
    mock_logger.info.assert_any_call("Validations ran successfully")
    mock_logger.error.assert_not_called()


def test_validate_data_missing_csv(mocker: MockerFixture, setup_paths, mock_suite):
    """Test handling of missing CSV file."""
    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)
    mocker.patch("pandas.read_csv", side_effect=FileNotFoundError("No such file"))
    mock_context = mocker.MagicMock()
    mocker.patch("great_expectations.get_context", return_value=mock_context)

    result = validate_data(
        setup_paths["csv_path"],
        mock_suite,
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    mock_logger.error.assert_called_once_with(
        "Error in Validation: No such file", exc_info=True
    )


def test_validate_data_empty_csv(
    mocker: MockerFixture, setup_paths, mock_suite, empty_csv
):
    """Test validation with an empty CSV."""
    df = pd.DataFrame(empty_csv)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mock_validation_result = mocker.MagicMock()

    # Simplified chaining mocking
    mocker.patch("great_expectations.get_context", return_value=mock_context)
    mock_data_source = mock_context.data_sources.add_pandas.return_value
    mock_data_asset = mock_data_source.add_dataframe_asset.return_value
    mock_batch_def = mock_data_asset.add_batch_definition_whole_dataframe.return_value
    mock_batch_def.get_batch.return_value = "mock_batch"
    mocker.patch(
        "great_expectations.ValidationDefinition",
        return_value=mocker.MagicMock(
            run=lambda batch_parameters: mock_validation_result
        ),
    )
    mock_context.validation_definitions.add_or_update.return_value.run.return_value = (
        mock_validation_result
    )

    result = validate_data(
        setup_paths["csv_path"],
        mock_suite,
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert (
        result == mock_validation_result
    ), f"Expected {mock_validation_result}, got {result}"
    mock_logger.info.assert_any_call("Setting up Validation Definition to run...")
    mock_logger.info.assert_any_call("Validations ran successfully")
    mock_logger.error.assert_not_called()
    print(f"Logger info calls: {mock_logger.info.call_args_list}")
    print(f"Logger error calls: {mock_logger.error.call_args_list}")


def test_validate_data_validation_run_failure(
    mocker: MockerFixture, setup_paths, mock_suite, sample_email_data
):
    """Test failure during validation run."""
    initial_data = {
        "Message-ID": sample_email_data["Message-ID"],
        "Date": ["2023-01-01"],
        "From": sample_email_data["From"],
        "To": sample_email_data["To"],
        "Subject": ["Meeting"],
        "Cc": sample_email_data["Cc"],
        "Bcc": sample_email_data["Cc"],
        "X-From": sample_email_data["X-From"],
        "X-To": sample_email_data["X-To"],
        "X-Cc": sample_email_data["X-Cc"],
        "Body": ["Hello"],
    }
    df = pd.DataFrame(initial_data)
    df.to_csv(setup_paths["csv_path"], index=False)

    mock_logger = mocker.MagicMock()
    mocker.patch("data_quality_validation.create_logger", return_value=mock_logger)
    mock_context = mocker.MagicMock()
    mock_data_source = mocker.MagicMock()
    mock_data_asset = mocker.MagicMock()
    mock_batch_definition = mocker.MagicMock()
    mock_validation_definition = mocker.MagicMock()

    mocker.patch("great_expectations.get_context", return_value=mock_context)
    mock_context.data_sources.get.side_effect = gx.exceptions.DataContextError
    mock_context.data_sources.add_pandas.return_value = mock_data_source
    mock_data_source.get_asset.side_effect = gx.exceptions.DataContextError
    mock_data_source.add_dataframe_asset.return_value = mock_data_asset
    mock_data_asset.get_batch_definition.side_effect = gx.exceptions.DataContextError
    mock_data_asset.add_batch_definition_whole_dataframe.return_value = (
        mock_batch_definition
    )
    mock_batch_definition.get_batch.return_value = "mock_batch"
    mocker.patch(
        "great_expectations.ValidationDefinition",
        return_value=mock_validation_definition,
    )
    mock_context.validation_definitions.add_or_update.return_value = (
        mock_validation_definition
    )
    mock_validation_definition.run.side_effect = Exception("Validation run error")

    result = validate_data(
        setup_paths["csv_path"],
        mock_suite,
        setup_paths["context_root_dir"],
        setup_paths["log_path"],
        setup_paths["logger_name"],
    )

    assert result is None
    assert any(
        "Error in Validation:" in call.args[0]
        for call in mock_logger.error.call_args_list
    )


if __name__ == "__main__":
    pytest.main()
