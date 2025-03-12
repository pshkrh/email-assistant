import os
import pandas as pd
import spacy
from tqdm import tqdm

# Load Spacy NLP Model
nlp = spacy.load("en_core_web_sm")

# File Paths
INPUT_CSV_PATH = "dataset/enron_summarized.csv"  # Input file with emails
OUTPUT_CSV_PATH = "dataset/enron_action_verbs.csv"  # Output file with action verbs

# Define Function to Extract Action Verbs
def extract_action_verbs(text):
    """Extracts verbs related to actions from an email body."""
    if not isinstance(text, str) or text.strip() == "":
        return ""

    doc = nlp(text)
    action_verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]  # Extract verbs (base form)
    
    return ", ".join(set(action_verbs))  # Convert list to comma-separated string

# Process Emails for Action Verbs
def process_emails_for_verbs(input_csv, output_csv):
    """Processes emails and extracts action verbs per email."""
    if not os.path.exists(input_csv):
        print(f"Error: {input_csv} not found!")
        return

    df = pd.read_csv(input_csv, usecols=["Message-ID", "Body"])  # Load necessary columns
    print(f"Processing {len(df)} emails for action verbs...")

    # Extract action verbs for each email
    df["Action Verbs"] = df["Body"].apply(lambda text: extract_action_verbs(text))

    # Save the updated dataframe
    df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"✅ Action verbs extracted and saved to {output_csv}")

if __name__ == "__main__":
    process_emails_for_verbs(INPUT_CSV_PATH, OUTPUT_CSV_PATH)
