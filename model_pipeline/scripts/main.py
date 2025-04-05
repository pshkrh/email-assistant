import mlflow
import requests
from data_loader import load_enron_data
from fetch_gmail_threads import process_thread
from llm_generator import process_email_body
from llm_ranker import rank_all_outputs
from output_verifier import verify_all_outputs
from validation import run_validation
from bias_checker import main
from mlflow_config import start_experiment
from config import LABELED_SAMPLE_CSV_PATH, PREDICTED_SAMPLE_CSV_PATH


def send_fetch_gmail_thread_request(email, thread_id):
    """Send a POST request to the fetch_gmail_thread endpoint."""
    url = "http://127.0.0.1:8000/fetch_gmail_thread"
    payload = {
        "userEmail": email,
        "messageId": "unknown",  # Placeholder; adjust if you have a real message ID
        "threadId": thread_id,
        "messagesCount": 1,  # Placeholder; adjust based on actual data
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending request to fetch_gmail_thread: {e}")
        return {"error": str(e)}


def process_emails(data_source="enron", email=None, thread_id=None):
    """Process emails from Enron or Gmail with MLflow tracking."""
    if data_source == "enron":
        df = load_enron_data()
        data_iter = df.iterrows()
    elif data_source == "gmail" and email and thread_id:
        # Send request to fetch_gmail_thread instead of calling process_thread
        response = send_fetch_gmail_thread_request(email, thread_id)
        if "error" in response:
            raise ValueError(f"Failed to fetch Gmail thread: {response['error']}")

        # Assuming the response contains thread data; adjust based on actual response
        messages = [
            {
                "Body": "Fetched thread data",
                "Message-ID": response.get("messageId", "unknown"),
            }
        ]
        data_iter = enumerate(messages)
    else:
        raise ValueError("Invalid data source or missing parameters")

    predicted_outputs = {}
    with mlflow.start_run(nested=True, run_name=f"{data_source}_processing"):
        mlflow.log_param("data_source", data_source)
        if data_source == "gmail":
            mlflow.log_param("email", email)
            mlflow.log_param("thread_id", thread_id)

        tasks = ["summary"]
        for idx, row in data_iter:
            body = row["Body"]
            msg_id = row["Message-ID"]
            with mlflow.start_run(nested=True, run_name=f"msg_{msg_id}"):
                outputs = process_email_body(
                    body, tasks=tasks, user_email=email or "unknown"
                )
                ranked_outputs = rank_all_outputs(outputs, tasks, body)
                verified_outputs = verify_all_outputs(
                    ranked_outputs, tasks, body, email or "unknown"
                )
                predicted_outputs[msg_id] = verified_outputs
                mlflow.log_dict(verified_outputs, f"outputs_{msg_id}.json")
                print(f"Processed {msg_id}: {verified_outputs}")

    return predicted_outputs


if __name__ == "__main__":
    start_experiment()

    # Testing/Validation with Enron
    print("Running validation with Enron dataset...")
    with mlflow.start_run(run_name="enron_validation"):
        enron_outputs = process_emails(data_source="enron")
        run_validation(PREDICTED_SAMPLE_CSV_PATH, LABELED_SAMPLE_CSV_PATH)
        main(PREDICTED_SAMPLE_CSV_PATH, LABELED_SAMPLE_CSV_PATH)

    # Live run with Gmail
    # print("Running live with Gmail...")
    # with mlflow.start_run(run_name="gmail_live"):
    #     gmail_outputs = process_emails(
    #         data_source="gmail",
    #         email="try8200@gmail.com",
    #         thread_id="FMfcgzQZTgNvHWKpQpRqCRLDbRjSWmxJ"
    #     )
