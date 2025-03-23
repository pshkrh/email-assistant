# model_pipeline/output_verifier.py
import mlflow

from llm_generator import process_email_body
from llm_ranker import rank_all_outputs
import re
import yaml
from config import STRUCTURE_PROMPTS_YAML


def load_structure_rules(yaml_file_path):
    """
    Loads structure rules from a YAML file and returns them as a dictionary.
    """
    with open(yaml_file_path, "r") as file:
        return yaml.safe_load(file)


def verify_structure(output, task, rules):
    """
    Verifies that `output` matches the structure defined for `task`
    according to the loaded `rules`.
    """
    if task not in rules:
        # If the task is not found in the YAML, consider it invalid or handle gracefully
        return False

    task_rules = rules[task]

    # ------------------------------
    # EXAMPLE: summary
    # ------------------------------
    if task == "summary":
        # 1. Check bullet patterns
        bullet_found = False
        for pattern in task_rules.get("bullet_patterns", []):
            # Compile once per pattern
            if re.search(pattern, output, flags=re.MULTILINE):
                bullet_found = True
                break
        if not bullet_found:
            return False

        # 2. Check prohibited phrases
        for phrase in task_rules.get("prohibited_phrases", []):
            if phrase in output:
                return False

        # 3. (Optional) Check word count if specified
        # min_word_count = task_rules.get("min_word_count", None)
        # max_word_count = task_rules.get("max_word_count", None)
        # if min_word_count or max_word_count:
        #     word_count = len(output.split())
        #     if min_word_count and word_count < min_word_count:
        #         return False
        #     if max_word_count and word_count > max_word_count:
        #         return False

        return True

    # ------------------------------
    # EXAMPLE: action_items
    # ------------------------------
    elif task == "action_items":
        # 1. Check bullet patterns
        bullet_found = False
        for pattern in task_rules.get("bullet_patterns", []):
            if re.search(pattern, output, flags=re.MULTILINE):
                bullet_found = True
                break
        if not bullet_found:
            return False

        # 2. Check prohibited phrases
        for phrase in task_rules.get("prohibited_phrases", []):
            if phrase in output:
                return False

        return True

    # ------------------------------
    # EXAMPLE: draft_reply
    # ------------------------------
    elif task == "draft_reply":
        # 1. Must contain at least one of the required phrases (e.g. "Dear")
        required_phrases = task_rules.get("required_phrases", [])
        for req_phrase in required_phrases:
            if req_phrase not in output:
                return False

        # 2. Must contain at least one of the sign-off phrases
        sign_off_phrases = task_rules.get("sign_off_phrases", [])
        if not any(phrase in output for phrase in sign_off_phrases):
            return False

        # 3. (Optional) Minimum number of lines
        # min_lines = task_rules.get("min_lines", None)
        # if min_lines:
        #     lines = output.strip().split('\n')
        #     if len(lines) < min_lines:
        #         return False

        return True

    else:
        # Unrecognized task
        return False


def get_best_output(ranked_outputs, task, body, userEmail, max_attempts=2):
    """Verify top output, fall back if needed, retry LLM if all fail."""
    # Example usage:
    rules = load_structure_rules(STRUCTURE_PROMPTS_YAML)

    attempt = 0
    with mlflow.start_run(nested=True):
        mlflow.log_param(f"{task}_max_attempts", max_attempts)
        while attempt < max_attempts:
            for i, output in enumerate(ranked_outputs):
                if verify_structure(output, task, rules):
                    mlflow.log_metric(f"{task}_verification_attempts", attempt + 1)
                    mlflow.log_text(output, f"{task}_verified_output.txt")
                    return output
            attempt += 1
            ranked_outputs = rank_all_outputs(
                process_email_body(body, [task], userEmail), [task], body
            )[task]
            mlflow.log_metric(f"{task}_regen_attempts", attempt)
        mlflow.log_text(ranked_outputs[0], f"{task}_fallback_output.txt")
        return ranked_outputs[0]  # Fallback


def verify_all_outputs(ranked_outputs_dict, tasks, body, userEmail):
    """Verify and select best output for each task."""

    best_output = {}
    for task in tasks:
        best_output[task] = get_best_output(
            ranked_outputs_dict[task], task, body, userEmail
        )
    return best_output


# if __name__ == "__main__":

#     body = """
#         Checked out
#         ---------- Forwarded message ---------
#         From: Try <try8200@gmail.com>
#         Date: Sun, Mar 9, 2025 at 8:41 PM
#         Subject: Fwd: Test
#         To: Shubh Desai <shubhdesai111@gmail.com>


#         Check out this
#         ---------- Forwarded message ---------
#         From: Shubh Desai <shubhdesai111@gmail.com>
#         Date: Sun, Mar 9, 2025 at 8:37 PM
#         Subject: Re: Test
#         To: Try <try8200@gmail.com>


#         Hey, once again

#         On Sun, Mar 9, 2025 at 8:36 PM Try <try8200@gmail.com> wrote:
#         hello Shubh

#         On Sun, Mar 9, 2025 at 8:35 PM Shubh Desai <shubhdesai111@gmail.com> wrote:
#         Hello Try
#         we have a meeting tomorrow at 10am, related to the project and its important to discuss the project and its progress
#         Also we have a important deadline for the project on 30th march of this month. So we need to speed up the process and complete the project on time.

#     """

#     # Test the output verifier
#     tasks = ["summary", "action_item", "draft_reply"]
#     userEmail = "try8200@gmail.com"
#     llm_outputs = process_email_body(body, tasks, userEmail)
#     ranked_outputs = rank_all_outputs(llm_outputs, tasks, body)
#     best_outputs = verify_all_outputs(ranked_outputs, tasks, body, userEmail)
#     for task, output in best_outputs.items():
#         print(f"\n\n{task.upper()} OUTPUT\n{output}\n\n")

#     # print(best_outputs)
