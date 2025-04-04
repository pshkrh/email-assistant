import os
import pickle
import base64
import logging
from flask import Flask, request, jsonify
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from flask_cors import CORS
from config import GMAIL_API_CREDENTIALS, TOKEN_DIR
from llm_generator import process_email_body
from llm_ranker import rank_all_outputs
from output_verifier import verify_all_outputs
from save_to_database import save_to_db

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# CORS(
#     app,
#     resources={
#         r"/fetch_gmail_thread": {
#             "origins": "chrome-extension://aelnladbenlanifdljmagnljckohcohe"
#         }
#     },
# )
# CORS(app)
CORS(app, resources={r"/fetch_gmail_thread": {"origins": "chrome-extension://*"}})

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = GMAIL_API_CREDENTIALS
TOKEN_DIR = TOKEN_DIR


def authenticate_gmail(email):
    """Authenticate Gmail user and return API service."""
    creds = None
    # Ensure token directory exists
    os.makedirs(TOKEN_DIR, exist_ok=True)

    token_file = os.path.join(TOKEN_DIR, f"{email}_token.pickle")

    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

        with open(token_file, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)


def process_thread(email, thread_id):
    if not thread_id or not email:
        return Exception(status_code=400, detail="Missing thread ID or email")

    service = authenticate_gmail(email)
    thread_data = service.users().threads().get(userId="me", id=thread_id).execute()

    messages_count = len(thread_data.get("messages", []))
    thread = thread_data.get("messages", [])[-1]
    messages = []
    payload = thread["payload"]
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    body = None
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8", "ignore"
                )
                break
    elif "body" in payload:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
            "utf-8", "ignore"
        )

    messages.append(
        {
            "Message-ID": headers.get("Message-ID", "N/A"),
            "Date": headers.get("Date", "N/A"),
            "From": headers.get("From", "N/A"),
            "To": headers.get("To", "N/A"),
            "Subject": headers.get("Subject", "N/A"),
            "Body": body or "No readable body",
            "MessagesCount": messages_count,
        }
    )

    return messages


@app.route("/fetch_gmail_thread", methods=["POST"])
def fetch_gmail_thread():
    """Fetch email thread details for a given thread ID."""
    app.logger.info("Request Received...")
    data = request.get_json()
    # TODO: tasks = data.get("tasks") [list of tasks user wants to perform]
    required_fields = ["userEmail", "messageId", "threadId", "messagesCount"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    thread_id = data.get("threadId")
    email = data.get("email")

    try:
        # messages = process_thread(email, thread_id)

        # print(messages)

        # llm_generator_output = process_email_body(
        #     body=messages[0]["Body"], tasks=[""], user_email=email
        # )
        # llm_ranker_output = rank_all_outputs(
        #     llm_outputs=llm_generator_output, tasks=[""], body=messages[0]["Body"]
        # )
        # best_output = verify_all_outputs(
        #     ranked_outputs_dict=llm_ranker_output, tasks=[""], userEmail=email
        # )

        # table_docid = save_to_db(
        #     user_email=email,
        #     message_data=messages[0],
        #     thread_id=thread_id,
        #     best_output=best_output,
        # )

        """
        After return responses
            If user responds for each task performed
                Save it to db with table_docid
        """

        return jsonify({"threadId": thread_id, "messages": data.get("body", "")})
    except Exception as e:
        return jsonify({"error": "Missing thread ID or email"}), 400


if __name__ == "__main__":
    print("Starting server")
    app.run(port=8000, debug=True)
