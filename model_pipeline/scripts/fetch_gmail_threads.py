import os
import pickle
import base64
import logging
from flask import Flask, request, jsonify
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from flask_cors import CORS
from config import GMAIL_API_CREDENTIALS, TOKEN_DIR

# from llm_generator import process_email_body
# from llm_ranker import rank_all_outputs
# from output_verifier import verify_all_outputs
from save_to_database import save_to_db

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

CORS(
    app,
    resources={
        r"/fetch_gmail_thread": {
            "origins": ["chrome-extension://*"],  # Allow any extension
            "methods": ["POST", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type"],
            "supports_credentials": True,
        }
    },
)


@app.route("/fetch_gmail_thread", methods=["POST"])
def fetch_gmail_thread():
    """Fetch email thread details for a given thread ID."""
    app.logger.info("Request Received...")
    data = request.get_json()
    # TODO: tasks = data.get("tasks") [list of tasks user wants to perform]
    required_fields = ["userEmail", "messageId", "threadId", "messagesCount", "body"]
    if not all(field in data and data[field] is not None for field in required_fields):
        return (
            jsonify({"error": f"Missing one/more required fields: {required_fields}"}),
            400,
        )
    thread_id = data.get("threadId")
    email = data.get("userEmail")

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

        table_docid = save_to_db(
            message_data=message_data,
            best_output={
                "Summary": "Dummy Summary",
                "Action_Items": "Dummy Action Items",
                "Draft_Reply": "Dummy Draft Reply",
            },
        )

        """
        After return responses
            If user responds for each task performed
                Save it to db with table_docid
        """

        print(table_docid)

        return jsonify({"threadId": thread_id, "messages": data.get("userEmail", "")})
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    print("Starting server")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
