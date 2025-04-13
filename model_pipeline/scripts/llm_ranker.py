import os
import json
import time
import mlflow
import yaml
from google.cloud import logging as gcp_logging
from dotenv import load_dotenv
from load_prompts import load_prompts
from render_criteria import render_criteria
import vertexai
from vertexai.generative_models import GenerativeModel
from config import (
    SERVICE_ACCOUNT_FILE,
    RANKER_CRITERIA_YAML,
    MODEL_ENV_PATH,
    IN_CLOUD_RUN,
    GCP_PROJECT_ID,
    SERVICE_ACCOUNT_SECRET_ID,
)
from send_notification import send_email_notification

if IN_CLOUD_RUN:
    from secret_manager import get_credentials_from_secret

load_dotenv(dotenv_path=MODEL_ENV_PATH)

gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("llm_ranker")

# Initialize credentials
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


def rank_outputs(criteria_prompt, outputs, task, request_id=None):
    """Rank outputs for a given task based on criteria."""
    start_time = time.time()

    with mlflow.start_run(
        nested=True, run_name=f"rank_{task}_{request_id or 'unknown'}"
    ):
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
            model = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002"))
            response = model.generate_content(criteria_prompt)
            response_text = response.text.strip() if response and response.text else ""
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
                return outputs
            try:
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
                ranked_outputs = [outputs[i] for i in ranked_indices]
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
                return outputs
        except Exception as e:
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
            return outputs


def rank_all_outputs(llm_outputs, task, body, request_id=None):
    start_time = time.time()

    with mlflow.start_run(
        nested=True, run_name=f"rank_all_{task}_{request_id or 'unknown'}"
    ):
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
            criterias = load_prompts(RANKER_CRITERIA_YAML)
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
            llm_ranks = {
                task: rank_outputs(
                    criteria_prompt=full_prompt,
                    outputs=llm_outputs[task],
                    task=task,
                    request_id=request_id,
                )
            }
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
