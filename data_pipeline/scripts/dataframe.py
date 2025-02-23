import os
import pandas as pd
import email
# Path to the extracted dataset
MAILDIR_PATH = "enron_dataset/maildir"

# Headers to extract
HEADER_KEYS = ["Message-ID", "Date", "From", "To", "Subject", "Cc", "Bcc", "X-From", "X-To", "X-Cc"]

# Extracts metadata and full email body from an email file.
def extract_email_data(email_path):
    
    with open(email_path, "r", encoding="utf-8", errors="ignore") as f:
        msg = email.message_from_file(f)

    # Extract metadata
    email_data = {key: msg.get(key, None) for key in HEADER_KEYS}

    # Extract the email body (handle multipart and plain text emails)
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":  # Extract plain text content
                try:
                    body_parts.append(part.get_payload(decode=True).decode(errors="ignore"))
                except Exception:
                    pass  # Skip problematic encodings
    else:
        try:
            body_parts.append(msg.get_payload(decode=True).decode(errors="ignore"))
        except Exception:
            pass  # Skip problematic encodings

    # Join all body parts, keeping forwarded messages intact
    email_data["Body"] = "\n".join(body_parts).strip()
    return email_data

# Loop through all folders and extract emails into a DataFrame.
def process_enron_emails(data_dir):
    
    email_list = []
    total_files = 0

    if not os.path.exists(data_dir):
        print(f"ERROR: Directory {data_dir} does not exist!")
        return pd.DataFrame()

    print(f"Processing emails in: {data_dir}")

    for root, _, files in os.walk(data_dir):
        print(f"Scanning directory: {root}")  # Debugging print

        for file in files:
            email_path = os.path.join(root, file)
            total_files += 1
            try:
                email_data = extract_email_data(email_path)
                email_list.append(email_data)
            except Exception as e:
                print(f"Error processing {email_path}: {e}")

    print(f"Total emails processed: {total_files}")

    # Convert to Pandas DataFrame
    df = pd.DataFrame(email_list)
    return df

if __name__ == "__main__":
    # Process all emails
    df_enron = process_enron_emails(MAILDIR_PATH)
