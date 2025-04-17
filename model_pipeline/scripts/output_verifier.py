"""
Output Verifier Module

This module verifies the quality and structure of ranked outputs from the ranker module.
It ensures outputs meet structural requirements (e.g., bullet points for summaries,
proper sign-offs for replies) and regenerates content if needed.
"""

import time
import re

import mlflow
import yaml
from google.cloud import logging as gcp_logging

from llm_generator import process_email_body
from llm_ranker import rank_all_outputs
from config import STRUCTURE_PROMPTS_YAML, GCP_PROJECT_ID
from send_notification import send_email_notification

# Initialize GCP Cloud Logging
gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("output_verifier")


def load_structure_rules(yaml_file_path, request_id=None):
    """
    Load structural rules for output verification from YAML file.

    Args:
        yaml_file_path (str): Path to YAML file with structure rules
        request_id (str, optional): Unique identifier for request correlation

    Returns:
        dict: Dictionary of structure rules by task

    Raises:
        FileNotFoundError: If YAML file not found
        YAMLError: If YAML parsing fails
    """
    try:
        with open(yaml_file_path, "r") as file:
            rules = yaml.safe_load(file)
        gcp_logger.log_struct(
            {
                "message": "Loaded structure rules",
                "request_id": request_id or "unknown",
                "file_path": yaml_file_path,
                "rule_count": len(rules) if rules else 0,
            },
            severity="INFO",
        )
        return rules
    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        error_msg = f"Error loading structure rules: {str(e)}"
        gcp_logger.log_struct(
            {"message": error_msg, "request_id": request_id or "unknown"},
            severity="ERROR",
        )
        raise


def verify_structure(output, task, rules, request_id=None):
    """
    Verify the structure of an output against task-specific rules.

    Args:
        output (str): Generated output text
        task (str): Task type (summary, action_items, draft_reply)
        rules (dict): Dictionary of structure rules by task
        request_id (str, optional): Unique identifier for request correlation

    Returns:
        bool: True if structure is valid, False otherwise
    """
    # Check if rules exist for this task
    if task not in rules:
        gcp_logger.log_struct(
            {
                "message": f"Task {task} not found in structure rules",
                "request_id": request_id or "unknown",
                "task": task,
            },
            severity="WARNING",
        )
        return False

    task_rules = rules[task]
    result = False

    # Apply task-specific verification rules
    if task == "summary":
        # Check for bullet point patterns and prohibited phrases
        bullet_found = any(
            re.search(pattern, output, flags=re.MULTILINE)
            for pattern in task_rules.get("bullet_patterns", [])
        )
        prohibited_found = any(
            phrase in output for phrase in task_rules.get("prohibited_phrases", [])
        )
        result = bullet_found and not prohibited_found
    elif task == "action_items":
        # Check for bullet point patterns and prohibited phrases
        bullet_found = any(
            re.search(pattern, output, flags=re.MULTILINE)
            for pattern in task_rules.get("bullet_patterns", [])
        )
        prohibited_found = any(
            phrase in output for phrase in task_rules.get("prohibited_phrases", [])
        )
        result = bullet_found and not prohibited_found
    elif task == "draft_reply":
        # Check for required phrases and sign-off
        required_phrases_met = all(
            req_phrase in output
            for req_phrase in task_rules.get("required_phrases", [])
        )
        sign_off_found = any(
            phrase in output for phrase in task_rules.get("sign_off_phrases", [])
        )
        result = required_phrases_met and sign_off_found

    # Log verification result
    gcp_logger.log_struct(
        {
            "message": f"Verified structure for task {task}",
            "request_id": request_id or "unknown",
            "task": task,
            "result": result,
            "output_length": len(output),
        },
        severity="DEBUG",
    )
    return result


