import os
import pickle
import base64
import logging
from flask import Flask, request, jsonify
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from flask_cors import CORS
from config import GMAIL_API_CREDENTIALS, TOKEN_DIR

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
# CORS(app, resources={r"/fetch_gmail_thread": {"origins": "chrome-extension://*"}})

CORS(
    app,
    resources={
        r"/fetch_gmail_thread": {
            "origins": ["chrome-extension://agmojfdfhghpgmklbbdijhihdheihnda"],
            "methods": ["POST"],
            "allow_headers": ["Authorization", "Content-Type"],
        }
    },
)

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
        }
    )

    return messages


@app.route("/fetch_gmail_thread", methods=["POST"])
def fetch_gmail_thread():
    """Fetch email thread details for a given thread ID."""
    app.logger.info("Request Received...")
    data = request.get_json()
    thread_id = data.get("threadId")
    email = data.get("email")

    # Get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid authorization"}), 401

    token = auth_header.split(" ")[1]

    try:
        # Create credentials from the token
        from google.oauth2.credentials import Credentials

        credentials = Credentials(token=token)

        # Build Gmail service with the credentials
        service = build("gmail", "v1", credentials=credentials)

        # Fetch thread data using the existing code structure
        thread_data = service.users().threads().get(userId="me", id=thread_id).execute()

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
            }
        )

        return jsonify({"threadId": thread_id, "messages": messages})
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    print("Starting server")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
