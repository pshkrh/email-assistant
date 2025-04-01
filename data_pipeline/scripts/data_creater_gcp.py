import os
import time
import json
import pandas as pd
import yaml
from jinja2 import Template
from tqdm import tqdm
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from multiprocessing import Pool

# -----------------------------------------------------------------------------
# Configuration & Initialization
# -----------------------------------------------------------------------------

# Load environment variables from .env file
load_dotenv()

# GCP settings
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION") 
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# Ensure credentials are set correctly
if not GCP_PROJECT_ID or not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise ValueError("Google Cloud credentials or project ID not set! Check your .env file.")

# File paths
INPUT_FILES = {
    "short": "./data_pipeline/data/enron_balanced_short_emails.csv",
    "medium": "./data_pipeline/data/enron_balanced_medium_emails.csv",
    "long": "./data_pipeline/data/enron_balanced_long_emails.csv",
}
OUTPUT_FOLDER = "./data_pipeline/data/"
FINAL_OUTPUT_CSV = os.path.join(OUTPUT_FOLDER, "enron_all_processed_emails.csv")

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

def load_prompts(filename):
    """Load prompt templates from a YAML file."""
    with open(filename, "r") as file:
        return yaml.safe_load(file)

def render_prompt(template_str, email_thread):
    """Render a Jinja2 prompt template."""
    template = Template(template_str)
    return template.render(email_thread=email_thread)

def call_gemini(prompt):
    """Sends a single request to Gemini and expects a structured JSON response."""
    try:
        model = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002"))
        response = model.generate_content(prompt)

        # Extract text response and attempt to parse it as JSON
        response_text = response.text.strip()
        
        # Ensure structured response formatting
        structured_data = json.loads(response_text) if response_text.startswith("{") else {
            "summary": response_text.split("Summary:")[1].split("Suggested Reply:")[0].strip() if "Summary:" in response_text else "No summary",
            "suggested_reply": response_text.split("Suggested Reply:")[1].split("Action Items:")[0].strip() if "Suggested Reply:" in response_text else "No reply",
            "action_items": response_text.split("Action Items:")[1].strip().split("\n") if "Action Items:" in response_text else []
        }

        return structured_data
    
    except json.JSONDecodeError:
        print("Error parsing response from Gemini. Returning default structure.")
        return {
            "summary": "Failed to generate summary.",
            "suggested_reply": "Failed to generate reply.",
            "action_items": []
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return {
            "summary": "API Error",
            "suggested_reply": "API Error",
            "action_items": []
        }

# -----------------------------------------------------------------------------
# Parallel Processing Function
# -----------------------------------------------------------------------------

def process_emails(file_key):
    """Processes emails using Gemini model with parallel execution for each CSV file."""
    input_csv = INPUT_FILES[file_key]
    output_csv = os.path.join(OUTPUT_FOLDER, f"processed_{file_key}.csv")

    if not os.path.exists(input_csv):
        print(f"❌ File not found: {input_csv}")
        return None

    print(f"🚀 Processing {file_key} emails from {input_csv}")

    # Load prompts
    prompts = load_prompts("prompts.yaml")

    # Load email data
    df = pd.read_csv(input_csv)

    # Ensure necessary columns exist
    for col in ["Action Label", "Action Type", "Summary", "Suggested Reply"]:
        if col not in df.columns:
            df[col] = ""

    # Process each email
    for index, row in tqdm(df.iterrows(), total=len(df), desc=f"Processing {file_key} Emails"):
        if pd.notna(row["Summary"]) and pd.notna(row["Suggested Reply"]) and pd.notna(row["Action Label"]):
            continue  # Skip already processed rows

        email_thread = f"Subject: {row['Subject']}\n\n{row['Body']}"

        # Create a single structured request by merging all prompts
        full_prompt = f"""
        {render_prompt(prompts["summarization_prompt"], email_thread)}

        {render_prompt(prompts["draft_reply_prompt"], email_thread)}

        {render_prompt(prompts["action_items_prompt"], email_thread)}

        Please structure the response in the following format:
        ```
        Summary: <summary_text_here>

        Suggested Reply: <suggested_reply_here>

        Action Items: <action_items_here>
        ```
        """

        # Call Gemini API once and parse response
        response_data = call_gemini(full_prompt)

        # Extract structured responses
        df.at[index, "Summary"] = response_data.get("summary", "No summary provided.")
        df.at[index, "Suggested Reply"] = response_data.get("suggested_reply", "No reply generated.")
        df.at[index, "Action Type"] = "; ".join(response_data.get("action_items", []))

    # Save results
    df.to_csv(output_csv, index=False)
    print(f"✅ Processing complete for {file_key}! Results saved to '{output_csv}'")

    return output_csv

# -----------------------------------------------------------------------------
# Run Parallel Processing
# -----------------------------------------------------------------------------

def run_parallel_processing():
    """Runs email processing for all files in parallel and merges results."""
    with Pool(processes=len(INPUT_FILES)) as pool:
        output_files = pool.map(process_emails, INPUT_FILES.keys())

    # Merge results into a single CSV file
    merge_csv_files([f for f in output_files if f is not None])

def merge_csv_files(file_list):
    """Merges multiple processed CSV files into one."""
    if not file_list:
        print("❌ No files to merge!")
        return

    combined_df = pd.concat([pd.read_csv(file) for file in file_list], ignore_index=True)
    combined_df.to_csv(FINAL_OUTPUT_CSV, index=False)
    
    print(f"\n✅ All processed emails merged into {FINAL_OUTPUT_CSV}")

# -----------------------------------------------------------------------------
# Run the Script
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    run_parallel_processing()