def get_best_output(
    ranked_outputs,
    task,
    body,
    userEmail,
    experiment_id,
    max_attempts=2,
    request_id=None,
):
    """
    Get the best output that passes structural verification.

    If no outputs pass verification, regenerate content and retry.

    Args:
        ranked_outputs (list): List of outputs ranked by quality
        task (str): Task type (summary, action_items, draft_reply)
        body (str): Email body text
        userEmail (str): User email address
        experiment_id (str): MLflow experiment ID
        max_attempts (int): Maximum number of regeneration attempts
        request_id (str, optional): Unique identifier for request correlation

    Returns:
        str: Best verified output
    """
    start_time = time.time()
    rules = load_structure_rules(STRUCTURE_PROMPTS_YAML, request_id)

    with mlflow.start_run(
        nested=True,
        experiment_id=experiment_id,
        run_name=f"verify_{task}_{request_id or 'unknown'}",
    ):
        # Log parameters
        mlflow.log_params(
            {
                "task": task,
                "request_id": request_id or "unknown",
                "max_attempts": max_attempts,
                "input_output_count": len(ranked_outputs),
            }
        )
        gcp_logger.log_struct(
            {
                "message": f"Starting verification for task {task}",
                "request_id": request_id or "unknown",
                "task": task,
                "user_email": userEmail,
                "max_attempts": max_attempts,
                "input_output_count": len(ranked_outputs),
            },
            severity="INFO",
        )

        attempt = 0
        while attempt < max_attempts:
            # Try each output in ranked order
            for i, output in enumerate(ranked_outputs):
                if verify_structure(output, task, rules, request_id):
                    # Found valid output
                    mlflow.log_metric("verification_attempts", attempt + 1)
                    mlflow.log_text(output, f"{task}_verified_output.txt")
                    duration = time.time() - start_time
                    mlflow.log_metric("verification_duration_seconds", duration)
                    gcp_logger.log_struct(
                        {
                            "message": f"Verified output for task {task}",
                            "request_id": request_id or "unknown",
                            "task": task,
                            "attempt": attempt,
                            "index": i,
                            "duration_seconds": duration,
                        },
                        severity="INFO",
                    )
                    return output

            # No valid outputs found, retry
            attempt += 1
            gcp_logger.log_struct(
                {
                    "message": f"No valid output found, retrying task {task}",
                    "request_id": request_id or "unknown",
                    "task": task,
                    "attempt": attempt,
                },
                severity="WARNING",
            )

            try:
                # Regenerate outputs with default settings
                new_llm_outputs = process_email_body(
                    body=body,
                    task=task,
                    user_email=userEmail,
                    prompt_strategy={},
                    negative_examples=[],
                    request_id=request_id,
                    experiment_id=experiment_id,
                )
                # Rank new outputs
                ranked_outputs = rank_all_outputs(
                    llm_outputs=new_llm_outputs,
                    task=task,
                    body=body,
                    request_id=request_id,
                    experiment_id=experiment_id,
                )[task]

                # Log regeneration metrics
                mlflow.log_metric("regen_attempts", attempt)
                mlflow.log_dict(
                    {task: ranked_outputs}, f"{task}_regenerated_outputs.json"
                )
                gcp_logger.log_struct(
                    {
                        "message": f"Regenerated outputs for task {task}",
                        "request_id": request_id or "unknown",
                        "task": task,
                        "attempt": attempt,
                        "new_output_count": len(ranked_outputs),
                    },
                    severity="DEBUG",
                )
            except Exception as e:
                # Handle regeneration errors
                error_msg = f"Regeneration failed for task {task}: {str(e)}"
                mlflow.log_param("regen_error", str(e))
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                        "attempt": attempt,
                    },
                    severity="ERROR",
                )
                send_email_notification(
                    "LLM Regeneration Failure", error_msg, request_id
                )
                break

        # Fallback to top-ranked output if no valid outputs found
        fallback_output = ranked_outputs[0]
        mlflow.log_text(fallback_output, f"{task}_fallback_output.txt")
        duration = time.time() - start_time
        mlflow.log_metric("verification_duration_seconds", duration)
        gcp_logger.log_struct(
            {
                "message": f"Fallback to top-ranked output for task {task}",
                "request_id": request_id or "unknown",
                "task": task,
                "attempts_made": attempt,
                "duration_seconds": duration,
            },
            severity="WARNING",
        )
        return fallback_output


def verify_all_outputs(
    ranked_outputs_dict, task, body, userEmail, experiment_id, request_id=None
):
    """
    Verify all outputs for a task and return the best one.

    Args:
        ranked_outputs_dict (dict): Dictionary of ranked outputs by task
        task (str): Task type (summary, action_items, draft_reply)
        body (str): Email body text
        userEmail (str): User email address
        experiment_id (str): MLflow experiment ID
        request_id (str, optional): Unique identifier for request correlation

    Returns:
        str: Best verified output for the task

    Raises:
        ValueError: If no ranked outputs found
    """
    start_time = time.time()

    with mlflow.start_run(
        nested=True,
        experiment_id=experiment_id,
        run_name=f"verify_all_{task}_{request_id or 'unknown'}",
    ):
        # Log parameters
        mlflow.log_params(
            {
                "task": task,
                "request_id": request_id or "unknown",
                "user_email": userEmail,
            }
        )
        gcp_logger.log_struct(
            {
                "message": f"Verifying all outputs for task {task}",
                "request_id": request_id or "unknown",
                "task": task,
                "user_email": userEmail,
            },
            severity="INFO",
        )

        try:
            # Get outputs for this task
            outputs = ranked_outputs_dict.get(task)

            # Validate outputs
            if not outputs or not isinstance(outputs, list):
                error_msg = f"No ranked outputs found for task '{task}'"
                mlflow.log_param("verify_error", error_msg)
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                    },
                    severity="ERROR",
                )
                send_email_notification("LLM Output Failure", error_msg, request_id)
                raise ValueError(error_msg)

            # Get the best output
            best_output = get_best_output(
                ranked_outputs=outputs,
                task=task,
                body=body,
                userEmail=userEmail,
                experiment_id=experiment_id,
                request_id=request_id,
            )

            # Log best output and metrics
            mlflow.log_dict({task: best_output}, f"{task}_best_output.json")
            duration = time.time() - start_time
            mlflow.log_metric("verify_all_duration_seconds", duration)
            gcp_logger.log_struct(
                {
                    "message": f"Completed verification for task {task}",
                    "request_id": request_id or "unknown",
                    "task": task,
                    "duration_seconds": duration,
                },
                severity="INFO",
            )
            return best_output
        except Exception as e:
            # Handle verification errors
            error_msg = f"Verification failed for task '{task}': {str(e)}"
            mlflow.log_param("verify_error", str(e))
            gcp_logger.log_struct(
                {
                    "message": error_msg,
                    "request_id": request_id or "unknown",
                    "task": task,
                },
                severity="ERROR",
            )
            raise
