"""
MLflow Configuration Module

This module handles the setup and configuration of MLflow tracking for the email assistant application.
It provides functions to configure the MLflow tracking URI, ensure experiments exist, and start runs.
"""

import os

import mlflow

from config import MLFLOW_LOG_DIR, MLFLOW_EXPERIMENT_NAME


def configure_mlflow(log_dir=MLFLOW_LOG_DIR):
    """
    Configure MLflow with tracking URI.

    Args:
        log_dir (str): Directory path for MLflow logging if using local filesystem

    Returns:
        object: MLflow experiment object if successful, None otherwise
    """
    # Set tracking URI - use environment variable if defined, otherwise use local filesystem
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"file://{log_dir}")

    # If using local filesystem, ensure the directory exists
    if tracking_uri.startswith("file://"):
        os.makedirs(log_dir, exist_ok=True)

    # Configure MLflow with the tracking URI
    mlflow.set_tracking_uri(tracking_uri)

    # Ensure the experiment exists
    try:
        # Try to get the experiment by name
        experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
        if experiment is None:
            # Create it if it doesn't exist
            mlflow.create_experiment(MLFLOW_EXPERIMENT_NAME)
            experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
        return experiment
    except Exception as e:
        # Log the error but continue - will fallback to default experiment
        print(f"Error ensuring experiment exists: {str(e)}")
        return None


def start_experiment(experiment_name=MLFLOW_EXPERIMENT_NAME):
    """
    Start an MLflow experiment.

    Args:
        experiment_name (str): Name of the experiment to start

    Returns:
        object: MLflow run object
    """
    # Configure MLflow first
    configure_mlflow()

    # Set the active experiment
    mlflow.set_experiment(experiment_name)

    # Ensure no active run (terminate any existing run)
    if mlflow.active_run():
        mlflow.end_run()

    # Start and return a new run
    return mlflow.start_run()
