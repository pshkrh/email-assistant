from db_connection import get_db_connection


def update_user_feedback(column_name, feedback, doc_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = f"""
                    UPDATE user_feedback
                    SET {column_name} = %s
                    WHERE id = %s
                """
                cur.execute(query, (feedback, doc_id))
                conn.commit()

        return {
            "message": f"Feedback updated for doc ID: {doc_id}",
        }
    except Exception as e:
        return {"error": str(e)}
