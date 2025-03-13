import os
import time
import pandas as pd
import yaml
from jinja2 import Template
from tqdm import tqdm
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

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
INPUT_CSV = "./data_pipeline/data/enron_sampled_for_labeling.csv"
OUTPUT_CSV = "./data_pipeline/data/enron_sampled_for_labeling_labeled_gcp.csv"

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

def load_prompts(filename="prompts.yaml"):
    """Load prompt templates from a YAML file."""
    with open(filename, "r") as file:
        return yaml.safe_load(file)

def render_prompt(template_str, email_thread):
    """Render a Jinja2 prompt template."""
    template = Template(template_str)
    return template.render(email_thread = email_thread)

def call_gemini(prompt):
    """Call Gemini model using Vertex AI API."""
    try:
        model = GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        return response.text.strip() if response.text else "No response generated"
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return "API Error"

# -----------------------------------------------------------------------------
# Main Processing Function
# -----------------------------------------------------------------------------

def process_emails():
    """Processes emails using Gemini model and saves responses to CSV."""
    # Load prompts
    prompts = load_prompts()

    # Load email data
    df = pd.read_csv(INPUT_CSV)

    # Ensure necessary columns exist
    for col in ["Action Label", "Action Type", "Summary", "Suggested Reply"]:
        if col not in df.columns:
            df[col] = ""

    # Process each email
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing Emails"):
        if pd.notna(row["Summary"]) and pd.notna(row["Suggested Reply"]) and pd.notna(row["Action Label"]):
            continue  # Skip already processed rows

        email_thread = f"Subject: {row['Subject']}\n\n{row['Body']}"

        # Generate prompts
        summary_prompt = render_prompt(prompts["summarization_prompt"], email_thread)
        reply_prompt = render_prompt(prompts["draft_reply_prompt"], email_thread)
        action_prompt = render_prompt(prompts["action_items_prompt"], email_thread)

        # Call Gemini API
        df.at[index, "Summary"] = call_gemini(summary_prompt)
        df.at[index, "Suggested Reply"] = call_gemini(reply_prompt)
        df.at[index, "Action Label"] = call_gemini(action_prompt)
        df.at[index, "Action Type"] = "Action Required"  # Adjust logic if needed

        time.sleep(1)  # Rate limiting

    # Save results
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nProcessing complete! Results saved")

# -----------------------------------------------------------------------------
# Run the Script
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    process_emails(user_email="your_email@example.com")