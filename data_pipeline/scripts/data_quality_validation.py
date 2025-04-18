"""
Module for data validation using Great Expectations.

This script validates email datasets against predefined data expectations,
ensuring data quality, consistency, and schema integrity.

Functions:
    validate_data(csv_path, suite, context_root_dir, log_path, logger_name)
"""
import pandas as pd
import great_expectations as gx
from create_logger import create_logger
from airflow.operators.python import get_current_context
from great_expectations.core.expectation_suite import ExpectationSuite

def validate_data(log_path, logger_name, **kwargs):
    """
    Validates cleaned Enron email data against expectations using Great Expectations.
    Pulls all inputs via XCom: csv_path, context_root_dir, and expectation suite.
    """
    ti = kwargs["ti"]
    csv_path = ti.xcom_pull(task_ids="clean_data", key="return_value")
    suite_dict = ti.xcom_pull(task_ids="expectation_suite", key="return_value")
    context_root_dir = ti.xcom_pull(task_ids="setup_gx_context_and_logger", key="return_value")

    if not all([csv_path, suite_dict, context_root_dir]):
        raise ValueError("❌ Missing one or more required XCom values: csv_path, suite, or context_root_dir.")

    suite = ExpectationSuite(**suite_dict)
    context = gx.get_context(context_root_dir=context_root_dir)
    data_quality_logger = create_logger(log_path, logger_name)

    try:
        df = pd.read_csv(csv_path)
        data_quality_logger.info("Starting validation with Great Expectations...")

        try:
            data_source = context.data_sources.get(name="enron_data_source")
        except Exception:
            data_source = context.data_sources.add_pandas(name="enron_data_source")

        try:
            data_asset = data_source.get_asset(name="enron_email_data")
        except Exception:
            data_asset = data_source.add_dataframe_asset(name="enron_email_data")

        try:
            batch_definition = data_asset.get_batch_definition("enron_batch_definition")
        except Exception:
            batch_definition = data_asset.add_batch_definition_whole_dataframe("enron_batch_definition")

        batch_definition.get_batch(batch_parameters={"dataframe": df})

        validation_definition = gx.ValidationDefinition(
            data=batch_definition, suite=suite, name="enron_validation_definition"
        )
        validation_definition = context.validation_definitions.add_or_update(validation_definition)
        validation_result = validation_definition.run(batch_parameters={"dataframe": df})
        result_dict = validation_result.to_json_dict()
        data_quality_logger.info("✅ Validations completed successfully!")

        return {
    "success": result_dict["success"],
    "results": result_dict["results"],  # now it's serializable!
    "expectation_suite_name": suite.name,
    "results_count": len(result_dict["results"]),
    "unexpected_count": sum(
        r["result"].get("unexpected_count", 0)
        for r in result_dict["results"]
        if "result" in r
    ),
}


    except Exception as e:
        error_message = f"❌ Error in Validation: {e}"
        data_quality_logger.error(error_message, exc_info=True)
        return None