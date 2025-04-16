import os
import time
import uuid
import mlflow
import logging
from datetime import datetime, timedelta
from google.cloud import logging as gcp_logging
from db_connection import get_db_connection
from load_prompts import load_prompts
from config import GCP_PROJECT_ID
from send_notification import send_email_notification

# Initialize GCP Cloud Logging
gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("performance_monitor")

# Thresholds for prompt optimization
PERFORMANCE_THRESHOLD = 0.7  # 70% positive feedback required
MIN_FEEDBACK_COUNT = (
    5  # Minimum number of feedback entries to consider (reduced for demo)
)
LOOKBACK_DAYS = 30  # Analyze feedback from the last 30 days (increased for demo)


def calculate_performance_metrics(lookback_days=LOOKBACK_DAYS):
    """
    Calculate performance metrics from recent feedback.
    Returns a dictionary with performance scores for each task.
    """
    try:
        metrics = {}

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # For each task type, get feedback metrics
                for task in ["summary", "action_items", "draft_reply"]:
                    feedback_column = f"{task}_feedback"

                    # Query to get feedback metrics for the last N days
                    query = f"""
                        SELECT 
                            COUNT(*) as total_count,
                            SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END) as positive_count,
                            SUM(CASE WHEN {feedback_column} = 0 THEN 1 ELSE 0 END) as negative_count
                        FROM user_feedback
                        WHERE {feedback_column} IS NOT NULL
                        AND date >= %s
                    """

                    cutoff_date = datetime.now() - timedelta(days=lookback_days)
                    cur.execute(query, (cutoff_date.date(),))
                    result = cur.fetchone()

                    # Calculate performance score (percentage of positive feedback)
                    total_count = result["total_count"] if result else 0
                    positive_count = result["positive_count"] if result else 0
                    negative_count = result["negative_count"] if result else 0

                    if total_count >= MIN_FEEDBACK_COUNT:
                        performance_score = (
                            positive_count / total_count if total_count > 0 else 0
                        )
                    else:
                        # Not enough feedback to make a determination
                        performance_score = None

                    metrics[task] = {
                        "total_feedback": total_count,
                        "positive_feedback": positive_count,
                        "negative_feedback": negative_count,
                        "performance_score": performance_score,
                        "below_threshold": (
                            performance_score is not None
                            and performance_score < PERFORMANCE_THRESHOLD
                        ),
                    }

                    # Get recent trends (last 7 days vs previous 7 days)
                    if total_count >= MIN_FEEDBACK_COUNT:
                        # Get data for last 7 days
                        recent_cutoff = datetime.now() - timedelta(days=7)

                        query = f"""
                            SELECT 
                                COUNT(*) as total_count,
                                SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END) as positive_count
                            FROM user_feedback
                            WHERE {feedback_column} IS NOT NULL
                            AND date >= %s
                        """

                        cur.execute(query, (recent_cutoff.date(),))
                        recent_result = cur.fetchone()

                        recent_total = (
                            recent_result["total_count"] if recent_result else 0
                        )
                        recent_positive = (
                            recent_result["positive_count"] if recent_result else 0
                        )

                        # Get data for previous 7 days
                        prev_start = datetime.now() - timedelta(days=14)
                        prev_end = datetime.now() - timedelta(days=7)

                        query = f"""
                            SELECT 
                                COUNT(*) as total_count,
                                SUM(CASE WHEN {feedback_column} = 1 THEN 1 ELSE 0 END) as positive_count
                            FROM user_feedback
                            WHERE {feedback_column} IS NOT NULL
                            AND date >= %s AND date < %s
                        """

                        cur.execute(query, (prev_start.date(), prev_end.date()))
                        prev_result = cur.fetchone()

                        prev_total = prev_result["total_count"] if prev_result else 0
                        prev_positive = (
                            prev_result["positive_count"] if prev_result else 0
                        )

                        # Calculate trend
                        recent_score = (
                            recent_positive / recent_total if recent_total > 0 else 0
                        )
                        prev_score = prev_positive / prev_total if prev_total > 0 else 0

                        trend = (
                            recent_score - prev_score
                            if prev_total >= MIN_FEEDBACK_COUNT
                            else None
                        )

                        metrics[task]["recent_score"] = recent_score
                        metrics[task]["previous_score"] = prev_score
                        metrics[task]["trend"] = trend
                        metrics[task]["trend_direction"] = (
                            "improving"
                            if trend and trend > 0.05
                            else "declining" if trend and trend < -0.05 else "stable"
                        )

                    # Log to GCP
                    gcp_logger.log_struct(
                        {
                            "message": f"Performance metrics calculated for {task}",
                            "task": task,
                            "total_feedback": total_count,
                            "positive_feedback": positive_count,
                            "performance_score": performance_score,
                            "below_threshold": metrics[task]["below_threshold"],
                            "lookback_days": lookback_days,
                        },
                        severity="INFO",
                    )

        return metrics

    except Exception as e:
        error_msg = f"Error calculating performance metrics: {str(e)}"
        gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
        logging.error(error_msg)
        return None


