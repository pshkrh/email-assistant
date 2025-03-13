# model_pipeline/output_verifier.py
from llm_generator import generate_outputs
import mlflow
import re


def verify_structure(output, task):
    """Check if output matches expected structure."""
    if task == "summary":
        words = output.split()
        return 20 <= len(words) <= 100 and "\n" not in output
    elif task == "action_items":
        return bool(re.match(r"(\d+\.\s+.*\n?)+", output.strip()))
    elif task == "draft_reply":
        return len(output.split("\n")) >= 3 and "Dear" in output
    return False


def get_best_output(ranked_outputs, task, body, max_attempts=2):
    """Verify top output, fall back if needed, retry LLM if all fail."""
    attempt = 0
    with mlflow.start_run(nested=True):
        mlflow.log_param(f"{task}_max_attempts", max_attempts)
        while attempt < max_attempts:
            for i, output in enumerate(ranked_outputs):
                if verify_structure(output, task):
                    mlflow.log_metric(f"{task}_verification_attempts", attempt + 1)
                    mlflow.log_text(output, f"{task}_verified_output.txt")
                    return output
            attempt += 1
            ranked_outputs = rank_outputs(generate_outputs(body, task), task, body)
            mlflow.log_metric(f"{task}_regen_attempts", attempt)
        mlflow.log_text(ranked_outputs[0], f"{task}_fallback_output.txt")
        return ranked_outputs[0]  # Fallback


def verify_all_outputs(ranked_outputs_dict, body):
    """Verify and select best output for each task."""
    return {
        "summary": get_best_output(ranked_outputs_dict["summaries"], "summary", body),
        "action_items": get_best_output(
            ranked_outputs_dict["action_items"], "action_items", body
        ),
        "draft_reply": get_best_output(
            ranked_outputs_dict["draft_replies"], "draft_reply", body
        ),
    }
