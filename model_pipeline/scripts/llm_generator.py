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
from config import SERVICE_ACCOUNT_FILE, GENERATOR_PROMPTS_YAML, MODEL_ENV_PATH
from load_prompts import load_prompts
from render_prompt import render_prompt

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
            model = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002"))
            response = model.generate_content(prompt)
            # Extract text response and attempt to parse it as JSON
            response_text = response.text.strip()
            # Ensure structured response formatting
            structured_data = (
                json.loads(response_text)
                if response_text.startswith("{")
                else {
                    task: (
                        response_text.split(f"{task}:")[1].split("```")[0]
                        if f"{task}:" in response_text
                        else f"No {task}"
                    )
                }
            )
            outputs.append(structured_data[task])
            mlflow.log_text(structured_data[task], f"{task}_output_{i}.txt")
        mlflow.log_param(f"{task}_output_count", len(outputs))
    return outputs


def process_email_body(body, tasks, user_email):
    """Generate outputs for all tasks."""

    prompts = load_prompts(GENERATOR_PROMPTS_YAML)

    llm_outputs = {}

    # Use with statement to automatically close the file
    try:
        # Loop through each task and generate the output
        for task in tasks:
            full_prompt = f"""
                {render_prompt(prompts[task], body, user_email)}
            """
            if full_prompt:
                llm_outputs[task] = generate_outputs(task, full_prompt)
            else:
                llm_outputs[task] = f"No prompt found for task: {task}"

        return llm_outputs

    except FileNotFoundError:
        print(f"Error: The file {GENERATOR_PROMPTS_YAML} does not exist.")
        return llm_outputs
    except Exception as e:
        print(f"Unexpected error: {e}")
        return llm_outputs


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
