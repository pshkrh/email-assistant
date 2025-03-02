import pandas as pd
import re

from create_logger import create_logger


# Function to classify emails as 'original', 'reply', or 'forward'
def classify_email_type(body, subject):
    subject = subject.lower() if pd.notna(subject) else ""
    if re.search(
        r"-----\s*Forwarded Message\s*-----", body, re.IGNORECASE
    ) or subject.startswith(("fw:", "fwd:")):
        return "forward"
    elif re.search(
        r"-----\s*Original Message\s*-----", body, re.IGNORECASE
    ) or subject.startswith("re:"):
        return "reply"
    return "original"


# Function to split an email thread while keeping full email content
def split_email_thread(email_body):
    emails = re.split(
        r"(?=\n*-{3,}.*?(Original Message|Forwarded Message|From:|Sent:|To:|Cc:|Subject:))",
        email_body,
        flags=re.IGNORECASE,
    )
    return [
        email.strip() for email in emails if email.strip() and len(email.strip()) > 20
    ]


# Function to clean the `Body` column (removing \n, \t, and extra spaces)
def clean_body(text):
    if pd.isna(text):
        return ""
    text = text.replace("\n", " ").replace("\t", " ")
    return " ".join(text.split())


def data_clean(input_file, output_file, path, logger_name):

    data_cleaning_logger = create_logger(path, logger_name)

    # Chunk size (adjust based on your memory capacity, e.g., 1000-5000 rows)
    chunk_size = 1000

    data_cleaning_logger.info("Starting email processing...")

    # Process the CSV in chunks
    first_chunk = True
    total_emails_processed = 0
    total_threads_extracted = 0

    for chunk_number, chunk in enumerate(
        pd.read_csv(input_file, chunksize=chunk_size, low_memory=False)
    ):
        data_cleaning_logger.info(
            f"Processing chunk {chunk_number + 1} with {len(chunk)} rows..."
        )

        new_rows = []

        # Process each email in the chunk
        for index, row in chunk.iterrows():
            email_body = row["Body"] if pd.notna(row["Body"]) else ""
            subject = row["Subject"] if pd.notna(row["Subject"]) else ""
            thread_id = row["Message-ID"]

            # Clean the email body
            email_body = clean_body(email_body)

            # Check if email contains replies or forwards
            if (
                "-----Original Message-----" in email_body
                or "----- Forwarded Message -----" in email_body
            ):
                split_emails = split_email_thread(email_body)
                total_threads_extracted += len(split_emails)

                for i, email in enumerate(split_emails):
                    email = clean_body(email)
                    if email in [">", "-", "original message"] or len(email) < 20:
                        continue

                    new_row = row.copy()
                    new_row["Body"] = email
                    new_row["thread_id"] = thread_id
                    new_row["email_part"] = i + 1
                    new_row["email_type"] = classify_email_type(email, subject)
                    new_rows.append(new_row.to_dict())  # Convert to dict for efficiency
            else:
                row["Body"] = email_body
                row["thread_id"] = thread_id
                row["email_part"] = 1
                row["email_type"] = classify_email_type(email_body, subject)
                new_rows.append(row.to_dict())

        total_emails_processed += len(new_rows)
        data_cleaning_logger.info(
            f"Chunk {chunk_number + 1} processed: {len(new_rows)} emails extracted."
        )

        # Convert chunk to DataFrame and write to CSV
        chunk_df = pd.DataFrame(new_rows)
        if first_chunk:
            chunk_df.to_csv(
                output_file, mode="w", index=False
            )  # Overwrite for first chunk
            first_chunk = False
        else:
            chunk_df.to_csv(
                output_file, mode="a", header=False, index=False
            )  # Append subsequent chunks

        # Clear memory
        del chunk_df
        del new_rows

    data_cleaning_logger.info("Processing complete!")
    data_cleaning_logger.info(f"Total emails processed: {total_emails_processed}")
    data_cleaning_logger.info(
        f"Total email threads extracted: {total_threads_extracted}"
    )
    data_cleaning_logger.info(f"Final cleaned dataset saved to: {output_file}")


if __name__ == "__main__":
    # File paths
    input_file = "./data_pipeline/data/enron_emails.csv"
    output_file = "./data_pipeline/data/processed_enron_emails_ver14.csv"
    path = "./data_pipeline/logs/data_clean_log.log"
    logger_name = "data_cleaning_logger"
    data_clean(input_file, output_file, path, logger_name)
