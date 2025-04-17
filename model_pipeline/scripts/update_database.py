"""
Database Update Module

This module provides functions to update existing records in the database.
It includes functionality to store user feedback on generated content to
improve future generations through learning from user preferences.
"""

from db_connection import get_db_connection


def update_user_feedback(column_name, feedback, doc_id):
    """
    Update user feedback for a specific content type in the database.

    This function stores user ratings (thumbs up/down) for generated content.
    These ratings are used to track performance and optimize prompt strategies.

    Args:
        column_name (str): Database column to update (e.g., "summary_feedback")
        feedback (int): Feedback value (0 for negative, 1 for positive)
        doc_id (int): Database record ID to update

    Returns:
        dict: Status message or error information

    Raises:
        Exception: Handled internally and returned as error message
    """
    try:
        # Connect to database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Construct and execute update query
                query = f"""
                    UPDATE user_feedback
                    SET {column_name} = %s
                    WHERE id = %s
                """
                cur.execute(query, (feedback, doc_id))
                conn.commit()

        # Return success message
        return {
            "message": f"Feedback updated for doc ID: {doc_id}",
        }
    except Exception as e:
        # Return error message
        return {"error": str(e)}
