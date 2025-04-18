"""
Monitoring API Module

This module implements API endpoints for monitoring and optimizing prompt strategies
based on user feedback. It provides endpoints for checking performance metrics,
triggering optimization, and viewing optimization history.
"""

import uuid
import time
import logging
from datetime import datetime

from flask import jsonify, request
from google.cloud import logging as gcp_logging

from performance_monitor import (
    calculate_user_performance_metrics,
    get_user_prompt_strategies,
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

    This function adds performance monitoring and prompt optimization
    endpoints to the provided Flask application.

    Args:
        app: Flask application instance
    """

    @app.route("/check_performance", methods=["GET"])
    def check_performance():
        """
        Check current performance metrics without making changes.

        Endpoint to check performance metrics globally or for a specific user.

        Returns:
            Response: JSON with performance metrics
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        gcp_logger.log_struct(
            {"message": "Manual performance check requested", "request_id": request_id},
            severity="INFO",
        )

        try:
            # Get user_email from query parameter (if provided)
            user_email = request.args.get("user_email")

            # Get metrics based on scope (specific user or all users)
            if user_email:
                # Get metrics for a specific user
                user_metrics = {}
                all_user_metrics = calculate_user_performance_metrics()
                if all_user_metrics and user_email in all_user_metrics:
                    user_metrics[user_email] = all_user_metrics[user_email]
            else:
                # Get metrics for all users
                user_metrics = calculate_user_performance_metrics()

            # Handle calculation failure
            if not user_metrics:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Failed to calculate performance metrics",
                        }
                    ),
                    500,
                )

            # Identify users/tasks below threshold
            users_below_threshold = {}
            if user_metrics:
                for email, tasks in user_metrics.items():
                    below_threshold_tasks = [
                        task
                        for task, task_metrics in tasks.items()
                        if task_metrics.get("below_threshold", False)
                    ]
                    if below_threshold_tasks:
                        users_below_threshold[email] = below_threshold_tasks

            # Get user-specific strategies
            user_strategies = {}
            if user_email:
                user_strategies[user_email] = get_user_prompt_strategies(user_email)
            elif user_metrics:
                for email in user_metrics.keys():
                    user_strategies[email] = get_user_prompt_strategies(email)

            # Prepare response
            response = {
                "success": True,
                "user_metrics": user_metrics,
                "user_strategies": user_strategies,
                "users_below_threshold": users_below_threshold,
                "timestamp": datetime.now().isoformat(),
            }

            # Log completion
            gcp_logger.log_struct(
                {
                    "message": "Performance check completed",
                    "request_id": request_id,
                    "duration_seconds": time.time() - start_time,
                    "users_below_threshold": len(users_below_threshold),
                },
                severity="INFO",
            )

            return jsonify(response)

        except Exception as e:
            # Handle errors
            error_msg = f"Error checking performance: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            logging.error(error_msg)
            logging.exception(e)
            return jsonify({"success": False, "message": error_msg}), 500

    @app.route("/optimize_prompts", methods=["POST"])
    def optimize_prompts():
        """
        Trigger prompt optimization based on performance metrics.

        Endpoint to optimize prompt strategies for users with below-threshold performance.
        Can be targeted to a specific user or all users.

        Returns:
            Response: JSON with optimization results
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
            # Check if optimization is for a specific user
            data = request.get_json() or {}
            user_email = data.get("user_email")
            logging.info(
                f"Optimizing prompts for {'specific user: ' + user_email if user_email else 'all users'}"
            )

            # Track changes made during optimization
            changes_made = []
            users_below_threshold = {}

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # For each task type, find users with below-threshold performance
                    for task in ["summary", "action_items", "draft_reply"]:
                        feedback_column = f"{task}_feedback"

                        # Query based on optimization scope
                        if user_email:
                            # Specific user query
                            query = f"""
                                SELECT 
                                    user_email,
                                    COUNT(*) as total,
                                    SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END) as positive
                                FROM user_feedback
                                WHERE {feedback_column} IS NOT NULL AND user_email = %s
                                GROUP BY user_email
                                HAVING COUNT(*) >= 5 
                                AND (SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END)::float / COUNT(*)) < 0.7
                            """
                            cur.execute(query, (user_email,))
                        else:
                            # All users query
                            query = f"""
                                SELECT 
                                    user_email,
                                    COUNT(*) as total,
                                    SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END) as positive
                                FROM user_feedback
                                WHERE {feedback_column} IS NOT NULL
                                GROUP BY user_email
                                HAVING COUNT(*) >= 5 
                                AND (SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END)::float / COUNT(*)) < 0.7
                            """
                            cur.execute(query)

                        # Process users with low performance
                        users_with_low_performance = cur.fetchall()
                        logging.info(
                            f"Found {len(users_with_low_performance)} users with low performance on {task}"
                        )

                        for user_record in users_with_low_performance:
                            curr_user_email = user_record["user_email"]

                            # Add to users below threshold
                            if curr_user_email not in users_below_threshold:
                                users_below_threshold[curr_user_email] = []
                            users_below_threshold[curr_user_email].append(task)

                            # Get current strategy
                            column_name = f"{task}_strategy"
                            cur.execute(
                                f"SELECT {column_name} FROM user_prompt_strategies WHERE user_email = %s",
                                (curr_user_email,),
                            )
                            result = cur.fetchone()
                            current_strategy = (
                                result[column_name] if result else "default"
                            )

                            # Only update if current strategy is default
                            if current_strategy == "default":
                                logging.info(
                                    f"Updating {task} strategy for {curr_user_email}"
                                )

                                # Update strategy
                                if result:  # User exists in user_prompt_strategies
                                    cur.execute(
                                        f"UPDATE user_prompt_strategies SET {column_name} = %s, last_updated = %s WHERE user_email = %s",
                                        ("alternate", datetime.now(), curr_user_email),
                                    )
                                else:  # Insert new record
                                    summary_val = (
                                        "alternate" if task == "summary" else "default"
                                    )
                                    action_items_val = (
                                        "alternate"
                                        if task == "action_items"
                                        else "default"
                                    )
                                    draft_reply_val = (
                                        "alternate"
                                        if task == "draft_reply"
                                        else "default"
                                    )

                                    cur.execute(
                                        """
                                        INSERT INTO user_prompt_strategies 
                                        (user_email, summary_strategy, action_items_strategy, draft_reply_strategy, last_updated)
                                        VALUES (%s, %s, %s, %s, %s)
                                        """,
                                        (
                                            curr_user_email,
                                            summary_val,
                                            action_items_val,
                                            draft_reply_val,
                                            datetime.now(),
                                        ),
                                    )

                                # Record change
                                cur.execute(
                                    """
                                    INSERT INTO prompt_strategy_changes
                                    (task, old_strategy, new_strategy, change_reason, timestamp, user_email)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    RETURNING id
                                    """,
                                    (
                                        task,
                                        "default",
                                        "alternate",
                                        "Performance below threshold",
                                        datetime.now(),
                                        curr_user_email,
                                    ),
                                )

                                change_id = cur.fetchone()["id"]
                                changes_made.append(
                                    {
                                        "user_email": curr_user_email,
                                        "task": task,
                                        "old_strategy": "default",
                                        "new_strategy": "alternate",
                                        "performance_score": user_record["positive"]
                                        / user_record["total"],
                                        "change_id": change_id,
                                    }
                                )

                    # Commit all changes
                    conn.commit()

            # Prepare response
            logging.info(f"Optimization completed with {len(changes_made)} changes")
            result = {
                "success": True,
                "users_below_threshold": users_below_threshold,
                "user_changes": changes_made,
                "timestamp": datetime.now().isoformat(),
            }

            # Log completion
            gcp_logger.log_struct(
                {
                    "message": "Prompt optimization completed",
                    "request_id": request_id,
                    "success": True,
                    "duration_seconds": time.time() - start_time,
                    "user_tasks_updated": len(changes_made),
                },
                severity="INFO",
            )

            return jsonify(result)

        except Exception as e:
            # Handle errors
            error_msg = f"Error optimizing prompts: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            logging.error(error_msg)
            logging.exception(e)
            return jsonify({"success": False, "message": error_msg}), 500

    @app.route("/scheduled_check", methods=["GET", "POST"])
    def scheduled_check():
        """
        Endpoint for Cloud Scheduler to trigger automated performance checks.

        This endpoint runs performance checks and optimizes strategies automatically.
        Intended to be called by a Cloud Scheduler job on a regular schedule.

        Returns:
            Response: JSON with check results
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
            # Track changes made during optimization
            changes_made = []
            users_below_threshold = {}

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # For each task type, find users with below-threshold performance
                    for task in ["summary", "action_items", "draft_reply"]:
                        feedback_column = f"{task}_feedback"

                        # Query for users with low performance across all users
                        query = f"""
                            SELECT 
                                user_email,
                                COUNT(*) as total,
                                SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END) as positive
                            FROM user_feedback
                            WHERE {feedback_column} IS NOT NULL
                            GROUP BY user_email
                            HAVING COUNT(*) >= 5 
                            AND (SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END)::float / COUNT(*)) < 0.7
                        """
                        cur.execute(query)

                        # Process users with low performance
                        users_with_low_performance = cur.fetchall()
                        logging.info(
                            f"Found {len(users_with_low_performance)} users with low performance on {task}"
                        )

                        for user_record in users_with_low_performance:
                            curr_user_email = user_record["user_email"]

                            # Add to users below threshold
                            if curr_user_email not in users_below_threshold:
                                users_below_threshold[curr_user_email] = []
                            users_below_threshold[curr_user_email].append(task)

                            # Get current strategy
                            column_name = f"{task}_strategy"
                            cur.execute(
                                f"SELECT {column_name} FROM user_prompt_strategies WHERE user_email = %s",
                                (curr_user_email,),
                            )
                            result = cur.fetchone()
                            current_strategy = (
                                result[column_name] if result else "default"
                            )

                            # Only update if current strategy is default
                            if current_strategy == "default":
                                logging.info(
                                    f"Updating {task} strategy for {curr_user_email}"
                                )

                                # Update strategy
                                if result:  # User exists in user_prompt_strategies
                                    cur.execute(
                                        f"UPDATE user_prompt_strategies SET {column_name} = %s, last_updated = %s WHERE user_email = %s",
                                        ("alternate", datetime.now(), curr_user_email),
                                    )
                                else:  # Insert new record
                                    summary_val = (
                                        "alternate" if task == "summary" else "default"
                                    )
                                    action_items_val = (
                                        "alternate"
                                        if task == "action_items"
                                        else "default"
                                    )
                                    draft_reply_val = (
                                        "alternate"
                                        if task == "draft_reply"
                                        else "default"
                                    )

                                    cur.execute(
                                        """
                                        INSERT INTO user_prompt_strategies 
                                        (user_email, summary_strategy, action_items_strategy, draft_reply_strategy, last_updated)
                                        VALUES (%s, %s, %s, %s, %s)
                                        """,
                                        (
                                            curr_user_email,
                                            summary_val,
                                            action_items_val,
                                            draft_reply_val,
                                            datetime.now(),
                                        ),
                                    )

                                # Record change
                                cur.execute(
                                    """
                                    INSERT INTO prompt_strategy_changes
                                    (task, old_strategy, new_strategy, change_reason, timestamp, user_email)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    RETURNING id
                                    """,
                                    (
                                        task,
                                        "default",
                                        "alternate",
                                        "Scheduled optimization",
                                        datetime.now(),
                                        curr_user_email,
                                    ),
                                )

                                change_id = cur.fetchone()["id"]
                                changes_made.append(
                                    {
                                        "user_email": curr_user_email,
                                        "task": task,
                                        "old_strategy": "default",
                                        "new_strategy": "alternate",
                                        "performance_score": user_record["positive"]
                                        / user_record["total"],
                                        "change_id": change_id,
                                    }
                                )

                    # Commit all changes
                    conn.commit()

            # Prepare response
            logging.info(
                f"Scheduled optimization completed with {len(changes_made)} changes"
            )
            result = {
                "success": True,
                "users_below_threshold": users_below_threshold,
                "user_changes": changes_made,
                "timestamp": datetime.now().isoformat(),
            }

            # Log completion
            gcp_logger.log_struct(
                {
                    "message": "Scheduled check completed",
                    "request_id": request_id,
                    "success": True,
                    "duration_seconds": time.time() - start_time,
                    "user_tasks_updated": len(changes_made),
                },
                severity="INFO",
            )

            return jsonify(result)

        except Exception as e:
            # Handle errors
            error_msg = f"Error in scheduled check: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            logging.error(error_msg)
            logging.exception(e)
            return jsonify({"success": False, "message": error_msg}), 500

    @app.route("/get_optimization_history", methods=["GET"])
    def get_optimization_history():
        """
        Retrieve the history of prompt strategy changes.

        Endpoint to get history of strategy changes, optionally filtered by user.

        Returns:
            Response: JSON with optimization history
        """
        request_id = str(uuid.uuid4())
        user_email = request.args.get("user_email")

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    if user_email:
                        # Get user-specific history
                        query = """
                            SELECT 
                                id, task, old_strategy, new_strategy, 
                                change_reason, timestamp, user_email
                            FROM prompt_strategy_changes
                            WHERE user_email = %s
                            ORDER BY timestamp DESC
                            LIMIT 50
                        """
                        cur.execute(query, (user_email,))
                    else:
                        # Get all history
                        query = """
                            SELECT 
                                id, task, old_strategy, new_strategy, 
                                change_reason, timestamp, user_email
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
                # Add scope for clarity
                change_dict["scope"] = "user-specific"
                history.append(change_dict)

            # Log completion
            gcp_logger.log_struct(
                {
                    "message": "Retrieved optimization history",
                    "request_id": request_id,
                    "history_count": len(history),
                    "user_email": user_email or "all",
                },
                severity="INFO",
            )

            return jsonify({"success": True, "history": history})

        except Exception as e:
            # Handle errors
            error_msg = f"Error retrieving optimization history: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            logging.error(error_msg)
            logging.exception(e)
            return jsonify({"success": False, "message": error_msg}), 500

    @app.route("/get_user_strategies", methods=["GET"])
    def get_user_strategies():
        """
        Retrieve the current prompt strategies for a specific user.

        Endpoint to get a user's current strategy settings.

        Returns:
            Response: JSON with user strategies
        """
        request_id = str(uuid.uuid4())
        user_email = request.args.get("user_email")

        if not user_email:
            return jsonify({"success": False, "message": "User email is required"}), 400

        try:
            # Get strategies from database helper
            strategies = get_user_prompt_strategies(user_email)

            # Log completion
            gcp_logger.log_struct(
                {
                    "message": f"Retrieved user strategies for {user_email}",
                    "request_id": request_id,
                    "user_email": user_email,
                    "strategies": strategies,
                },
                severity="INFO",
            )

            return jsonify(
                {"success": True, "user_email": user_email, "strategies": strategies}
            )

        except Exception as e:
            # Handle errors
            error_msg = f"Error retrieving user strategies: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            logging.error(error_msg)
            logging.exception(e)
            return jsonify({"success": False, "message": error_msg}), 500


# If run directly, this can be used for testing the functions
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("This module is meant to be imported by the main Flask app.")
    logging.info(
        "Import and call register_monitoring_endpoints(app) to add these endpoints."
    )
