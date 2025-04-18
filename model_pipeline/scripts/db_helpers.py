"""
Database Helpers Module

This module provides helper functions for database operations related to
user feedback and email processing. It includes functions to retrieve existing
feedback records and recent feedback history.
"""

from db_connection import get_db_connection


def get_existing_user_feedback(user_email, thread_id, messages_count, tasks):
    """
    Returns the most recent record that has non-null values for all requested tasks.

    Checks if there's already a record for this thread with outputs for the
    requested tasks, so we can avoid regenerating content unnecessarily.

    Args:
        user_email (str): User's email address
        thread_id (str): Email thread ID
        messages_count (int): Number of messages in the thread
        tasks (list): List of tasks to check for (e.g., ["summary", "action_items"])

    Returns:
        dict: Database record or None if no matching record found
    """
    # Build conditions to check that all requested tasks have values
    task_conditions = " AND ".join([f"{task} IS NOT NULL" for task in tasks])

    # Construct query to find the most recent record
    query = f"""
        SELECT *
        FROM user_feedback
        WHERE user_email = %s AND thread_id = %s AND messages_count = %s
        {"AND " + task_conditions if task_conditions else ""}
        ORDER BY id DESC
        LIMIT 1
    """

    # Execute query and return result
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_email, thread_id, messages_count))
            return cur.fetchone()


def get_last_3_feedbacks(user_email, feedback_column, task):
    """
    Get last 3 feedback values for a task.

    Retrieves recent feedback history for a specific task to identify patterns
    and determine if an alternate prompt strategy might be needed.

    Args:
        user_email (str): User's email address
        feedback_column (str): Column name for the feedback (e.g., "summary_feedback")
        task (str): Task name (e.g., "summary")

    Returns:
        list: List of tuples (body, content, feedback) for the last 3 feedback entries
    """
    # Query to get the 3 most recent feedback records for a specific task
    query = f"""
        SELECT body, {task}, {feedback_column}
        FROM user_feedback
        WHERE user_email = %s AND {feedback_column} IS NOT NULL AND {task} is NOT NULL
        ORDER BY id DESC
        LIMIT 3
    """

    # Execute query and format results
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_email,))
            rows = cur.fetchall()
            return [(row["body"], row[task], row[feedback_column]) for row in rows]
