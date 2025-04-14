import json
import yaml
import os
import time
import mlflow
from google.cloud import logging as gcp_logging
from jinja2 import Template
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from config import (
    SERVICE_ACCOUNT_FILE,
    GENERATOR_PROMPTS_YAML,
    ALTERNATE_GENERATOR_PROMPTS_YAML,
    MODEL_ENV_PATH,
    IN_CLOUD_RUN,
    GCP_PROJECT_ID,
    SERVICE_ACCOUNT_SECRET_ID,
)
from load_prompts import load_prompts
from render_prompt import render_prompt
from render_alternate_prompt import render_alternate_prompt
from send_notification import send_email_notification

if IN_CLOUD_RUN:
    from secret_manager import get_credentials_from_secret

load_dotenv(dotenv_path=MODEL_ENV_PATH)

gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("llm_generator")

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


def generate_outputs(task, prompt, experiment_id, request_id=None):
    """Generate 3 outputs for a given task using LLM."""
    start_time = time.time()
    outputs = []

    with mlflow.start_run(
        nested=True,
        experiment_id=experiment_id,
        run_name=f"generate_{task}_{request_id or 'unknown'}",
    ):
        mlflow.log_params({"task": task, "request_id": request_id or "unknown"})
        gcp_logger.log_struct(
            {
                "message": f"Generating outputs for task {task}",
                "request_id": request_id or "unknown",
                "task": task,
                "prompt_length": len(prompt),
            },
            severity="INFO",
        )

        for i in range(3):
            try:
                model = GenerativeModel(
                    os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002")
                )
                response = model.generate_content(prompt)
                response_text = (
                    response.text.strip() if response and response.text else ""
                )
                if not response_text:
                    error_msg = f"Empty response from LLM for task {task}"
                    outputs.append(error_msg)
                    mlflow.log_text(error_msg, f"{task}_output_{i}_error.txt")
                    gcp_logger.log_struct(
                        {
                            "message": error_msg,
                            "request_id": request_id or "unknown",
                            "task": task,
                        },
                        severity="ERROR",
                    )
                    send_email_notification("LLM Output Failure", error_msg, request_id)
                    continue
                if response_text.startswith("{"):
                    structured_data = json.loads(response_text)
                else:
                    content = (
                        response_text.split(f"{task}:")[1].split("```")[0].strip()
                        if f"{task}:" in response_text
                        else f"[Fallback] No {task} detected."
                    )
                    structured_data = {task: content}
                output = structured_data.get(task, f"[Missing key '{task}']")
                outputs.append(output)
                mlflow.log_text(output, f"{task}_output_{i}.txt")
                gcp_logger.log_struct(
                    {
                        "message": f"Generated output {i} for task {task}",
                        "request_id": request_id or "unknown",
                        "task": task,
                        "output_length": len(output),
                    },
                    severity="DEBUG",
                )
            except Exception as e:
                error_msg = f"Failed to generate output {i} for task {task}: {str(e)}"
                outputs.append(error_msg)
                mlflow.log_text(error_msg, f"{task}_output_{i}_error.txt")
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                    },
                    severity="ERROR",
                )
                send_email_notification("LLM Connection Failure", error_msg, request_id)
                continue

        duration = time.time() - start_time
        mlflow.log_metrics(
            {"output_count": len(outputs), "generation_duration_seconds": duration}
        )
        gcp_logger.log_struct(
            {
                "message": f"Completed generation for task {task}",
                "request_id": request_id or "unknown",
                "task": task,
                "output_count": len(outputs),
                "duration_seconds": duration,
            },
            severity="INFO",
        )
    return outputs


def get_prompt_for_task(task, strategy="default"):
    """Load prompt based on strategy."""
    try:
        prompts = load_prompts(
            GENERATOR_PROMPTS_YAML
            if strategy == "default"
            else ALTERNATE_GENERATOR_PROMPTS_YAML
        )
        return prompts.get(task)
    except Exception as e:
        gcp_logger.log_struct(
            {"message": f"Failed to load prompt for task {task}", "error": str(e)},
            severity="ERROR",
        )
        raise


def process_email_body(
    body,
    task,
    user_email,
    prompt_strategy,
    negative_examples,
    experiment_id,
    request_id=None,
):
    start_time = time.time()

    with mlflow.start_run(
        nested=True,
        experiment_id=experiment_id,
        run_name=f"process_email_{task}_{request_id or 'unknown'}",
    ):
        mlflow.log_params(
            {
                "task": task,
                "user_email": user_email,
                "prompt_strategy": prompt_strategy.get(task, "default"),
                "request_id": request_id or "unknown",
                "body_length": len(body),
            }
        )
        gcp_logger.log_struct(
            {
                "message": f"Processing email body for task {task}",
                "request_id": request_id or "unknown",
                "task": task,
                "user_email": user_email,
                "prompt_strategy": prompt_strategy.get(task, "default"),
            },
            severity="INFO",
        )

        try:
            prompt_style = prompt_strategy.get(task, "default")
            selected_prompt = get_prompt_for_task(task, strategy=prompt_style)
            if not selected_prompt:
                error_msg = f"No prompt found for task {task}"
                mlflow.log_param("error", error_msg)
                raise ValueError(error_msg)
            full_prompt = (
                render_prompt(selected_prompt, body, user_email)
                if prompt_style == "default"
                else render_alternate_prompt(
                    selected_prompt, body, user_email, negative_examples
                )
            )
            if not full_prompt:
                error_msg = f"Invalid prompt generated for task {task}"
                mlflow.log_param("error", error_msg)
                raise ValueError(error_msg)
            mlflow.log_text(full_prompt, f"{task}_full_prompt.txt")
            gcp_logger.log_struct(
                {
                    "message": f"Generated prompt for task {task}",
                    "request_id": request_id or "unknown",
                    "task": task,
                    "prompt_length": len(full_prompt),
                },
                severity="DEBUG",
            )
            llm_outputs = {
                task: generate_outputs(
                    task, full_prompt, request_id, experiment_id=experiment_id
                )
            }
            mlflow.log_dict(llm_outputs, f"{task}_outputs.json")
            duration = time.time() - start_time
            mlflow.log_metric("process_duration_seconds", duration)
            gcp_logger.log_struct(
                {
                    "message": f"Completed processing for task {task}",
                    "request_id": request_id or "unknown",
                    "task": task,
                    "output_count": len(llm_outputs[task]),
                    "duration_seconds": duration,
                },
                severity="INFO",
            )
            return llm_outputs
        except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
            error_msg = f"Error in process_email_body: {str(e)}"
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
