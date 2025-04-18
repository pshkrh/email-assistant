"""
Performance Monitoring Module

This module calculates performance metrics for user tasks based on feedback
and provides functions to optimize prompt strategies based on those metrics.
It handles both global and user-specific performance tracking.
"""

import time
import uuid
import logging
from datetime import datetime, timedelta

import mlflow
from google.cloud import logging as gcp_logging

from db_connection import get_db_connection
from config import GCP_PROJECT_ID
from send_notification import send_email_notification

# Initialize GCP Cloud Logging
gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("performance_monitor")

# Thresholds for prompt optimization
PERFORMANCE_THRESHOLD = 0.7  # 70% positive feedback required
MIN_FEEDBACK_COUNT = 5  # Minimum number of feedback entries to consider
LOOKBACK_DAYS = 30  # Analyze feedback from the last 30 days


def calculate_user_performance_metrics(lookback_days=LOOKBACK_DAYS):
    """
    Calculate performance metrics per user for each task.

    Args:
        lookback_days (int): Number of days to look back for feedback

    Returns:
        dict: Dictionary mapping users to task-specific performance scores
    """
    try:
        user_metrics = {}

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First, get all users who have provided feedback
                cur.execute(
                    """
                    SELECT DISTINCT user_email 
                    FROM user_feedback 
                    WHERE date >= %s
                """,
                    (datetime.now() - timedelta(days=lookback_days),),
                )

                users = [row["user_email"] for row in cur.fetchall()]

                logging.info(f"Found {len(users)} users with feedback")

                # For each user, calculate task-specific metrics
                for user_email in users:
                    user_metrics[user_email] = {}

                    # For each task type, get user-specific feedback metrics
                    for task in ["summary", "action_items", "draft_reply"]:
                        feedback_column = f"{task}_feedback"

                        # Query to get user's feedback metrics
                        query = f"""
                            SELECT 
                                COUNT(*) as total_count,
                                SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END) as positive_count,
                                SUM(CASE WHEN {feedback_column} = 0 THEN 1 ELSE 0 END) as negative_count
                            FROM user_feedback
                            WHERE {feedback_column} IS NOT NULL
                            AND user_email = %s
                            AND date >= %s
                        """

                        cutoff_date = datetime.now() - timedelta(days=lookback_days)
                        cur.execute(query, (user_email, cutoff_date.date()))
                        result = cur.fetchone()

                        # Calculate performance score (percentage of positive feedback)
                        total_count = result["total_count"] if result else 0
                        positive_count = result["positive_count"] if result else 0
                        negative_count = result["negative_count"] if result else 0

                        # Only calculate score if minimum feedback threshold met
                        if total_count >= MIN_FEEDBACK_COUNT:
                            performance_score = (
                                positive_count / total_count if total_count > 0 else 0
                            )
                        else:
                            # Not enough feedback to make a determination
                            performance_score = None

                        # Store metrics
                        user_metrics[user_email][task] = {
                            "total_feedback": total_count,
                            "positive_feedback": positive_count,
                            "negative_feedback": negative_count,
                            "performance_score": performance_score,
                            "below_threshold": (
                                performance_score is not None
                                and performance_score < PERFORMANCE_THRESHOLD
                            ),
                        }

                        # Log metrics
                        score_str = (
                            f"{performance_score:.2f}"
                            if performance_score is not None
                            else "None"
                        )
                        logging.info(
                            f"User {user_email} task {task}: "
                            f"score={score_str}, "
                            f"total={total_count}, positive={positive_count}, "
                            f"below_threshold={user_metrics[user_email][task]['below_threshold']}"
                        )

                        # Log to GCP
                        gcp_logger.log_struct(
                            {
                                "message": f"User performance metrics calculated for {user_email} on {task}",
                                "user_email": user_email,
                                "task": task,
                                "total_feedback": total_count,
                                "positive_feedback": positive_count,
                                "performance_score": performance_score,
                                "below_threshold": user_metrics[user_email][task][
                                    "below_threshold"
                                ],
                                "lookback_days": lookback_days,
                            },
                            severity="INFO",
                        )

        return user_metrics

    except Exception as e:
        # Handle calculation errors
        error_msg = f"Error calculating user performance metrics: {str(e)}"
        gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
        logging.error(error_msg)
        logging.exception(e)  # Log full traceback
        return None


