"""
LLM Ranker Module

This module handles the ranking of multiple candidate outputs from the generator module.
It uses Vertex AI's Gemini model to evaluate and rank outputs based on quality criteria.
"""

import os
import json
import time

import mlflow
import yaml
from google.cloud import logging as gcp_logging
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

from load_prompts import load_prompts
from render_criteria import render_criteria
from config import (
    SERVICE_ACCOUNT_FILE,
    RANKER_CRITERIA_YAML,
    MODEL_ENV_PATH,
    IN_CLOUD_RUN,
    GCP_PROJECT_ID,
    SERVICE_ACCOUNT_SECRET_ID,
)
from send_notification import send_email_notification

# Import secret manager if in Cloud Run
if IN_CLOUD_RUN:
    from secret_manager import get_credentials_from_secret

# Load environment variables
load_dotenv(dotenv_path=MODEL_ENV_PATH)

# Initialize GCP Cloud Logging
gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("llm_ranker")

# Initialize credentials based on environment
if IN_CLOUD_RUN:
    creds_dict = get_credentials_from_secret(
        GCP_PROJECT_ID, SERVICE_ACCOUNT_SECRET_ID, save_to_file=SERVICE_ACCOUNT_FILE
    )
    from google.oauth2 import service_account

    CREDENTIALS = service_account.Credentials.from_service_account_info(creds_dict)
    GCP_PROJECT_ID = creds_dict.get("project_id", GCP_PROJECT_ID)
else:
    from google.auth import load_credentials_from_file

    CREDENTIALS, GCP_PROJECT_ID = load_credentials_from_file(SERVICE_ACCOUNT_FILE)

# Initialize Vertex AI
try:
    vertexai.init(
        project=GCP_PROJECT_ID,
        location=os.getenv("GCP_LOCATION"),
        credentials=CREDENTIALS,
    )
except Exception as e:
    error_msg = f"Vertex AI initialization failed: {str(e)}"
    gcp_logger.log_struct({"message": error_msg}, severity="ERROR")
    send_email_notification("LLM Connection Failure", error_msg)
    raise


def rank_outputs(criteria_prompt, outputs, task, experiment_id, request_id=None):
    """
    Rank multiple outputs for a task based on quality criteria.

    Args:
        criteria_prompt (str): Prompt containing ranking criteria and outputs
        outputs (list): List of outputs to rank
        task (str): Task type (summary, action_items, draft_reply)
        experiment_id (str): MLflow experiment ID
        request_id (str, optional): Unique identifier for request correlation

    Returns:
        list: Ranked outputs in order of quality
    """
    start_time = time.time()

    with mlflow.start_run(
        nested=True,
        experiment_id=experiment_id,
        run_name=f"rank_{task}_{request_id or 'unknown'}",
    ):
        # Log parameters
        mlflow.log_params(
            {
                "task": task,
                "request_id": request_id or "unknown",
                "input_output_count": len(outputs),
            }
        )
        gcp_logger.log_struct(
            {
                "message": f"Ranking outputs for task {task}",
                "request_id": request_id or "unknown",
                "task": task,
                "criteria_prompt_length": len(criteria_prompt),
                "input_output_count": len(outputs),
            },
            severity="INFO",
        )

        try:
            # Initialize model
            model = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002"))

            # Generate ranking response
            response = model.generate_content(criteria_prompt)
            response_text = response.text.strip() if response and response.text else ""

            # Handle empty response
            if not response_text:
                error_msg = f"Empty response from ranking LLM for task {task}"
                mlflow.log_param("rank_error", error_msg)
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                    },
                    severity="ERROR",
                )
                send_email_notification("LLM Output Failure", error_msg, request_id)
                return outputs  # Return original outputs if ranking failed

            try:
                # Parse response to get ranking
                structured_data = (
                    json.loads(response_text)
                    if response_text.startswith("{")
                    else {
                        task: response_text.split("ranked_indices:")[1]
                        .strip()
                        .split("\n")[0]
                    }
                )
                ranked_indices = json.loads(structured_data[task])

                # Reorder outputs based on ranking
                ranked_outputs = [outputs[i] for i in ranked_indices]

                # Log results
                mlflow.log_text("\n".join(ranked_outputs), f"{task}_ranked_outputs.txt")
                mlflow.log_param("top_ranked_index", ranked_indices[0])
                mlflow.log_dict(
                    {"ranked_indices": ranked_indices}, f"{task}_ranked_indices.json"
                )

                gcp_logger.log_struct(
                    {
                        "message": f"Ranked outputs for task {task}",
                        "request_id": request_id or "unknown",
                        "task": task,
                        "ranked_indices": ranked_indices,
                        "output_count": len(ranked_outputs),
                    },
                    severity="DEBUG",
                )

                # Log metrics
                duration = time.time() - start_time
                mlflow.log_metric("ranking_duration_seconds", duration)
                gcp_logger.log_struct(
                    {
                        "message": f"Completed ranking for task {task}",
                        "request_id": request_id or "unknown",
                        "task": task,
                        "duration_seconds": duration,
                    },
                    severity="INFO",
                )
                return ranked_outputs
            except Exception as e:
                # Handle parsing errors
                error_msg = (
                    f"Failed to parse ranking response for task {task}: {str(e)}"
                )
                mlflow.log_param("rank_parse_error", error_msg)
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                    },
                    severity="ERROR",
                )
                send_email_notification("LLM Output Failure", error_msg, request_id)
                return outputs  # Return original outputs if parsing failed
        except Exception as e:
            # Handle Gemini errors
            error_msg = f"Gemini ranking failed for task {task}: {str(e)}"
            mlflow.log_param("rank_error", error_msg)
            gcp_logger.log_struct(
                {
                    "message": error_msg,
                    "request_id": request_id or "unknown",
                    "task": task,
                },
                severity="ERROR",
            )
            send_email_notification("LLM Connection Failure", error_msg, request_id)
            return outputs  # Return original outputs if ranking failed