def get_current_prompt_strategies():
    """
    Retrieve the current prompt strategies for each task type.
    Returns a dictionary mapping task types to their current strategy.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get the latest prompt strategies used
                query = """
                    SELECT 
                        prompt_strategy_summary as summary,
                        prompt_strategy_action_items as action_items,
                        prompt_strategy_draft_reply as draft_reply
                    FROM user_feedback
                    ORDER BY id DESC
                    LIMIT 1
                """
                cur.execute(query)
                result = cur.fetchone()

                if not result:
                    # Default to "default" strategy if no records found
                    return {
                        "summary": "default",
                        "action_items": "default",
                        "draft_reply": "default",
                    }

                strategies = {
                    "summary": result["summary"] or "default",
                    "action_items": result["action_items"] or "default",
                    "draft_reply": result["draft_reply"] or "default",
                }

                gcp_logger.log_struct(
                    {
                        "message": "Retrieved current prompt strategies",
                        "strategies": strategies,
                    },
                    severity="DEBUG",
                )

                return strategies

    except Exception as e:
        error_msg = f"Error retrieving current prompt strategies: {str(e)}"
        gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
        logging.error(error_msg)
        return {
            "summary": "default",
            "action_items": "default",
            "draft_reply": "default",
        }


def update_prompt_strategy(task, new_strategy):
    """
    Update the prompt strategy configuration for a task.

    Args:
        task (str): The task type (summary, action_items, draft_reply)
        new_strategy (str): The new strategy to use (default, alternate)

    Returns:
        dict: Result of the operation
    """
    try:
        # Map task names to database column names
        column_mapping = {
            "summary": "prompt_strategy_summary",
            "action_items": "prompt_strategy_action_items",
            "draft_reply": "prompt_strategy_draft_reply",
        }

        if task not in column_mapping:
            error_msg = f"Invalid task type: {task}"
            gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
            return {"success": False, "message": error_msg}

        # Create a change record in our prompt_strategy_changes table
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First, insert a record into the prompt_strategy_changes table
                query = """
                    INSERT INTO prompt_strategy_changes (
                        task, old_strategy, new_strategy, change_reason, timestamp
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """

                # Get current strategy first
                current_strategies = get_current_prompt_strategies()
                old_strategy = current_strategies.get(task, "default")

                cur.execute(
                    query,
                    (
                        task,
                        old_strategy,
                        new_strategy,
                        "Performance below threshold",
                        datetime.now(),
                    ),
                )

                change_id = cur.fetchone()["id"]
                conn.commit()

        gcp_logger.log_struct(
            {
                "message": f"Updated prompt strategy for {task}",
                "task": task,
                "old_strategy": old_strategy,
                "new_strategy": new_strategy,
                "change_id": change_id,
            },
            severity="INFO",
        )

        return {
            "success": True,
            "message": f"Updated prompt strategy for {task} from {old_strategy} to {new_strategy}",
            "change_id": change_id,
        }

    except Exception as e:
        error_msg = f"Error updating prompt strategy for {task}: {str(e)}"
        gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
        logging.error(error_msg)
        return {"success": False, "message": error_msg}


def optimize_prompt_strategies(metrics=None, experiment_id=None):
    """
    Analyze performance metrics and optimize prompt strategies where needed.

    Args:
        metrics (dict, optional): Performance metrics. If None, calculates them.
        experiment_id (str, optional): MLflow experiment ID for logging.

    Returns:
        dict: Results of the optimization process.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Use MLflow if an experiment ID is provided
    if experiment_id:
        with mlflow.start_run(
            experiment_id=experiment_id, run_name=f"optimize_prompts_{request_id}"
        ):
            return _run_optimization(metrics, request_id, experiment_id)
    else:
        return _run_optimization(metrics, request_id)


def _run_optimization(metrics=None, request_id=None, experiment_id=None):
    """Internal function to run the optimization process."""
    try:
        # Calculate metrics if not provided
        if metrics is None:
            metrics = calculate_performance_metrics()

        if metrics is None:
            error_msg = "Failed to calculate performance metrics"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            return {"success": False, "message": error_msg}

        # Log metrics to MLflow if available
        if experiment_id:
            for task, task_metrics in metrics.items():
                if task_metrics["performance_score"] is not None:
                    mlflow.log_metric(
                        f"{task}_performance_score", task_metrics["performance_score"]
                    )

        # Get current strategies
        current_strategies = get_current_prompt_strategies()

        # Track changes
        changes_made = []
        tasks_below_threshold = []

        # Check each task and optimize if needed
        for task, task_metrics in metrics.items():
            if task_metrics["below_threshold"]:
                tasks_below_threshold.append(task)

                # Only change strategy if we're not already using alternate
                current_strategy = current_strategies.get(task, "default")

                if current_strategy == "default":
                    # Switch to alternate strategy
                    result = update_prompt_strategy(task, "alternate")
                    changes_made.append(
                        {
                            "task": task,
                            "old_strategy": current_strategy,
                            "new_strategy": "alternate",
                            "performance_score": task_metrics["performance_score"],
                            "change_id": (
                                result.get("change_id") if result["success"] else None
                            ),
                        }
                    )

                    gcp_logger.log_struct(
                        {
                            "message": f"Optimized prompt for {task}: switching to alternate strategy",
                            "request_id": request_id,
                            "task": task,
                            "performance_score": task_metrics["performance_score"],
                            "threshold": PERFORMANCE_THRESHOLD,
                        },
                        severity="INFO",
                    )
                else:
                    # Already using alternate strategy
                    gcp_logger.log_struct(
                        {
                            "message": f"Task {task} below threshold but already using alternate strategy",
                            "request_id": request_id,
                            "task": task,
                            "performance_score": task_metrics["performance_score"],
                            "current_strategy": current_strategy,
                        },
                        severity="INFO",
                    )

        # Send notification if any tasks were below threshold
        if tasks_below_threshold:
            notification_message = (
                f"Performance below threshold for tasks: {', '.join(tasks_below_threshold)}. "
                f"Prompt strategies updated for: {', '.join([c['task'] for c in changes_made])}"
            )

            # Log notification message
            gcp_logger.log_struct(
                {
                    "message": "Sending performance notification",
                    "request_id": request_id,
                    "notification": notification_message,
                },
                severity="INFO",
            )

            # In a production system, you would uncomment this to send actual email notifications
            # send_email_notification(
            #     "Performance Alert",
            #     notification_message,
            #     request_id
            # )

        # Log result
        result = {
            "success": True,
            "metrics": metrics,
            "tasks_below_threshold": tasks_below_threshold,
            "changes_made": changes_made,
            "timestamp": datetime.now().isoformat(),
        }

        if experiment_id:
            mlflow.log_dict(result, "optimization_result.json")

        return result

    except Exception as e:
        error_msg = f"Error in prompt optimization: {str(e)}"
        gcp_logger.log_struct(
            {"message": error_msg, "request_id": request_id}, severity="ERROR"
        )
        logging.error(error_msg)

        if experiment_id:
            mlflow.log_param("error", str(e))

        return {"success": False, "message": error_msg}


# If run directly, execute the optimization process
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = optimize_prompt_strategies()
    print(result)
