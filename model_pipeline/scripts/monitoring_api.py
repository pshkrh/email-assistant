import os
import json
import uuid
import time
import logging
from datetime import datetime
from flask import jsonify, request
import mlflow
from google.cloud import logging as gcp_logging
from performance_monitor import (
    calculate_performance_metrics,
    optimize_prompt_strategies,
    get_current_prompt_strategies,
)
from db_connection import get_db_connection
from config import GCP_PROJECT_ID
from mlflow_config import configure_mlflow

# Initialize GCP Cloud Logging
gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("monitoring_api")

# Configure MLflow
experiment = configure_mlflow()
experiment_id = experiment.experiment_id if experiment else None


def register_monitoring_endpoints(app):
    """
    Register monitoring endpoints with the Flask app.

    Args:
        app: Flask application instance
    """

    @app.route("/check_performance", methods=["GET"])
    def check_performance():
        """
        Manual endpoint to check current performance metrics.
        Returns performance metrics without making any changes.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        gcp_logger.log_struct(
            {"message": "Manual performance check requested", "request_id": request_id},
            severity="INFO",
        )

        try:
            # Calculate performance metrics
            metrics = calculate_performance_metrics()

            if metrics is None:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Failed to calculate performance metrics",
                        }
                    ),
                    500,
                )

            # Get current strategies
            current_strategies = get_current_prompt_strategies()

            # Prepare tasks that need attention
            tasks_below_threshold = [
                task
                for task, task_metrics in metrics.items()
                if task_metrics.get("below_threshold", False)
            ]

            response = {
                "success": True,
                "metrics": metrics,
                "current_strategies": current_strategies,
                "tasks_below_threshold": tasks_below_threshold,
                "timestamp": datetime.now().isoformat(),
            }

            # Log metrics to GCP
            gcp_logger.log_struct(
                {
                    "message": "Performance check completed",
                    "request_id": request_id,
                    "duration_seconds": time.time() - start_time,
                    "tasks_below_threshold": tasks_below_threshold,
                },
                severity="INFO",
            )

            return jsonify(response)

        except Exception as e:
            error_msg = f"Error checking performance: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            return jsonify({"success": False, "message": error_msg}), 500

    @app.route("/optimize_prompts", methods=["POST"])
    def optimize_prompts():
        """
        Manual endpoint to trigger prompt optimization based on performance metrics.
        Will make changes to prompt strategies if performance is below threshold.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        gcp_logger.log_struct(
            {
                "message": "Manual prompt optimization requested",
                "request_id": request_id,
            },
            severity="INFO",
        )

        try:
            # Run optimization process
            result = optimize_prompt_strategies(experiment_id=experiment_id)

            # Log result
            gcp_logger.log_struct(
                {
                    "message": "Prompt optimization completed",
                    "request_id": request_id,
                    "success": result.get("success", False),
                    "duration_seconds": time.time() - start_time,
                    "tasks_updated": [
                        c.get("task") for c in result.get("changes_made", [])
                    ],
                },
                severity="INFO",
            )

            return jsonify(result)

        except Exception as e:
            error_msg = f"Error optimizing prompts: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            return jsonify({"success": False, "message": error_msg}), 500

    @app.route("/scheduled_check", methods=["GET", "POST"])
    def scheduled_check():
        """
        Endpoint for Cloud Scheduler to trigger automated performance checks.
        This endpoint can be called by a Cloud Scheduler job.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        gcp_logger.log_struct(
            {
                "message": "Scheduled performance check triggered",
                "request_id": request_id,
                "method": request.method,
            },
            severity="INFO",
        )

        try:
            # Run the optimization process
            result = optimize_prompt_strategies(experiment_id=experiment_id)

            # Log completion
            gcp_logger.log_struct(
                {
                    "message": "Scheduled check completed",
                    "request_id": request_id,
                    "success": result.get("success", False),
                    "duration_seconds": time.time() - start_time,
                    "tasks_updated": [
                        c.get("task") for c in result.get("changes_made", [])
                    ],
                },
                severity="INFO",
            )

            return jsonify(result)

        except Exception as e:
            error_msg = f"Error in scheduled check: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            return jsonify({"success": False, "message": error_msg}), 500

    @app.route("/get_optimization_history", methods=["GET"])
    def get_optimization_history():
        """
        Retrieve the history of prompt strategy changes.
        """
        request_id = str(uuid.uuid4())

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT 
                            id, task, old_strategy, new_strategy, 
                            change_reason, timestamp
                        FROM prompt_strategy_changes
                        ORDER BY timestamp DESC
                        LIMIT 50
                    """
                    cur.execute(query)
                    changes = cur.fetchall()

            # Convert RealDictRow objects to regular dictionaries
            history = []
            for change in changes:
                change_dict = dict(change)
                # Convert datetime to string for JSON serialization
                change_dict["timestamp"] = change_dict["timestamp"].isoformat()
                history.append(change_dict)

            gcp_logger.log_struct(
                {
                    "message": "Retrieved optimization history",
                    "request_id": request_id,
                    "history_count": len(history),
                },
                severity="INFO",
            )

            return jsonify({"success": True, "history": history})

        except Exception as e:
            error_msg = f"Error retrieving optimization history: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            return jsonify({"success": False, "message": error_msg}), 500


# If run directly, this can be used for testing the functions
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("This module is meant to be imported by the main Flask app.")
    logging.info(
        "Import and call register_monitoring_endpoints(app) to add these endpoints."
    )