def rank_all_outputs(llm_outputs, task, body, experiment_id, request_id=None):
    """
    Process and rank all outputs for a given task.

    Args:
        llm_outputs (dict): Dictionary containing generator outputs for the task
        task (str): Task type (summary, action_items, draft_reply)
        body (str): Email body text
        experiment_id (str): MLflow experiment ID
        request_id (str, optional): Unique identifier for request correlation

    Returns:
        dict: Dictionary containing ranked outputs for the task

    Raises:
        ValueError: If criteria not found or outputs insufficient
        FileNotFoundError: If criteria file not found
    """
    start_time = time.time()

    with mlflow.start_run(
        nested=True,
        experiment_id=experiment_id,
        run_name=f"rank_all_{task}_{request_id or 'unknown'}",
    ):
        # Log parameters
        mlflow.log_params(
            {
                "task": task,
                "request_id": request_id or "unknown",
                "input_output_count": len(llm_outputs.get(task, [])),
            }
        )
        gcp_logger.log_struct(
            {
                "message": f"Processing ranking for task {task}",
                "request_id": request_id or "unknown",
                "task": task,
                "body_length": len(body),
            },
            severity="INFO",
        )

        try:
            # Load ranking criteria from YAML
            criterias = load_prompts(RANKER_CRITERIA_YAML)

            # Check if criteria exists for this task
            if task not in criterias:
                error_msg = f"No criteria found for task: {task}"
                mlflow.log_param("error", error_msg)
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                    },
                    severity="ERROR",
                )
                return {task: error_msg}

            # Check if we have enough outputs to rank
            if not llm_outputs.get(task) or len(llm_outputs[task]) < 3:
                error_msg = f"Invalid or insufficient outputs for task {task}"
                mlflow.log_param("error", error_msg)
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                    },
                    severity="ERROR",
                )
                send_email_notification("LLM Output Failure", error_msg, request_id)
                return {task: error_msg}

            # Render the criteria prompt with the outputs
            full_prompt = render_criteria(
                criterias[task],
                output0=llm_outputs[task][0],
                output1=llm_outputs[task][1],
                output2=llm_outputs[task][2],
                body=body,
            )

            if not full_prompt:
                error_msg = f"Failed to generate criteria prompt for task {task}"
                mlflow.log_param("error", error_msg)
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                    },
                    severity="ERROR",
                )
                return {task: error_msg}

            # Log the criteria prompt
            mlflow.log_text(full_prompt, f"{task}_criteria_prompt.txt")
            gcp_logger.log_struct(
                {
                    "message": f"Generated criteria prompt for task {task}",
                    "request_id": request_id or "unknown",
                    "task": task,
                    "prompt_length": len(full_prompt),
                },
                severity="DEBUG",
            )

            # Rank the outputs
            llm_ranks = {
                task: rank_outputs(
                    criteria_prompt=full_prompt,
                    outputs=llm_outputs[task],
                    task=task,
                    experiment_id=experiment_id,
                    request_id=request_id,
                )
            }

            # Log results and metrics
            mlflow.log_dict(llm_ranks, f"{task}_ranks.json")
            duration = time.time() - start_time
            mlflow.log_metric("rank_all_duration_seconds", duration)
            gcp_logger.log_struct(
                {
                    "message": f"Completed ranking for task {task}",
                    "request_id": request_id or "unknown",
                    "task": task,
                    "output_count": len(llm_ranks[task]),
                    "duration_seconds": duration,
                },
                severity="INFO",
            )
            return llm_ranks
        except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
            error_msg = f"Error in rank_all_outputs: {str(e)}"
            mlflow.log_param("error", error_msg)
            gcp_logger.log_struct(
                {
                    "message": error_msg,
                    "request_id": request_id or "unknown",
                    "task": task,
                },
                severity="ERROR",
            )
            raise
