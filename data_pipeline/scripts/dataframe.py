import os
import pandas as pd
import email
import multiprocessing
from pathlib import Path
from functools import partial
from concurrent.futures import ProcessPoolExecutor

# Paths
MAILDIR_PATH = "dataset/maildir"
DATA_DIR = "dataset"
CSV_OUTPUT_PATH = os.path.join(DATA_DIR, "enron_emails.csv")
CHUNK_SIZE = 10000  # Save every 10,000 emails to reduce memory usage

# Headers to extract
HEADER_KEYS = ["Message-ID", "Date", "From", "To", "Subject", "Cc", "Bcc", "X-From", "X-To", "X-Cc"]

# Extracts metadata and full email body from an email file.
def extract_email_data(email_path):
    try:
        with open(email_path, "rb") as f:  # Read in binary mode for better performance
            msg = email.message_from_bytes(f.read())  # Faster than message_from_file

        # Extract metadata
        email_data = {key: msg.get(key, None) for key in HEADER_KEYS}

        # Extract body
        body_parts = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body_parts.append(part.get_payload(decode=True).decode(errors="ignore"))
        else:
            body_parts.append(msg.get_payload(decode=True).decode(errors="ignore"))

        email_data["Body"] = "\n".join(filter(None, body_parts)).strip()
        return email_data

    except Exception as e:
        print(f"Error processing {email_path}: {e}")
        return None

# Process emails using multiprocessing
def process_enron_emails_parallel(maildir_path, num_workers=8):
    email_files = [f for f in Path(maildir_path).rglob("*") if f.is_file()]  # ✅ Ignore directories
    total_files = len(email_files)
    print(f"Total emails found: {total_files}")

    if total_files == 0:
        print("No emails found!")
        return pd.DataFrame()

    results = []
    batch_counter = 0

    # Process emails in parallel
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for email_data in executor.map(extract_email_data, email_files):
            if email_data:
                results.append(email_data)

            # Save periodically to reduce memory usage
            if len(results) >= CHUNK_SIZE:
                df_chunk = pd.DataFrame(results)
                df_chunk.to_csv(CSV_OUTPUT_PATH, mode='a', header=not os.path.exists(CSV_OUTPUT_PATH), index=False, encoding="utf-8")
                batch_counter += 1
                print(f"Saved batch {batch_counter} ({CHUNK_SIZE} emails)")
                results.clear()  # Clear memory

    # Save remaining emails
    if results:
        df_final = pd.DataFrame(results)
        df_final.to_csv(CSV_OUTPUT_PATH, mode='a', header=not os.path.exists(CSV_OUTPUT_PATH), index=False, encoding="utf-8")
        print(f"Saved final batch ({len(results)} emails)")

    print(f"Processing complete! Data saved to {CSV_OUTPUT_PATH}")

if __name__ == "__main__":
    process_enron_emails_parallel(MAILDIR_PATH, num_workers=8)
