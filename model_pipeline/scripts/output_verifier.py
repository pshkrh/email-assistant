import time
import mlflow
from google.cloud import logging as gcp_logging
from llm_generator import process_email_body
from llm_ranker import rank_all_outputs
import re
import yaml
from config import STRUCTURE_PROMPTS_YAML, GCP_PROJECT_ID

# Initialize GCP Cloud Logging
gcp_client = gcp_logging.Client(project=GCP_PROJECT_ID)
gcp_logger = gcp_client.logger("output_verifier")


def load_structure_rules(yaml_file_path, request_id=None):
    """Load structure rules from YAML file."""
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
    except FileNotFoundError as e:
        error_msg = f"Structure rule file not found: {yaml_file_path}"
        gcp_logger.log_struct(
            {"message": error_msg, "request_id": request_id or "unknown"},
            severity="ERROR",
        )
        raise FileNotFoundError(error_msg)
    except yaml.YAMLError as e:
        error_msg = f"YAML parse error in structure rules: {str(e)}"
        gcp_logger.log_struct(
            {"message": error_msg, "request_id": request_id or "unknown"},
            severity="ERROR",
        )
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error loading structure rules: {str(e)}"
        gcp_logger.log_struct(
            {"message": error_msg, "request_id": request_id or "unknown"},
            severity="ERROR",
        )
        raise RuntimeError(error_msg)


def verify_structure(output, task, rules, request_id=None):
    """Verify that output matches the structure defined for the task."""
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

    if task == "summary":
        bullet_found = any(
            re.search(pattern, output, flags=re.MULTILINE)
            for pattern in task_rules.get("bullet_patterns", [])
        )
        prohibited_found = any(
            phrase in output for phrase in task_rules.get("prohibited_phrases", [])
        )
        result = bullet_found and not prohibited_found

    elif task == "action_items":
        bullet_found = any(
            re.search(pattern, output, flags=re.MULTILINE)
            for pattern in task_rules.get("bullet_patterns", [])
        )
        prohibited_found = any(
            phrase in output for phrase in task_rules.get("prohibited_phrases", [])
        )
        result = bullet_found and not prohibited_found

    elif task == "draft_reply":
        required_phrases_met = all(
            req_phrase in output
            for req_phrase in task_rules.get("required_phrases", [])
        )
        sign_off_found = any(
            phrase in output for phrase in task_rules.get("sign_off_phrases", [])
        )
        result = required_phrases_met and sign_off_found

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
    ranked_outputs, task, body, userEmail, max_attempts=2, request_id=None
):
    """Verify top output, fall back if needed, retry LLM if all fail."""
    start_time = time.time()
    rules = load_structure_rules(STRUCTURE_PROMPTS_YAML, request_id)

    with mlflow.start_run(nested=True, run_name=f"verify_{task}"):
        # Log parameters
        mlflow.log_params(
            {
                f"{task}_max_attempts": max_attempts,
                "request_id": request_id or "unknown",
                "user_email": userEmail,
                f"{task}_input_output_count": len(ranked_outputs),
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
            for i, output in enumerate(ranked_outputs):
                if verify_structure(output, task, rules, request_id):
                    mlflow.log_metric(f"{task}_verification_attempts", attempt + 1)
                    mlflow.log_text(output, f"{task}_verified_output.txt")

                    duration = time.time() - start_time
                    mlflow.log_metric(f"{task}_verification_duration_seconds", duration)

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
                new_llm_outputs = process_email_body(
                    body, task, userEmail, {}, [], request_id=request_id
                )
                ranked_outputs = rank_all_outputs(
                    new_llm_outputs, task, body, request_id=request_id
                )[task]
                mlflow.log_metric(f"{task}_regen_attempts", attempt)
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
                error_msg = f"Regeneration failed for task {task}: {str(e)}"
                mlflow.log_param(f"{task}_regen_error", str(e))
                mlflow.log_text(str(e), f"{task}_regen_fallback_error.txt")
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                        "attempt": attempt,
                    },
                    severity="ERROR",
                )
                break  # Exit retry loop and fall back

        # Fallback to top-ranked output
        fallback_output = ranked_outputs[0]
        mlflow.log_text(fallback_output, f"{task}_fallback_output.txt")

        duration = time.time() - start_time
        mlflow.log_metric(f"{task}_verification_duration_seconds", duration)

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


def verify_all_outputs(ranked_outputs_dict, task, body, userEmail, request_id=None):
    """Verify all ranked outputs for a task and return the best one."""
    start_time = time.time()

    with mlflow.start_run(run_name=f"verify_all_{task}"):
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
            outputs = ranked_outputs_dict.get(task)
            if not outputs or not isinstance(outputs, list):
                error_msg = f"No ranked outputs found for task '{task}'"
                mlflow.log_param(f"{task}_verify_failed", True)
                mlflow.log_text(error_msg, f"{task}_verify_failure.txt")
                gcp_logger.log_struct(
                    {
                        "message": error_msg,
                        "request_id": request_id or "unknown",
                        "task": task,
                    },
                    severity="ERROR",
                )
                raise ValueError(error_msg)

            best_output = get_best_output(
                outputs, task, body, userEmail, request_id=request_id
            )

            # Log result
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
            error_msg = f"Verification failed for task '{task}': {str(e)}"
            mlflow.log_param(f"{task}_verify_failed", True)
            mlflow.log_param(f"{task}_verify_error", str(e))
            mlflow.log_text(str(e), f"{task}_verify_failure.txt")
            gcp_logger.log_struct(
                {
                    "message": error_msg,
                    "request_id": request_id or "unknown",
                    "task": task,
                },
                severity="ERROR",
            )
            raise RuntimeError(error_msg) from e
