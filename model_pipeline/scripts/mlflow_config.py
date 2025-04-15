import os
import mlflow
from config import MLFLOW_LOG_DIR, MLFLOW_EXPERIMENT_NAME


def configure_mlflow(log_dir=MLFLOW_LOG_DIR):
    """Configure MLflow with tracking URI."""
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"file://{log_dir}")
    if tracking_uri.startswith("file://"):
        os.makedirs(log_dir, exist_ok=True)
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
    """Start an MLflow experiment."""
    configure_mlflow()
    mlflow.set_experiment(experiment_name)
    # Ensure no active run
    if mlflow.active_run():
        mlflow.end_run()
    return mlflow.start_run()
