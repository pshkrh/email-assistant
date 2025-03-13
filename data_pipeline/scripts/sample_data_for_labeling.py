import os
import pandas as pd
import random

# File Paths
DATASET_PATH = "./data_pipeline/data/enron_emails.csv" 
SAMPLED_DATA_PATH = "./data_pipeline/data/enron_sampled_for_labeling.csv"

# Keywords to identify actionable emails
KEYWORDS = ["please", "action required", "follow up", "due date", "urgent", "approve", "schedule", "review"]

def load_email_data():
    """Loads the Enron dataset and selects relevant columns."""
    if not os.path.exists(DATASET_PATH):
        print(f"Error: {DATASET_PATH} not found!")
        return None

    df = pd.read_csv(DATASET_PATH, usecols=["Message-ID", "Subject", "Body"])
    print(f"Loaded {len(df)} emails from {DATASET_PATH}")
    return df

def filter_emails(df):
    """Filters emails that contain action-related keywords."""
    df_filtered = df[df["Body"].str.contains('|'.join(KEYWORDS), case=False, na=False)]
    print(f"Filtered {len(df_filtered)} emails containing action-related keywords.")
    return df_filtered

def sample_emails(df_filtered, sample_size=10):
    """Samples a subset of emails for labeling."""
    df_sample = df_filtered.sample(n=sample_size, random_state=42) if len(df_filtered) > sample_size else df_filtered
    print(f"Sampled {len(df_sample)} emails for labeling.")
    return df_sample

def save_sampled_data(df_sample):
    """Saves the sampled emails to a new CSV file for manual labeling."""
    df_sample["Action Label"] = ""  # Empty column for manual labeling
    df_sample["Action Type"] = ""  # Empty column for type of action (optional)
    df_sample["Summary"] = ""  # Empty column for summaries (optional)
    df_sample["Suggested Reply"] = ""  # Empty column for draft reply (optional)

    df_sample.to_csv(SAMPLED_DATA_PATH, index=False)
    print(f"Saved sampled emails to {SAMPLED_DATA_PATH}")

if __name__ == "__main__":
    df = load_email_data()
    if df is not None:
        df_filtered = filter_emails(df)
        df_sample = sample_emails(df_filtered)
        save_sampled_data(df_sample)
