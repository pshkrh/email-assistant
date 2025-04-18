"""
Main Application Module

This module serves as the entry point for the email assistant application.
It provides functions to process emails from different sources (Enron dataset or Gmail),
and run validation and bias checking on the results.
"""

import mlflow
import requests

from data_loader import load_enron_data
from llm_generator import process_email_body
from llm_ranker import rank_all_outputs
from output_verifier import verify_all_outputs
from validation import run_validation
from bias_checker import main as run_bias_checker
from mlflow_config import start_experiment
from config import LABELED_SAMPLE_CSV_PATH, PREDICTED_SAMPLE_CSV_PATH


def send_fetch_gmail_thread_request(email, thread_id):
    """
    Send a POST request to the fetch_gmail_thread endpoint.

    Args:
        email (str): User email address
        thread_id (str): Gmail thread ID to fetch

    Returns:
        dict: Response data or error information
    """
    url = "https://email-assistant-673808915782.us-central1.run.app/fetch_gmail_thread"
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


def process_emails(experiment_id, data_source="enron", email=None, thread_id=None):
    """
    Process emails from Enron or Gmail with MLflow tracking.

    Args:
        experiment_id (str): MLflow experiment ID
        data_source (str): Source of emails ('enron' or 'gmail')
        email (str, optional): User email for Gmail source
        thread_id (str, optional): Thread ID for Gmail source

    Returns:
        dict: Dictionary of predicted outputs by message ID

    Raises:
        ValueError: If data source is invalid or parameters are missing
    """
    if data_source == "enron":
        # Load Enron dataset
        df = load_enron_data()
        data_iter = df.iterrows()
    elif data_source == "gmail" and email and thread_id:
        # Send request to fetch Gmail thread
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

    # Track predicted outputs
    predicted_outputs = {}

    # Start MLflow run for tracking
    with mlflow.start_run(
        nested=True, experiment_id=experiment_id, run_name=f"{data_source}_processing"
    ):
        # Log parameters
        mlflow.log_param("data_source", data_source)
        if data_source == "gmail":
            mlflow.log_param("email", email)
            mlflow.log_param("thread_id", thread_id)

        # Process each message
        tasks = ["summary"]
        for idx, row in data_iter:
            body = row["Body"]
            msg_id = row["Message-ID"]

            # Start nested run for each message
            with mlflow.start_run(
                nested=True, experiment_id=experiment_id, run_name=f"msg_{msg_id}"
            ):
                # Step 1: Generate outputs using LLM
                outputs = process_email_body(
                    body, tasks=tasks, user_email=email or "unknown"
                )

                # Step 2: Rank outputs by quality
                ranked_outputs = rank_all_outputs(outputs, tasks, body)

                # Step 3: Verify and select best outputs
                verified_outputs = verify_all_outputs(
                    ranked_outputs, tasks, body, email or "unknown"
                )

                # Store and log results
                predicted_outputs[msg_id] = verified_outputs
                mlflow.log_dict(verified_outputs, f"outputs_{msg_id}.json")
                print(f"Processed {msg_id}: {verified_outputs}")

    return predicted_outputs


if __name__ == "__main__":
    # Initialize MLflow experiment
    start_experiment()

    # Testing/Validation with Enron dataset
    print("Running validation with Enron dataset...")
    with mlflow.start_run(run_name="enron_validation"):
        # Process Enron emails
        enron_outputs = process_emails(data_source="enron")

        # Run validation and bias checking
        run_validation(PREDICTED_SAMPLE_CSV_PATH, LABELED_SAMPLE_CSV_PATH)
        run_bias_checker(PREDICTED_SAMPLE_CSV_PATH, LABELED_SAMPLE_CSV_PATH)

    # Live run with Gmail - uncomment to use
    # print("Running live with Gmail...")
    # with mlflow.start_run(run_name="gmail_live"):
    #     gmail_outputs = process_emails(
    #         data_source="gmail",
    #         email="try8200@gmail.com",
    #         thread_id="FMfcgzQZTgNvHWKpQpRqCRLDbRjSWmxJ"
    #     )
