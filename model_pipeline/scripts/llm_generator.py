# model_pipeline/llm_generator.py
import json
import yaml
import os
import mlflow
import pandas as pd
from jinja2 import Template
from tqdm import tqdm
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from google.auth import load_credentials_from_file
from config import (
    SERVICE_ACCOUNT_FILE,
    GENERATOR_PROMPTS_YAML,
    ALTERNATE_GENERATOR_PROMPTS_YAML,
    MODEL_ENV_PATH,
)
from load_prompts import load_prompts
from render_prompt import render_prompt
from render_alternate_prompt import render_alternate_prompt

load_dotenv(dotenv_path=MODEL_ENV_PATH)

# GCP settings
GCP_LOCATION = os.getenv("GCP_LOCATION")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

CREDENTIALS, GCP_PROJECT_ID = load_credentials_from_file(SERVICE_ACCOUNT_FILE)

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION, credentials=CREDENTIALS)

"""
Prompts, LLM request code, 
"""


def generate_outputs(task, prompt):
    """Generate 3 outputs for a given task using LLM."""
    outputs = []
    with mlflow.start_run(nested=True):  # Nested run for each task
        mlflow.log_param(f"{task}_prompt", prompt)

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
                    raise ValueError("Empty response from LLM.")

                # Attempt to parse JSON response
                if response_text.startswith("{"):
                    structured_data = json.loads(response_text)
                else:
                    # Fallback: try to extract from raw format
                    if f"{task}:" in response_text:
                        content = (
                            response_text.split(f"{task}:")[1].split("```")[0].strip()
                        )
                    else:
                        content = f"[Fallback] No {task} detected."

                    structured_data = {task: content}

                output = structured_data.get(task, f"[Missing key '{task}']")
                outputs.append(output)
                mlflow.log_text(output, f"{task}_output_{i}.txt")

            except Exception as e:
                fallback_msg = f"[Error] Failed to generate output: {str(e)}"
                outputs.append(fallback_msg)
                mlflow.log_text(fallback_msg, f"{task}_output_{i}_error.txt")
                print(f"Generation failed for output {i}: {e}")

        mlflow.log_param(f"{task}_output_count", len(outputs))
    return outputs


def get_prompt_for_task(task, strategy="default"):
    if strategy == "default":
        prompts = load_prompts(GENERATOR_PROMPTS_YAML)
    else:
        prompts = load_prompts(ALTERNATE_GENERATOR_PROMPTS_YAML)

    return prompts.get(task)


def process_email_body(body, task, user_email, prompt_strategy, negative_examples):
    """Generate outputs for all tasks."""

    llm_outputs = {}

    # Use with statement to automatically close the file
    try:
        # Loop through each task and generate the output
        prompt_style = prompt_strategy.get(task, "default")
        selected_prompt = get_prompt_for_task(task, strategy=prompt_style)

        full_prompt = ""
        if prompt_style == "default":
            full_prompt = f"""
            {render_prompt(selected_prompt, body, user_email)}
        """
        else:
            full_prompt = f"""
            {render_alternate_prompt(selected_prompt, body, user_email, negative_examples)}
        """

        if full_prompt and selected_prompt:
            llm_outputs[task] = generate_outputs(task, full_prompt)
        else:
            raise ValueError(f"No prompt found or invalid for task: {task}")

        return llm_outputs

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Error: The file {GENERATOR_PROMPTS_YAML} does not exist."
        )
    except yaml.YAMLError as e:
        raise ValueError(f"YAML loading error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error in process_email_body: {str(e)}") from e


# if __name__ == "__main__":
#     body = """
#     Checked out
#     ---------- Forwarded message ---------
#     From: Try <try8200@gmail.com>
#     Date: Sun, Mar 9, 2025 at 8:41 PM
#     Subject: Fwd: Test
#     To: Shubh Desai <shubhdesai111@gmail.com>

#     Check out this
#     ---------- Forwarded message ---------
#     From: Shubh Desai <shubhdesai111@gmail.com>
#     Date: Sun, Mar 9, 2025 at 8:37 PM
#     Subject: Re: Test
#     To: Try <try8200@gmail.com>

#     Hey, once again

#     On Sun, Mar 9, 2025 at 8:36 PM Try <try8200@gmail.com> wrote:
#     hello Shubh

#     On Sun, Mar 9, 2025 at 8:35 PM Shubh Desai <shubhdesai111@gmail.com> wrote:
#     Hello Try
#     """

# tasks = ["summary", "draft_reply", "action_items"]
# llm_outputs = process_email_body(body, tasks)
# print("LLM OUTPUTS: ", llm_outputs)

# for output in llm_outputs["draft_reply"]:
#     print("\n-----------\n", output, "\n-------------\n")
# for output in llm_outputs["summary"]:
#     print("\n-----------\n", output, "\n-------------\n")
