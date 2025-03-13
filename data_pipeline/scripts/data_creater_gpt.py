import pandas as pd

# Load CSV into DataFrame
df = pd.read_csv("./data_pipeline/data/enron_sampled_for_labeling.csv")

import os
import pandas as pd
import openai
import yaml
from jinja2 import Template
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_APPLICATION_CREDENTIALS = os.getenv("OPENAI_APPLICATION_CREDENTIALS")

# Validate API Key
if not OPENAI_APPLICATION_CREDENTIALS:
    raise ValueError("Missing OpenAI API Key! Set it in .env file.")

# Load OpenAI API Key
openai.api_key = OPENAI_APPLICATION_CREDENTIALS

# Load Prompts from YAML
def load_prompts(filename="prompts.yaml"):
    with open(filename, "r") as file:
        return yaml.safe_load(file)

prompts = load_prompts()

# Define Jinja2 Rendering Function
def render_prompt(template_str, email_thread, user_email="your_email@example.com"):
    template = Template(template_str)
    return template.render(email_thread=email_thread, user_email=user_email)

# OpenAI API Call Function
def call_openai(prompt):
    try:
        client = openai.OpenAI(api_key=OPENAI_APPLICATION_CREDENTIALS)  # Correct new syntax
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            # temperature=0.7,
            # max_tokens=200  # Adjust based on need
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return "API Error"

# Load Email Data
df = pd.read_csv("./data_pipeline/data/enron_sampled_for_labeling.csv")

# Ensure required columns exist
if "Subject" not in df.columns or "Body" not in df.columns:
    raise ValueError("CSV must contain 'Subject' and 'Body' columns!")

# Add missing result columns if they don't exist
for col in ["Action Label", "Action Type", "Summary", "Suggested Reply"]:
    if col not in df.columns:
        df[col] = ""

# Process Each Email
for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing Emails"):
    email_thread = f"Subject: {row['Subject']}\n\n{row['Body']}"

    # Render Prompts
    summary_prompt = render_prompt(prompts["summarization_prompt"], email_thread)
    reply_prompt = render_prompt(prompts["draft_reply_prompt"], email_thread)
    action_prompt = render_prompt(prompts["action_items_prompt"], email_thread)

    # Get API Responses
    summary_response = call_openai(summary_prompt)
    # draft_reply_response = call_openai(reply_prompt)
    # action_response = call_openai(action_prompt)

    # Populate DataFrame
    df.at[index, "Summary"] = "summary_response"
    df.at[index, "Suggested Reply"] = "draft_reply_response"
    df.at[index, "Action Label"] = "action_response" # Adjust if parsing needed
    df.at[index, "Action Type"] = "Action Required"  # Modify if needed

# Save Updated CSV
df.to_csv("./data_pipeline/data/enron_sampled_for_labeling_labeled.csv", index=False)
print("\nProcessing Complete! Results saved to 'enron_sampled_for_labeling_labeled.csv'")