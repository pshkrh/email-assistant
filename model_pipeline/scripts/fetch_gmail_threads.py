import os
import pickle
import base64
import logging
from flask import Flask, request, jsonify
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from flask_cors import CORS
from get_project_root import project_root

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# CORS(
#     app,
#     resources={
#         r"/process_thread": {
#             "origins": "chrome-extension://aelnladbenlanifdljmagnljckohcohe"
#         }
#     },
# )
# CORS(app)
CORS(app, resources={r"/process_thread": {"origins": "chrome-extension://*"}})

PROJECT_ROOT_DIR = project_root()
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = (
    f"{PROJECT_ROOT_DIR}/model_pipeline/credentials/MailMateCredentials.json"
)
TOKEN_DIR = f"{PROJECT_ROOT_DIR}/model_pipeline/credentials/user_tokens"


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


@app.route("/process_thread", methods=["POST"])
def process_thread():
    """Fetch email thread details for a given thread ID."""
    app.logger.info("Request Received...")
    data = request.get_json()
    thread_id = data.get("threadId")
    email = data.get("email")

    if not thread_id or not email:
        return jsonify({"error": "Missing thread ID or email"}), 400

    service = authenticate_gmail(email)
    thread_data = service.users().threads().get(userId="me", id=thread_id).execute()

    messages = []
    for msg in thread_data.get("messages", []):
        payload = msg["payload"]
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
                "messageId": headers.get("Message-ID", "N/A"),
                "date": headers.get("Date", "N/A"),
                "from": headers.get("From", "N/A"),
                "to": headers.get("To", "N/A"),
                "subject": headers.get("Subject", "N/A"),
                "body": body or "No readable body",
            }
        )

    print(len(messages), "\n\n")

    return jsonify({"threadId": thread_id, "messages": messages})


if __name__ == "__main__":
    print("Starting server")
    app.run(port=8000, debug=True)
