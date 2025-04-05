from email.utils import parsedate_to_datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_NAME, USER, PASSWORD, HOST, PORT

# Database configuration (use environment variables in production)
DB_CONFIG = {
    "dbname": DB_NAME,
    "user": USER,
    "password": PASSWORD,
    "host": HOST,
    "port": PORT,
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def save_to_db(message_data, best_output):
    """Save email metadata and LLM outputs to Cloud SQL."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_feedback (
                    user_email, message_id, date, from_email, to_email, subject, body,
                    messages_count, thread_id, summary, action_items, draft_reply
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    message_data["User_Email"],
                    message_data["Message-ID"],
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
                ),
            )
            doc_id = cur.fetchone()["id"]
            conn.commit()
    return doc_id
