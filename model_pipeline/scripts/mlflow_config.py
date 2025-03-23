import os
import mlflow
from config import MLFLOW_LOG_DIR
from config import MLFLOW_EXPERIMENT_NAME


def configure_mlflow(log_dir=MLFLOW_LOG_DIR):
    os.makedirs(log_dir, exist_ok=True)
    mlflow.set_tracking_uri(log_dir)


def start_experiment(experiment_name=MLFLOW_EXPERIMENT_NAME):
    configure_mlflow()
    mlflow.set_experiment(experiment_name)
