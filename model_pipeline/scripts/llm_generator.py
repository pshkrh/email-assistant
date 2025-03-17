import sys
import os
import json
import yaml
import mlflow
import pandas as pd
from jinja2 import Template
from tqdm import tqdm
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from google.auth import load_credentials_from_file
import re

# Ensure correct module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.get_project_root import project_root
from scripts.load_prompts import load_prompts
from scripts.render_prompt import render_prompt

load_dotenv()

# GCP settings
GCP_LOCATION = os.getenv("GCP_LOCATION")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
PROJECT_ROOT_DIR = project_root()

# Path to service account JSON file
SERVICE_ACCOUNT_FILE = os.path.join(
    PROJECT_ROOT_DIR, "model_pipeline", "credentials", "GoogleCloudCredential.json"
)
CREDENTIALS, GCP_PROJECT_ID = load_credentials_from_file(SERVICE_ACCOUNT_FILE)

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION, credentials=CREDENTIALS)

"""
Prompts, LLM request code, 
"""


def generate_outputs(task, prompt):
    """Generate 3 outputs for a given task using LLM."""
    outputs = []
    with mlflow.start_run(nested=True):
        mlflow.log_param(f"{task}_prompt", prompt)

        for i in range(3):
            model = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002"))
            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # ✅ Strictly check if response is structured JSON
            if response_text.startswith("{"):
                try:
                    structured_data = json.loads(response_text)
                except json.JSONDecodeError:
                    structured_data = {task: f"No {task} (Invalid JSON format)"}
            else:
                # ✅ If response does not follow expected format, enforce fallback
                structured_data = {task: response_text}
                
                # 🔹 Ensure proper structure for `summary`, `draft_reply`, and `action_items`
                if task == "summary" and not re.match(r"summary:\s*-", response_text):
                    structured_data = {task: f"No {task} (Unstructured response)"}
                elif task == "draft_reply" and "Dear" not in response_text:
                    structured_data = {task: f"No {task} (Invalid reply format)"}
                elif task == "action_item" and not re.match(r"action_item:\s*-", response_text):
                    structured_data = {task: f"No {task} (Unstructured response)"}

            outputs.append(structured_data[task])
            mlflow.log_text(structured_data[task], f"{task}_output_{i}.txt")

        mlflow.log_param(f"{task}_output_count", len(outputs))

    return outputs



def process_email_body(body, tasks, user_email="try8200@gmail.com"):
    """Generate outputs for all tasks."""
    prompt_file_path = os.path.join(
        project_root(), "model_pipeline", "data", "llm_generator_prompts.yaml"
    )

    try:
        prompts = load_prompts(prompt_file_path)
    except FileNotFoundError:
        print(f"Warning: Prompt file '{prompt_file_path}' not found.")
        return {}
    except Exception as e:
        print(f"Unexpected error while loading prompts: {e}")
        return {}

    llm_outputs = {}

    for task in tasks:
        if task not in prompts:
            llm_outputs[task] = f"No prompt found for task: {task}"
            continue

        try:
            full_prompt = render_prompt(prompts[task], body, user_email)
            llm_outputs[task] = generate_outputs(task, full_prompt)
        except Exception as e:
            print(f"⚠️ Error while processing task '{task}': {e}")
            llm_outputs[task] = f"Error generating output for {task}"

    return llm_outputs


if __name__ == "__main__":
    body = """
    Checked out
    ---------- Forwarded message ---------
    From: Try <try8200@gmail.com>
    Date: Sun, Mar 9, 2025 at 8:41 PM
    Subject: Fwd: Test
    To: Shubh Desai <shubhdesai111@gmail.com>

    Check out this
    ---------- Forwarded message ---------
    From: Shubh Desai <shubhdesai111@gmail.com>
    Date: Sun, Mar 9, 2025 at 8:37 PM
    Subject: Re: Test
    To: Try <try8200@gmail.com>

    Hey Try, Can you give me avalibility for interview?

    On Sun, Mar 9, 2025 at 8:36 PM Try <try8200@gmail.com> wrote:
    hello Shubh, Yes I am available in the next week Monday 9AM to 4PM, and Tuesday 12AM to  5PM.

    On Sun, Mar 9, 2025 at 8:35 PM Shubh Desai <shubhdesai111@gmail.com> wrote:
    Hello Try, according to your availibility I would like to arrange interview on Tuesday 10am to 10:30am.
    """
    
    tasks = ["draft_reply", "summary"]
    llm_outputs = process_email_body(body, tasks)
    print("LLM OUTPUTS: ", llm_outputs)
    for output in llm_outputs["draft_reply"]:
        print("\n-----------\n", output, "\n-------------\n")
    for output in llm_outputs["summary"]:
        print("\n-----------\n", output, "\n-------------\n")
