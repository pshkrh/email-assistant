"""
Module for defining data validation expectations using Great Expectations.

This module sets up expectations for email datasets, ensuring data integrity
and consistency in key columns like Message-ID, Date, From, To, and Body.

Functions:
    define_expectations(csv_path, context_root_dir, log_path, logger_name)
"""

import great_expectations as gx
import pandas as pd
from create_logger import create_logger

def define_expectations(log_path, logger_name, **kwargs):
    ti = kwargs["ti"]
    context_root_dir = ti.xcom_pull(task_ids="setup_gx_context_and_logger", key="return_value")
    csv_path = ti.xcom_pull(task_ids="clean_data", key="return_value")

    if context_root_dir is None or csv_path is None:
        raise ValueError("❌ Missing context_root_dir or csv_path from XCom.")

    data_quality_logger = create_logger(log_path, logger_name)
    context = gx.get_context(context_root_dir=context_root_dir)

    try:
        data_quality_logger.info("Setting up Expectations in Suite")
        df = pd.read_csv(csv_path)

        # ✅ Self-healing fallback for expected columns
        if "thread_id" in df.columns and df["thread_id"].isna().sum() > 0:
            df["thread_id"].fillna("unknown_thread", inplace=True)
            data_quality_logger.warning("Filled missing 'thread_id' with 'unknown_thread'.")

        if "email_type" in df.columns and df["email_type"].isna().sum() > 0:
            df["email_type"].fillna("unknown", inplace=True)
            data_quality_logger.warning("Filled missing 'email_type' with 'unknown'.")

        suite = gx.ExpectationSuite(name="enron_expectation_suite")
        suite = context.suites.add_or_update(suite)

        # Core schema expectations
        not_null_columns = ["Message-ID", "From", "Body"]
        for column in not_null_columns:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
            )

        # Email structure
        email_regex = {
            "From": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "To": r"^.+@.+\\..+$",
            "Cc": r"^.+@.+\\..+$",
            "Bcc": r"^.+@.+\\..+$",
        }
        for column, regex in email_regex.items():
            if column in df.columns:
                suite.add_expectation(
                    gx.expectations.ExpectColumnValuesToMatchRegex(
                        column=column, regex=regex, mostly=0.95
                    )
                )

        # Partial null allowances
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="Date", mostly=0.95)
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="X-From", mostly=0.90)
        )

        # # Uniqueness check
        # suite.add_expectation(
        #     gx.expectations.ExpectColumnUniqueValueCountToBeBetween(
        #         column="Message-ID", min_value=len(df), max_value=len(df)
        #     )
        # )

        # Date sanity
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeInSet(
                column="Date",
                value_set=pd.date_range("1980-01-01", pd.Timestamp.now(), freq="D")
                .strftime("%Y-%m-%d")
                .tolist(),
                mostly=0.90
            )
        )

        # Subject should exist for thread context
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="Subject", mostly=0.95)
        )

        # Action-oriented words
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToMatchRegex(
                column="Body",
                regex=r"(?i)\b(meeting|please|need|action|do|send|review|urgent|asap|respond|confirm|follow-up|complete|check)\b",
                mostly=0.50,
            )
        )

        # Email reply feasibility
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="To", mostly=0.95)
        )

        # ✅ NEW: Expectations on cleaned columns
        if "thread_id" in df.columns:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToNotBeNull(column="thread_id", mostly=0.99)
            )
        if "email_part" in df.columns:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToBeBetween(column="email_part", min_value=1)
            )
        if "email_type" in df.columns:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToBeInSet(
                    column="email_type",
                    value_set=["original", "reply", "forward", "unknown"]
                )
            )

        data_quality_logger.info("Created Expectation Suite successfully")
        return suite.to_json_dict()

    except Exception as e:
        data_quality_logger.error(f"Error in Expectations: {e}", exc_info=True)
        return None
