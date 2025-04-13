import os
import pickle
import base64
import uuid
import time
import logging
from flask import Flask, request, jsonify
from google.cloud import logging as gcp_logging
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from flask_cors import CORS
import mlflow

from llm_generator import process_email_body
from llm_ranker import rank_all_outputs
from output_verifier import verify_all_outputs
from save_to_database import save_to_db
from update_database import update_user_feedback
from db_helpers import get_existing_user_feedback
from db_helpers import get_last_3_feedbacks
from config import (
    IN_CLOUD_RUN,
    GCP_PROJECT_ID,
    GMAIL_API_SECRET_ID,
    GMAIL_API_CREDENTIALS,
)
from mlflow_config import start_experiment

if IN_CLOUD_RUN:
    from secret_manager import get_credentials_from_secret

start_experiment()  # Initialize MLflow

app = Flask(__name__)

# Set up GCP Cloud Logging
gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("gmail_thread_fetcher")
logging.getLogger().setLevel(logging.DEBUG)  # Fallback for local development

# Replace Flask's default logger with GCP logger for consistency
app.logger.handlers = []
app.logger.propagate = False

CORS(
    app,
    resources={
        r"/.*": {
            "origins": ["chrome-extension://*"],
            "methods": ["POST", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type"],
            "supports_credentials": True,
        }
    },
)

# Load Gmail API credentials
if IN_CLOUD_RUN:
    try:
        get_credentials_from_secret(
            GCP_PROJECT_ID, GMAIL_API_SECRET_ID, save_to_file=GMAIL_API_CREDENTIALS
        )
        gcp_logger.log_text(
            "Gmail API credentials loaded from Secret Manager", severity="INFO"
        )
    except Exception as e:
        gcp_logger.log_struct(
            {"message": "Failed to load Gmail credentials", "error": str(e)},
            severity="ERROR",
        )


@app.route("/fetch_gmail_thread", methods=["POST"])
def fetch_gmail_thread():
    """Fetch email thread details for a given thread ID."""
    request_id = str(uuid.uuid4())  # Unique ID for request correlation
    start_time = time.time()

    # Log request start
    gcp_logger.log_struct(
        {"message": "Received fetch_gmail_thread request", "request_id": request_id},
        severity="INFO",
    )

    # Start MLflow run for this endpoint
    with mlflow.start_run(run_name=f"fetch_gmail_thread_{request_id}"):
        try:
            data = request.get_json()
            required_fields = [
                "userEmail",
                "messageId",
                "threadId",
                "messagesCount",
                "body",
            ]

            # Validate input
            if not all(
                field in data and data[field] is not None for field in required_fields
            ):
                error_msg = f"Missing one/more required fields: {required_fields}"
                gcp_logger.log_struct(
                    {"message": error_msg, "request_id": request_id}, severity="ERROR"
                )
                mlflow.log_param("error", error_msg)
                return jsonify({"error": error_msg}), 400

            thread_id = data.get("threadId")
            email = data.get("userEmail")
            requested_tasks = data.get("tasks", [])

            # Log input parameters
            mlflow.log_params(
                {
                    "thread_id": thread_id,
                    "user_email": email,
                    "tasks": requested_tasks,
                    "messages_count": data.get("messagesCount"),
                }
            )
            mlflow.log_dict(data, "input_request.json")  # Save request payload

            gcp_logger.log_struct(
                {
                    "message": "Processing request",
                    "request_id": request_id,
                    "thread_id": thread_id,
                    "user_email": email,
                    "tasks": requested_tasks,
                },
                severity="DEBUG",
            )

            if not requested_tasks:
                error_msg = "No task specified"
                gcp_logger.log_struct(
                    {"message": error_msg, "request_id": request_id}, severity="ERROR"
                )
                mlflow.log_param("error", error_msg)
                return jsonify({"error": error_msg}), 400

            # Check existing record
            existing_record = get_existing_user_feedback(
                email, thread_id, data["messagesCount"], requested_tasks
            )
            gcp_logger.log_struct(
                {
                    "message": "Checked existing feedback",
                    "request_id": request_id,
                    "existing_record": bool(existing_record),
                },
                severity="DEBUG",
            )

            results = {}
            task_regen_needed = {}
            prompt_strategy = {
                "summary": None,
                "action_items": None,
                "draft_reply": None,
            }
            negative_examples_by_task = {}

            # Determine which tasks need regeneration
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
                        gcp_logger.log_struct(
                            {
                                "message": f"Reusing output for task {task}",
                                "request_id": request_id,
                                "thread_id": thread_id,
                            },
                            severity="INFO",
                        )
                        continue
                task_regen_needed[task] = True

            # Determine prompt strategy based on feedback
            for task in requested_tasks:
                if not task_regen_needed.get(task):
                    continue
                feedback_column = f"{task}_feedback"
                recent_feedbacks = get_last_3_feedbacks(email, feedback_column, task)
                negative_count = sum(1 for f in recent_feedbacks if f[2] == 0)

                gcp_logger.log_struct(
                    {
                        "message": f"Recent feedbacks for task {task}",
                        "request_id": request_id,
                        "feedback_count": len(recent_feedbacks),
                        "negative_count": negative_count,
                    },
                    severity="DEBUG",
                )

                if negative_count >= 2:
                    prompt_strategy[task] = "alternate"
                    negative_examples_by_task[task] = [
                        (f[0], f[1]) for f in recent_feedbacks if f[2] == 0
                    ]
                else:
                    prompt_strategy[task] = "default"
                    negative_examples_by_task[task] = []

                mlflow.log_param(f"{task}_prompt_strategy", prompt_strategy[task])

            # Process tasks requiring regeneration
            for task in requested_tasks:
                if not task_regen_needed.get(task):
                    continue

                gcp_logger.log_struct(
                    {
                        "message": f"Generating output for task {task}",
                        "request_id": request_id,
                        "thread_id": thread_id,
                    },
                    severity="INFO",
                )

                try:
                    body = data["body"]
                    llm_generator_output = process_email_body(
                        body=body,
                        task=task,
                        user_email=email,
                        prompt_strategy=prompt_strategy,
                        negative_examples=negative_examples_by_task.get(task, []),
                        request_id=request_id,
                    )

                    llm_ranker_output = rank_all_outputs(
                        llm_outputs=llm_generator_output,
                        task=task,
                        body=body,
                        request_id=request_id,
                    )

                    best_output = verify_all_outputs(
                        ranked_outputs_dict=llm_ranker_output,
                        task=task,
                        body=body,
                        userEmail=email,
                        request_id=request_id,
                    )

                    results[task] = best_output

                    # Log task output as artifact
                    mlflow.log_dict({task: best_output}, f"{task}_output.json")

                except Exception as e:
                    error_msg = f"Error generating output for task '{task}': {str(e)}"
                    gcp_logger.log_struct(
                        {
                            "message": error_msg,
                            "request_id": request_id,
                            "thread_id": thread_id,
                        },
                        severity="ERROR",
                    )
                    mlflow.log_param(f"{task}_error", str(e))
                    return jsonify({"error": error_msg}), 500

            # Prepare data for database
            message_data = {
                "Message-ID": data["messageId"],
                "From": data["from"],
                "To": data["to"],
                "Subject": data["subject"],
                "Date": data["date"],
                "Body": data["body"],
                "MessagesCount": data["messagesCount"],
                "Thread_Id": thread_id,
                "User_Email": email,
                "Prompt_Strategy": prompt_strategy,
            }

            # Save to database
            try:
                all_tasks_reused = all(
                    not needed for needed in task_regen_needed.values()
                )
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

                gcp_logger.log_struct(
                    {
                        "message": "Saved to database",
                        "request_id": request_id,
                        "doc_id": table_docid,
                        "reused": all_tasks_reused,
                    },
                    severity="INFO",
                )
                mlflow.log_param("doc_id", table_docid)

            except Exception as e:
                error_msg = f"Error saving to database: {str(e)}"
                gcp_logger.log_struct(
                    {"message": error_msg, "request_id": request_id}, severity="ERROR"
                )
                mlflow.log_param("db_error", str(e))
                return jsonify({"error": error_msg}), 500

            # Prepare response
            response = {
                "threadId": thread_id,
                "userEmail": email,
                "docId": table_docid,
                "result": results,
                "promptStrategy": prompt_strategy,
            }

            # Log response and duration
            duration = time.time() - start_time
            gcp_logger.log_struct(
                {
                    "message": "Request completed successfully",
                    "request_id": request_id,
                    "duration_seconds": duration,
                    "thread_id": thread_id,
                },
                severity="INFO",
            )
            mlflow.log_metric("request_duration_seconds", duration)
            mlflow.log_dict(response, "response.json")

            return jsonify(response)

        except Exception as e:
            error_msg = f"Unexpected server error: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            mlflow.log_param("server_error", str(e))
            return jsonify({"error": error_msg}), 500


@app.route("/store_feedback", methods=["POST"])
def store_feedback():
    """Store user feedback for a task."""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    gcp_logger.log_struct(
        {"message": "Received store_feedback request", "request_id": request_id},
        severity="INFO",
    )

    with mlflow.start_run(run_name=f"store_feedback_{request_id}"):
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
                error_msg = "Missing JSON payload"
                gcp_logger.log_struct(
                    {"message": error_msg, "request_id": request_id}, severity="ERROR"
                )
                mlflow.log_param("error", error_msg)
                return jsonify({"error": error_msg}), 400

            missing = [field for field in required_fields if field not in data]
            if missing:
                error_msg = f"Missing required fields: {', '.join(missing)}"
                gcp_logger.log_struct(
                    {"message": error_msg, "request_id": request_id}, severity="ERROR"
                )
                mlflow.log_param("error", error_msg)
                return jsonify({"error": error_msg}), 400

            task = data["task"]
            feedback = 0 if data["rating"] == "thumbs_down" else 1
            doc_id = data["docId"]

            mlflow.log_params(
                {
                    "user_email": data["userEmail"],
                    "thread_id": data["threadId"],
                    "task": task,
                    "feedback": feedback,
                    "doc_id": doc_id,
                }
            )
            mlflow.log_dict(data, "feedback_request.json")

            gcp_logger.log_struct(
                {
                    "message": "Processing feedback",
                    "request_id": request_id,
                    "task": task,
                    "feedback": feedback,
                    "doc_id": doc_id,
                },
                severity="DEBUG",
            )

            valid_tasks = {
                "summary": "summary_feedback",
                "action_items": "action_items_feedback",
                "draft_reply": "draft_reply_feedback",
            }

            column_name = valid_tasks.get(task)
            if not column_name:
                error_msg = f"Invalid task type: {task}"
                gcp_logger.log_struct(
                    {"message": error_msg, "request_id": request_id}, severity="ERROR"
                )
                mlflow.log_param("error", error_msg)
                return jsonify({"error": error_msg}), 400

            try:
                response = update_user_feedback(
                    column_name=column_name, feedback=feedback, doc_id=doc_id
                )

                gcp_logger.log_struct(
                    {
                        "message": "Feedback stored successfully",
                        "request_id": request_id,
                        "response": response["message"],
                    },
                    severity="INFO",
                )
                mlflow.log_dict(response, "feedback_response.json")

                duration = time.time() - start_time
                mlflow.log_metric("feedback_duration_seconds", duration)

                return jsonify(response)

            except Exception as db_error:
                error_msg = f"Database update failed: {str(db_error)}"
                gcp_logger.log_struct(
                    {"message": error_msg, "request_id": request_id}, severity="ERROR"
                )
                mlflow.log_param("db_error", str(db_error))
                return jsonify({"error": error_msg}), 500

        except Exception as e:
            error_msg = f"Unexpected server error in store_feedback: {str(e)}"
            gcp_logger.log_struct(
                {"message": error_msg, "request_id": request_id}, severity="ERROR"
            )
            mlflow.log_param("server_error", str(e))
            return jsonify({"error": error_msg}), 500


if __name__ == "__main__":
    print("Starting server")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
