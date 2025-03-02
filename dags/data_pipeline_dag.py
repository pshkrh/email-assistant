from airflow import DAG
from airflow.operators.python import PythonOperator
import sys

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


# Enable pickle support for XCom, allowing data to be passed between tasks
conf.conf.set("core", "enable_xcom_pickling", "True")
conf.conf.set("core", "enable_parquet_xcom", "True")

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

download_dataset = PythonOperator(
    task_id="download_enron_dataset",
    python_callable=download_enron_dataset,
    op_args=[
        "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz",
        "./dags/data_pipeline/data/enron_mail_20150507.tar.gz",
        "./dags/data_pipeline/logs/data_downloading_log.log",
        "data_downloading_logger",
    ],
    dag=dag,
)

unzip_file_task = PythonOperator(
    task_id="extract_enron_dataset",
    python_callable=extract_enron_dataset,
    op_args=[
        download_dataset.output,
        "./dags/data_pipeline/data/dataset",
        "./dags/data_pipeline/logs/data_extraction_log.log",
        "data_extraction_logger",
    ],
    dag=dag,
)

preprocess_emails = PythonOperator(
    task_id="process_enron_emails",
    python_callable=process_enron_emails,
    op_args=[
        unzip_file_task.output,
        "./dags/data_pipeline/logs/data_preprocessing_log.log",
        "data_preprocessing_logger",
        "./dags/data_pipeline/data/enron_emails.csv",
    ],
    dag=dag,
)

clean_email_dates = PythonOperator(
    task_id="clean_email_dates",
    python_callable=clean_and_parse_dates,
    op_args=[
        preprocess_emails.output,
        "./dags/data_pipeline/logs/data_preprocessing_log.log",
        "data_preprocessing_logger",
    ],
    dag=dag,
)

gx_context = PythonOperator(
    task_id="setup_gx_context_and_logger",
    python_callable=setup_gx_context_and_logger,
    op_args=[
        "./dags/data_pipeline/gx",
        "./dags/data_pipeline/logs/data_quality_log.log",
        "data_quality_logger",
    ],
    dag=dag,
)

suite = PythonOperator(
    task_id="expectation_suite",
    python_callable=define_expectations,
    op_args=[
        clean_email_dates.output,
        gx_context.output,
        "./dags/data_pipeline/logs/data_quality_log.log",
        "data_quality_logger",
    ],
    dag=dag,
)

validation_results = PythonOperator(
    task_id="validation",
    python_callable=validate_data,
    op_args=[
        clean_email_dates.output,
        suite.output,
        gx_context.output,
        "./dags/data_pipeline/logs/data_quality_log.log",
        "data_quality_logger",
    ],
    dag=dag,
)

handle_anomaly = PythonOperator(
    task_id="anomaly",
    python_callable=handle_anomalies,
    op_args=[
        validation_results.output,
        "./dags/data_pipeline/logs/data_anomaly_log.log",
        "data_anomaly_logger",
    ],
    dag=dag,
)

# ------------------ Task Dependencies ------------------

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
