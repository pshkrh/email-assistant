"""
Database Save Module

This module handles saving email data and LLM outputs to the PostgreSQL database.
It provides functionality to insert message data and generated content into the
user_feedback table for later retrieval and analysis.
"""

from email.utils import parsedate_to_datetime

from db_connection import get_db_connection


def save_to_db(message_data, best_output):
    """
    Save email metadata and LLM outputs to Cloud SQL.

    Args:
        message_data (dict): Dictionary containing email metadata including:
            - User_Email: Email address of the user
            - Message-ID: Unique identifier for the message
            - Date: Date of the message
            - From: Sender's email address
            - To: Recipient's email address
            - Subject: Email subject line
            - Body: Email body text
            - MessagesCount: Number of messages in thread
            - Thread_Id: Unique identifier for the thread
            - Prompt_Strategy: Dictionary of strategies used for each task
        best_output (dict): Dictionary of best outputs for each task:
            - Summary: Summary of the email
            - Action_Items: Action items extracted from the email
            - Draft_Reply: Draft reply to the email

    Returns:
        int: ID of the inserted database record
    """
    # Connect to database using connection pool
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Insert data into user_feedback table
            cur.execute(
                """
                INSERT INTO user_feedback (
                    user_email, message_id, date, from_email, to_email, subject, body,
                    messages_count, thread_id, summary, action_items, draft_reply, prompt_strategy_summary, 
                    prompt_strategy_action_items, prompt_strategy_draft_reply
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    message_data["User_Email"],
                    message_data["Message-ID"],
                    # Convert date string to datetime object, handle "N/A" values
                    (
                        parsedate_to_datetime(message_data["Date"]).date()
                        if message_data["Date"] != "N/A"
                        else None
                    ),
                    message_data["From"],
                    message_data["To"],
                    message_data["Subject"],
                    message_data["Body"],
                    message_data["MessagesCount"],
                    message_data["Thread_Id"],
                    best_output.get("Summary"),
                    best_output.get("Action_Items"),
                    best_output.get("Draft_Reply"),
                    message_data["Prompt_Strategy"]["summary"],
                    message_data["Prompt_Strategy"]["action_items"],
                    message_data["Prompt_Strategy"]["draft_reply"],
                ),
            )
            # Get the ID of the inserted record
            doc_id = cur.fetchone()["id"]
            # Commit the transaction
            conn.commit()
    return doc_id
