import os
import pickle
import base64
import logging
from flask import Flask, request, jsonify
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from flask_cors import CORS

from llm_generator import process_email_body
from llm_ranker import rank_all_outputs
from output_verifier import verify_all_outputs
from save_to_database import save_to_db
from update_database import update_user_feedback
from db_helpers import get_existing_user_feedback
from db_helpers import get_last_3_feedbacks
from config import IN_CLOUD_RUN, GCP_PROJECT_ID, GMAIL_API_SECRET_ID, GMAIL_API_CREDENTIALS

# Import the secret manager if running in Cloud Run
if IN_CLOUD_RUN:
    from secret_manager import get_credentials_from_secret

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

CORS(
    app,
    resources={
        r"/.*": {
            "origins": ["chrome-extension://*"],  # Allow any extension
            "methods": ["POST", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type"],
            "supports_credentials": True,
        }
    },
)

# Load Gmail API credentials
if IN_CLOUD_RUN:
    # In Cloud Run, get from Secret Manager
    try:
        get_credentials_from_secret(GCP_PROJECT_ID, GMAIL_API_SECRET_ID, save_to_file=GMAIL_API_CREDENTIALS)
        app.logger.info(f"Gmail API credentials loaded from Secret Manager")
    except Exception as e:
        app.logger.error(f"Failed to load Gmail credentials from Secret Manager: {e}")


@app.route("/fetch_gmail_thread", methods=["POST"])
def fetch_gmail_thread():
    """Fetch email thread details for a given thread ID."""
    app.logger.info("Request Received...")

    try:
        data = request.get_json()
        required_fields = [
            "userEmail",
            "messageId",
            "threadId",
            "messagesCount",
            "body",
        ]

        if not all(
            field in data and data[field] is not None for field in required_fields
        ):
            return (
                jsonify(
                    {"error": f"Missing one/more required fields: {required_fields}"}
                ),
                400,
            )

        thread_id = data.get("threadId")
        email = data.get("userEmail")
        requested_tasks = data.get("tasks", [])
        if not requested_tasks:
            return jsonify({"error": "No task specified"}), 400

        existing_record = get_existing_user_feedback(
            email, thread_id, data["messagesCount"], requested_tasks
        )
        results = {}
        task_regen_needed = {}
        prompt_strategy = {}
        negative_examples_by_task = {}

        for task in requested_tasks:
            output_column = task
            feedback_column = f"{task}_feedback"
            if existing_record:
                output_value = existing_record.get(output_column)
                feedback_value = existing_record.get(feedback_column)
                if output_value and (feedback_value == 1 or feedback_value is None):
                    results[task] = output_value
                    prompt_strategy[task] = "reused"
                    task_regen_needed[task] = False
                    continue
            task_regen_needed[task] = True

        for task in requested_tasks:
            if not task_regen_needed.get(task):
                continue
            feedback_column = f"{task}_feedback"
            recent_feedbacks = get_last_3_feedbacks(email, feedback_column, task)

            app.logger.info(f"Recent Feedbacks {recent_feedbacks}")

            negative_count = sum(1 for f in recent_feedbacks if f[2] == 0)
            if negative_count >= 2:
                prompt_strategy[task] = "alternate"
                negative_examples_by_task[task] = [
                    (f[0], f[1]) for i, f in enumerate(recent_feedbacks) if f[2] == 0
                ]
            else:
                prompt_strategy[task] = "default"
                negative_examples_by_task[task] = []

        for task in requested_tasks:
            if not task_regen_needed.get(task):
                continue

            try:
                body = data["body"]
                llm_generator_output = process_email_body(
                    body=body,
                    task=task,
                    user_email=email,
                    prompt_strategy=prompt_strategy,
                    negative_examples=negative_examples_by_task.get(task, []),
                )

                llm_ranker_output = rank_all_outputs(
                    llm_outputs=llm_generator_output, task=task, body=body
                )

                best_output = verify_all_outputs(
                    ranked_outputs_dict=llm_ranker_output,
                    task=task,
                    body=body,
                    userEmail=data["userEmail"],
                )

                results[task] = best_output

            except Exception as e:
                app.logger.error(f"Error generating output for task '{task}': {str(e)}")
                return (
                    jsonify({"error": f"Failed to process task '{task}': {str(e)}"}),
                    500,
                )

        message_data = {
            "Message-ID": data["messageId"],
            "From": data["from"],
            "To": data["to"],
            "Subject": data["subject"],
            "Date": data["date"],
            "Body": data["body"],
            "MessagesCount": data["messagesCount"],
            "Thread_Id": data["threadId"],
            "User_Email": data["userEmail"],
        }

        try:
            all_tasks_reused = all(not needed for needed in task_regen_needed.values())
            if not all_tasks_reused:
                table_docid = save_to_db(
                    message_data,
                    {
                        "Summary": results.get("summary"),
                        "Action_Items": results.get("action_items"),
                        "Draft_Reply": results.get("draft_reply"),
                    },
                )
            elif existing_record:
                table_docid = existing_record["id"]
            else:
                table_docid = None
        except Exception as e:
            app.logger.error(f"Error saving to database: {str(e)}")
            return jsonify({"error": f"Database save failed: {str(e)}"}), 500

        return jsonify(
            {
                "threadId": thread_id,
                "userEmail": email,
                "docId": table_docid,
                "result": results,
                "promptStrategy": prompt_strategy,
            }
        )

    except Exception as e:
        app.logger.error(f"Unexpected server error: {str(e)}")
        return jsonify({"error": f"Server failed to process request: {str(e)}"}), 500


@app.route("/store_feedback", methods=["POST"])
def store_feedback():
    """Store user feedback for a task."""
    app.logger.info("Feedback request received...")

    try:
        data = request.get_json()
        required_fields = [
            "userEmail",
            "threadId",
            "task",
            "rating",
            "timestamp",
            "docId",
        ]

        if not data:
            return jsonify({"error": "Missing JSON payload"}), 400

        missing = [field for field in required_fields if field not in data]
        if missing:
            return (
                jsonify({"error": f"Missing required fields: {', '.join(missing)}"}),
                400,
            )

        task = data["task"]
        feedback = 0 if data["rating"] == "thumbs_down" else 1
        doc_id = data["docId"]

        # Validate task
        valid_tasks = {
            "summary": "summary_feedback",
            "action_items": "action_items_feedback",
            "draft_reply": "draft_reply_feedback",
        }

        column_name = valid_tasks.get(task)
        if not column_name:
            return jsonify({"error": f"Invalid task type: {task}"}), 400

        # Update feedback in DB
        try:
            response = update_user_feedback(
                column_name=column_name, feedback=feedback, doc_id=doc_id
            )
            app.logger.info(response["message"])
            return jsonify(response)

        except Exception as db_error:
            app.logger.error(f"Database update failed: {str(db_error)}")
            return jsonify({"error": f"Database error: {str(db_error)}"}), 500

    except Exception as e:
        app.logger.error(f"Unexpected server error in /store_feedback: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == "__main__":
    print("Starting server")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
