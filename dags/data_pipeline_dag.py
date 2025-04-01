import sys
import os
from airflow import DAG
from airflow.operators.python import PythonOperator

# from airflow.operators.empty import EmptyOperator
from airflow import configuration as conf
from datetime import datetime, timedelta

# Add scripts folder to sys.path to make modules available for import
sys.path.append("/opt/airflow/dags/data_pipeline/scripts")
sys.path.append("/opt/airflow/dags/data_pipeline/logs")
sys.path.append("/opt/airflow/dags/data_pipeline/data")

from data_pipeline.scripts.download_dataset import download_enron_dataset
from data_pipeline.scripts.extract_dataset import extract_enron_dataset
from data_pipeline.scripts.dataframe import process_enron_emails
from data_pipeline.scripts.clean_and_parse_dates import clean_and_parse_dates
from data_pipeline.scripts.data_quality_setup import setup_gx_context_and_logger
from data_pipeline.scripts.data_quality_expectations import define_expectations
from data_pipeline.scripts.data_quality_validation import validate_data
from data_pipeline.scripts.data_quality_anomaly import handle_anomalies
from data_pipeline.scripts.get_project_root import project_root

# Default arguments for DAG
default_args = {
    "owner": "airflow2",
    "start_date": datetime(2023, 11, 9),
    "retries": 0,  # Number of retries in case of task failure
    "retry_delay": timedelta(minutes=5),  # Delay before retries
}

# Create a DAG instance named 'datapipeline'
dag = DAG(
    "datapipeline",
    default_args=default_args,
    description="Airflow DAG for the datapipeline",
    schedule_interval=None,  # Set the schedule interval or use None for manual triggering
    catchup=False,
)

# ------------------ Tasks ------------------

project_root_dir = PythonOperator(
    task_id="project_root",
    python_callable=project_root,
    dag=dag,
)

download_dataset = PythonOperator(
    task_id="download_enron_dataset",
    python_callable=download_enron_dataset,
    op_kwargs={
        "url": "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz",
        "save_path": f"{project_root_dir.output}/data_pipeline/data/enron_mail_20150507.tar.gz",
        "log_path": f"{project_root_dir.output}/data_pipeline/logs/data_downloading_log.log",
        "logger_name": "data_downloading_logger",
    },
    dag=dag,
)

project_root_dir >> download_dataset

unzip_file_task = PythonOperator(
    task_id="extract_enron_dataset",
    python_callable=extract_enron_dataset,
    op_kwargs={
        "archive_path": download_dataset.output,
        "extract_to": f"{project_root_dir.output}/data_pipeline/data/dataset",
        "log_path": f"{project_root_dir.output}/data_pipeline/logs/data_extraction_log.log",
        "logger_name": "data_extraction_logger",
    },
    dag=dag,
)

preprocess_emails = PythonOperator(
    task_id="process_enron_emails",
    python_callable=process_enron_emails,
    op_kwargs={
        "data_dir": unzip_file_task.output,
        "csv_path": f"{project_root_dir.output}/data_pipeline/data/enron_emails.csv",
        "log_path": f"{project_root_dir.output}/data_pipeline/logs/data_preprocessing_log.log",
        "logger_name": "data_preprocessing_logger",
    },
    dag=dag,
)

clean_email_dates = PythonOperator(
    task_id="clean_email_dates",
    python_callable=clean_and_parse_dates,
    op_kwargs={
        "csv_path": preprocess_emails.output,
        "log_path": f"{project_root_dir.output}/data_pipeline/logs/data_preprocessing_log.log",
        "logger_name": "data_preprocessing_logger",
    },
    dag=dag,
)

gx_context = PythonOperator(
    task_id="setup_gx_context_and_logger",
    python_callable=setup_gx_context_and_logger,
    op_kwargs={
        "context_root_dir": f"{project_root_dir.output}/data_pipeline/gx",
        "log_path": f"{project_root_dir.output}/data_pipeline/logs/data_quality_log.log",
        "logger_name": "data_quality_logger",
    },
    dag=dag,
)

suite = PythonOperator(
    task_id="expectation_suite",
    python_callable=define_expectations,
    op_kwargs={
        "csv_path": clean_email_dates.output,
        "context_root_dir": gx_context.output,
        "log_path": f"{project_root_dir.output}/data_pipeline/logs/data_quality_log.log",
        "logger_name": "data_quality_logger",
    },
    dag=dag,
)

validation_results = PythonOperator(
    task_id="validation",
    python_callable=validate_data,
    op_kwargs={
        "csv_path": clean_email_dates.output,
        "suite": suite.output,
        "context_root_dir": gx_context.output,
        "log_path": f"{project_root_dir.output}/data_pipeline/logs/data_quality_log.log",
        "logger_name": "data_quality_logger",
    },
    dag=dag,
)

handle_anomaly = PythonOperator(
    task_id="anomaly",
    python_callable=handle_anomalies,
    op_kwargs={
        "validation_results": validation_results.output,
        "log_path": f"{project_root_dir.output}/data_pipeline/logs/data_anomaly_log.log",
        "logger_name": "data_anomaly_logger",
    },
    dag=dag,
)

# # ------------------ Task Dependencies ------------------

(
    download_dataset
    >> unzip_file_task
    >> preprocess_emails
    >> clean_email_dates
    >> gx_context
    >> suite
    >> validation_results
    >> handle_anomaly
)
