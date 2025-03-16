import os
import pandas as pd

# File Paths
DATASET_PATH = "./data_pipeline/data/enron_emails.csv" 
BALANCED_SHORT_EMAIL_PATH = "./data_pipeline/data/enron_balanced_short_emails.csv"
BALANCED_MEDIUM_EMAIL_PATH = "./data_pipeline/data/enron_balanced_medium_emails.csv"
BALANCED_LONG_EMAIL_PATH = "./data_pipeline/data/enron_balanced_long_emails.csv"

# Minimum required emails per category
MIN_COUNT = 3500

def load_email_data():
    """Loads the Enron dataset and selects relevant columns."""
    if not os.path.exists(DATASET_PATH):
        print(f"Error: {DATASET_PATH} not found!")
        return None
    df = pd.read_csv(DATASET_PATH, usecols=["Message-ID", "Subject", "Body"])
    print(f"Loaded {len(df)} emails from {DATASET_PATH}")
    return df

def categorize_email_body_length(df):
    """Categorizes emails into short, medium, and long based on body length."""
    bins = [0, 700, 1500, float('inf')]  # Define thresholds
    labels = ["Short", "Medium", "Long"]

    df["Body Length"] = df["Body"].astype(str).apply(len)
    df["Body Category"] = pd.cut(df["Body Length"], bins=bins, labels=labels, right=False)
    
    return df

def rebalance_and_save_emails(df):
    """Balances and saves emails into separate CSV files."""
    # Sample emails per category
    sampled_dfs = {}
    for category in ["Short", "Medium", "Long"]:
        category_df = df[df["Body Category"] == category]
        sampled_dfs[category] = category_df.sample(n=min(MIN_COUNT, len(category_df)), random_state=42)

    # Drop unnecessary columns
    for key in sampled_dfs:
        sampled_dfs[key] = sampled_dfs[key].drop(columns=["Body Length", "Body Category"])

        # Add empty columns for manual labeling
        for col in ["Action Type", "Summary", "Suggested Reply"]:
            sampled_dfs[key][col] = ""

    # Save to CSV
    sampled_dfs["Short"].to_csv(BALANCED_SHORT_EMAIL_PATH, index=False)
    sampled_dfs["Medium"].to_csv(BALANCED_MEDIUM_EMAIL_PATH, index=False)
    sampled_dfs["Long"].to_csv(BALANCED_LONG_EMAIL_PATH, index=False)

    print("\nFinal Balanced Dataset:")
    print(f"Short Emails:  {len(sampled_dfs['Short'])} → {BALANCED_SHORT_EMAIL_PATH}")
    print(f"Medium Emails: {len(sampled_dfs['Medium'])} → {BALANCED_MEDIUM_EMAIL_PATH}")
    print(f"Long Emails:   {len(sampled_dfs['Long'])} → {BALANCED_LONG_EMAIL_PATH}")

if __name__ == "__main__":
    df = load_email_data()
    if df is not None:
        df = categorize_email_body_length(df)
        rebalance_and_save_emails(df)