from db_connection import get_db_connection


def get_existing_user_feedback(user_email, thread_id, messages_count, tasks):
    """
    Returns the most recent record that has non-null values for all requested tasks.
    """
    task_conditions = " AND ".join([f"{task} IS NOT NULL" for task in tasks])

    query = f"""
        SELECT *
        FROM user_feedback
        WHERE user_email = %s AND thread_id = %s AND messages_count = %s
        {"AND " + task_conditions if task_conditions else ""}
        ORDER BY id DESC
        LIMIT 1
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_email, thread_id, messages_count))
            return cur.fetchone()


def get_last_3_feedbacks(user_email, feedback_column, task):
    """Get last 3 feedback values for a task. Excludes NULLs from the DB."""
    query = f"""
        SELECT body, {task}, {feedback_column}
        FROM user_feedback
        WHERE user_email = %s AND {feedback_column} IS NOT NULL AND {task} is NOT NULL
        ORDER BY id DESC
        LIMIT 3
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_email,))
            rows = cur.fetchall()
            return [(row["body"], row[task], row[feedback_column]) for row in rows]