def get_user_prompt_strategies(user_email):
    """
    Retrieve the user-specific prompt strategies from the database.

    Args:
        user_email (str): User email to get strategies for

    Returns:
        dict: Dictionary mapping tasks to strategy types
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get the user-specific prompt strategies
                query = """
                    SELECT 
                        summary_strategy,
                        action_items_strategy,
                        draft_reply_strategy
                    FROM user_prompt_strategies
                    WHERE user_email = %s
                """
                cur.execute(query, (user_email,))
                result = cur.fetchone()

                # Fall back to defaults if no user-specific settings
                if not result:
                    default_strategies = {
                        "summary": "default",
                        "action_items": "default",
                        "draft_reply": "default",
                    }
                    logging.info(
                        f"No strategies found for {user_email}, using defaults"
                    )
                    gcp_logger.log_struct(
                        {
                            "message": f"No user-specific strategies for {user_email}, using default",
                            "user_email": user_email,
                            "strategies": default_strategies,
                        },
                        severity="DEBUG",
                    )
                    return default_strategies

                # Convert database result to dictionary
                strategies = {
                    "summary": result["summary_strategy"] or "default",
                    "action_items": result["action_items_strategy"] or "default",
                    "draft_reply": result["draft_reply_strategy"] or "default",
                }

                logging.info(f"Retrieved strategies for {user_email}: {strategies}")
                gcp_logger.log_struct(
                    {
                        "message": f"Retrieved user-specific prompt strategies for {user_email}",
                        "user_email": user_email,
                        "strategies": strategies,
                    },
                    severity="DEBUG",
                )

                return strategies

    except Exception as e:
        # Handle retrieval errors
        error_msg = f"Error retrieving user prompt strategies: {str(e)}"
        gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
        logging.error(error_msg)
        logging.exception(e)  # Log full traceback

        # Fall back to default strategies
        return {
            "summary": "default",
            "action_items": "default",
            "draft_reply": "default",
        }


def update_prompt_strategy(task, new_strategy, user_email):
    """
    Update the prompt strategy configuration for a user-specific task.

    Args:
        task (str): The task type (summary, action_items, draft_reply)
        new_strategy (str): The new strategy to use (default, alternate)
        user_email (str): User email for user-specific strategy

    Returns:
        dict: Result of the operation
    """
    try:
        logging.info(
            f"Updating prompt strategy for {user_email} on {task} to {new_strategy}"
        )

        # Validate inputs
        if not user_email:
            error_msg = "User email is required for strategy updates"
            gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
            logging.error(error_msg)
            return {"success": False, "message": error_msg}

        # Map task names to database column names
        column_mapping = {
            "summary": "summary_strategy",
            "action_items": "action_items_strategy",
            "draft_reply": "draft_reply_strategy",
        }

        # Validate task type
        if task not in column_mapping:
            error_msg = f"Invalid task type: {task}"
            gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
            logging.error(error_msg)
            return {"success": False, "message": error_msg}

        db_column = column_mapping[task]

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get current strategy first
                current_strategies = get_user_prompt_strategies(user_email)
                old_strategy = current_strategies.get(task, "default")

                # Check if user exists in user_prompt_strategies table
                cur.execute(
                    "SELECT COUNT(*) as count FROM user_prompt_strategies WHERE user_email = %s",
                    (user_email,),
                )
                user_exists = cur.fetchone()["count"] > 0
                logging.info(
                    f"User {user_email} exists in strategies table: {user_exists}"
                )

                if user_exists:
                    # Update existing user strategy
                    query = f"""
                        UPDATE user_prompt_strategies 
                        SET {db_column} = %s,
                        last_updated = %s
                        WHERE user_email = %s
                    """
                    logging.info(f"Executing update query: {query}")
                    cur.execute(query, (new_strategy, datetime.now(), user_email))
                    logging.info(f"Updated {cur.rowcount} rows")
                else:
                    # Insert new user strategy record
                    summary_strategy = new_strategy if task == "summary" else "default"
                    action_items_strategy = (
                        new_strategy if task == "action_items" else "default"
                    )
                    draft_reply_strategy = (
                        new_strategy if task == "draft_reply" else "default"
                    )

                    query = """
                        INSERT INTO user_prompt_strategies (
                            user_email, summary_strategy, action_items_strategy, 
                            draft_reply_strategy, last_updated
                        ) VALUES (%s, %s, %s, %s, %s)
                    """
                    logging.info(f"Executing insert query: {query}")
                    cur.execute(
                        query,
                        (
                            user_email,
                            summary_strategy,
                            action_items_strategy,
                            draft_reply_strategy,
                            datetime.now(),
                        ),
                    )
                    logging.info(f"Inserted {cur.rowcount} rows")

                change_reason = f"User performance below threshold for {task}"

                # Create a change record in our prompt_strategy_changes table
                query = """
                    INSERT INTO prompt_strategy_changes (
                        task, old_strategy, new_strategy, change_reason, 
                        timestamp, user_email
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                logging.info(f"Executing change record insertion: {query}")
                cur.execute(
                    query,
                    (
                        task,
                        old_strategy,
                        new_strategy,
                        change_reason,
                        datetime.now(),
                        user_email,
                    ),
                )

                change_id = cur.fetchone()["id"]
                logging.info(f"Created change record with ID: {change_id}")
                conn.commit()
                logging.info("Transaction committed")

        # Log the update
        gcp_logger.log_struct(
            {
                "message": f"Updated user-specific prompt strategy for {user_email} on {task}",
                "task": task,
                "old_strategy": old_strategy,
                "new_strategy": new_strategy,
                "user_email": user_email,
                "change_id": change_id,
            },
            severity="INFO",
        )

        return {
            "success": True,
            "message": f"Updated user-specific prompt strategy for {user_email} on {task} from {old_strategy} to {new_strategy}",
            "change_id": change_id,
        }

    except Exception as e:
        # Handle update errors
        error_msg = f"Error updating prompt strategy for {task}: {str(e)}"
        gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
        logging.error(error_msg)
        logging.exception(e)  # Log full traceback
        return {"success": False, "message": error_msg}


def optimize_user_prompt_strategies(user_metrics=None, experiment_id=None):
    """
    Analyze user performance metrics and optimize prompt strategies where needed.

    Args:
        user_metrics (dict, optional): User performance metrics (calculated if None)
        experiment_id (str, optional): MLflow experiment ID for logging

    Returns:
        dict: Results of the optimization process
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    logging.info(f"Starting user prompt optimization (request ID: {request_id})")

    # Use MLflow if an experiment ID is provided
    if experiment_id:
        with mlflow.start_run(
            experiment_id=experiment_id, run_name=f"optimize_prompts_{request_id}"
        ):
            return _run_optimization(user_metrics, request_id, experiment_id)
    else:
        return _run_optimization(user_metrics, request_id)


def _run_optimization(user_metrics=None, request_id=None, experiment_id=None):
    """
    Internal function to run the optimization process.

    Args:
        user_metrics (dict, optional): User performance metrics
        request_id (str, optional): Request ID for correlation
        experiment_id (str, optional): MLflow experiment ID

    Returns:
        dict: Optimization results
    """
    try:
        # Calculate user metrics if not provided
        if user_metrics is None:
            logging.info("No metrics provided, calculating user metrics")
            user_metrics = calculate_user_performance_metrics()

        # Validate metrics
        if not user_metrics:
            error_msg = "Failed to calculate user performance metrics or no users found"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            logging.error(error_msg)
            return {"success": False, "message": error_msg}

        logging.info(f"Found metrics for {len(user_metrics)} users")

        # Log metrics to MLflow if available
        if experiment_id:
            for user_email, user_task_metrics in user_metrics.items():
                for task, task_metrics in user_task_metrics.items():
                    if task_metrics["performance_score"] is not None:
                        mlflow.log_metric(
                            f"{user_email}_{task}_score",
                            task_metrics["performance_score"],
                        )

        # Track changes
        user_changes = []
        users_below_threshold = {}

        # Check user-specific metrics and optimize if needed
        for user_email, user_task_metrics in user_metrics.items():
            users_below_threshold[user_email] = []
            logging.info(f"Processing user: {user_email}")

            # Get current user strategies
            user_strategies = get_user_prompt_strategies(user_email)

            # Log the user strategies
            logging.info(f"Current strategies for {user_email}: {user_strategies}")

            for task, metrics in user_task_metrics.items():
                # Check if the performance score is available and below threshold
                if metrics.get("performance_score") is not None and metrics.get(
                    "below_threshold", False
                ):
                    users_below_threshold[user_email].append(task)
                    logging.info(f"User {user_email} task {task} is below threshold")

                    # Only change if we're not already using alternate strategy
                    current_strategy = user_strategies.get(task, "default")

                    logging.info(
                        f"Current strategy for {user_email} on {task}: {current_strategy}"
                    )

                    if current_strategy == "default":
                        # Switch to alternate strategy for this user
                        logging.info(
                            f"Updating strategy for {user_email} on {task} to alternate"
                        )
                        result = update_prompt_strategy(task, "alternate", user_email)

                        logging.info(f"Update result: {result}")

                        if result.get("success", False):
                            user_changes.append(
                                {
                                    "user_email": user_email,
                                    "task": task,
                                    "old_strategy": current_strategy,
                                    "new_strategy": "alternate",
                                    "performance_score": metrics.get(
                                        "performance_score"
                                    ),
                                    "change_id": result.get("change_id"),
                                }
                            )

                            gcp_logger.log_struct(
                                {
                                    "message": f"Successfully optimized user-specific prompt for {user_email} on {task}",
                                    "request_id": request_id,
                                    "user_email": user_email,
                                    "task": task,
                                    "performance_score": metrics.get(
                                        "performance_score"
                                    ),
                                    "threshold": PERFORMANCE_THRESHOLD,
                                },
                                severity="INFO",
                            )
                        else:
                            logging.error(
                                f"Failed to update strategy: {result.get('message')}"
                            )
                            gcp_logger.log_struct(
                                {
                                    "message": f"Failed to update strategy for {user_email} on {task}: {result.get('message')}",
                                    "request_id": request_id,
                                    "user_email": user_email,
                                    "task": task,
                                },
                                severity="ERROR",
                            )
                    else:
                        # Already using alternate strategy
                        logging.info(
                            f"User {user_email} task {task} already using {current_strategy}"
                        )
                        gcp_logger.log_struct(
                            {
                                "message": f"User {user_email} task {task} below threshold but already using alternate strategy",
                                "request_id": request_id,
                                "user_email": user_email,
                                "task": task,
                                "performance_score": metrics.get("performance_score"),
                                "current_strategy": current_strategy,
                            },
                            severity="INFO",
                        )

            # Clean up empty task lists
            if not users_below_threshold[user_email]:
                logging.info(
                    f"No tasks below threshold for {user_email}, removing from report"
                )
                del users_below_threshold[user_email]

        # Send notification if any users had tasks below threshold
        if users_below_threshold:
            notification_message = []

            user_notifications = []
            for user, tasks in users_below_threshold.items():
                user_notifications.append(f"{user}: {', '.join(tasks)}")

            notification_message.append(
                f"User-specific performance below threshold for: {'; '.join(user_notifications)}. "
                f"User-specific prompt strategies updated for {len(user_changes)} cases."
            )

            # Log notification message
            gcp_logger.log_struct(
                {
                    "message": "Sending performance notification",
                    "request_id": request_id,
                    "notification": "\n".join(notification_message),
                },
                severity="INFO",
            )

            # In production, uncomment to send actual notifications
            # send_email_notification(
            #     "Performance Alert",
            #     "\n".join(notification_message),
            #     request_id
            # )

        # Prepare result
        logging.info(f"Optimization completed with {len(user_changes)} changes")
        result = {
            "success": True,
            "user_metrics": user_metrics,
            "users_below_threshold": users_below_threshold,
            "user_changes": user_changes,
            "timestamp": datetime.now().isoformat(),
        }

        if experiment_id:
            mlflow.log_dict(result, "optimization_result.json")

        return result

    except Exception as e:
        # Handle optimization errors
        error_msg = f"Error in prompt optimization: {str(e)}"
        gcp_logger.log_struct(
            {"message": error_msg, "request_id": request_id},
            severity="ERROR",
        )
        logging.error(error_msg)
        logging.exception(e)  # Log full traceback

        if experiment_id:
            mlflow.log_param("error", str(e))

        return {"success": False, "message": error_msg}


# If run directly, execute the optimization process
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logging.info("Starting optimization process")
    result = optimize_user_prompt_strategies()
    logging.info(f"Optimization result: {result}")
