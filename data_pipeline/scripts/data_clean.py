import pandas as pd
import re
import os
import gc
import time
import signal
import traceback
from create_logger import create_logger
from contextlib import contextmanager
from get_project_root import project_root

# Precompile regex patterns for better performance
FORWARDED_PATTERN = re.compile(r"-----\s*Forwarded Message\s*-----", re.IGNORECASE)
ORIGINAL_PATTERN = re.compile(r"-----\s*Original Message\s*-----", re.IGNORECASE)
THREAD_SPLIT_PATTERN = re.compile(
    r"(?=\n*-{3,}.*?(Original Message|Forwarded Message|From:|Sent:|To:|Cc:|Subject:))",
    re.IGNORECASE,
)


# Define a timeout handler
class TimeoutException(Exception):
    pass


@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


"""
Contains_forward c.._reply -> boolean columns
regex for \n and \t replace multiple with one occurence
"""


# Function to classify emails as 'original', 'reply', or 'forward'
def classify_email_type(body, subject):
    subject_lower = subject.lower() if pd.notna(subject) else ""

    # Use precompiled patterns
    if FORWARDED_PATTERN.search(body) or subject_lower.startswith(("fw:", "fwd:")):
        return "forward"
    elif ORIGINAL_PATTERN.search(body) or subject_lower.startswith("re:"):
        return "reply"
    return "original"


# Function to split an email thread while keeping full email content
def split_email_thread(email_body, logger):
    try:
        # Use precompiled pattern
        emails = THREAD_SPLIT_PATTERN.split(email_body)
        result = [
            email.strip()
            for email in emails
            if email.strip() and len(email.strip()) > 20
        ]
        return result
    except Exception as e:
        logger.error(f"Error splitting email thread: {str(e)}")
        return []


# Function to clean the `Body` column (removing \n, \t, and extra spaces)
def clean_body(text):
    if pd.isna(text):
        return ""
    # Combine operations to reduce string copies
    return " ".join(text.replace("\n", " ").replace("\t", " ").split())


def process_row(row, logger):
    """Process a single row and return new rows"""
    new_rows = []
    threads_extracted = 0

    try:
        email_body = row["Body"] if pd.notna(row["Body"]) else ""
        subject = row["Subject"] if pd.notna(row["Subject"]) else ""
        thread_id = row["Message-ID"]

        # Clean the email body first to reduce repeated operations
        email_body = clean_body(email_body)

        # Check for thread markers without repeated string operations
        contains_thread = (
            "-----Original Message-----" in email_body
            or "----- Forwarded Message -----" in email_body
        )

        if contains_thread:
            # Set a time limit for splitting the email thread
            try:
                with time_limit(5):  # 5 second timeout
                    split_emails = split_email_thread(email_body, logger)
            except TimeoutException:
                logger.warning(
                    f"Timeout while splitting email with ID: {thread_id}. Skipping split."
                )
                # Treat as a single email instead
                split_emails = []

            if split_emails:
                threads_extracted = len(split_emails)

                for i, email in enumerate(split_emails):
                    try:
                        email = clean_body(email)
                        if email in [">", "-", "original message"] or len(email) < 20:
                            continue

                        # Create a new row for each email part
                        new_row = row.copy()
                        new_row["Body"] = email
                        new_row["thread_id"] = thread_id
                        new_row["email_part"] = i + 1
                        new_row["email_type"] = classify_email_type(email, subject)
                        new_rows.append(new_row)
                    except Exception as e:
                        logger.error(f"Error processing thread part {i}: {str(e)}")
                        continue
            else:
                # Fallback for timeout or empty split result
                new_row = row.copy()
                new_row["Body"] = email_body
                new_row["thread_id"] = thread_id
                new_row["email_part"] = 1
                new_row["email_type"] = classify_email_type(email_body, subject)
                new_rows.append(new_row)
        else:
            # For single emails, just add the thread info
            new_row = row.copy()
            new_row["Body"] = email_body
            new_row["thread_id"] = thread_id
            new_row["email_part"] = 1
            new_row["email_type"] = classify_email_type(email_body, subject)
            new_rows.append(new_row)
    except Exception as e:
        logger.error(f"Error processing row: {str(e)}")
        # Try to recover by just returning the original row
        try:
            fallback_row = row.copy()
            fallback_row["thread_id"] = row.get("Message-ID", "unknown")
            fallback_row["email_part"] = 1
            fallback_row["email_type"] = "unknown"
            new_rows.append(fallback_row)
        except:
            logger.error("Failed to create fallback row")

    return new_rows, threads_extracted


def process_chunk(chunk, logger):
    """Process a single chunk of data and return the processed rows"""
    start_time = time.time()
    logger.info(f"Starting to process chunk with {len(chunk)} rows...")

    all_new_rows = []
    total_threads_extracted = 0

    # Process each row with detailed progress tracking
    for idx, (index, row) in enumerate(chunk.iterrows()):
        if idx % 100 == 0:
            logger.info(f"Processing row {idx}/{len(chunk)} in chunk...")

        try:
            # Set a time limit for processing each row
            try:
                with time_limit(10):  # 10 second timeout per row
                    new_rows, threads_extracted = process_row(row, logger)
            except TimeoutException:
                logger.warning(f"Timeout processing row at index {index}. Skipping.")
                continue

            all_new_rows.extend(new_rows)
            total_threads_extracted += threads_extracted

        except Exception as e:
            logger.error(f"Error processing row at index {index}: {str(e)}")
            logger.error(traceback.format_exc())
            continue

    # Create DataFrame from the list of Series objects
    if all_new_rows:
        result = pd.DataFrame(all_new_rows)
    else:
        # Return an empty DataFrame with the right columns if no rows
        result = pd.DataFrame(
            columns=chunk.columns.tolist() + ["thread_id", "email_part", "email_type"]
        )

    duration = time.time() - start_time
    logger.info(
        f"Chunk processing completed in {duration:.2f} seconds. Extracted {len(result)} rows."
    )

    return result, total_threads_extracted


def data_clean(input_file, output_file, path, logger_name):
    data_cleaning_logger = create_logger(path, logger_name)

    # Reduced chunk size to avoid memory issues
    chunk_size = 100

    data_cleaning_logger.info("Starting email processing...")

    # Check if the output file already exists and get the number of processed chunks
    start_chunk = 0
    if os.path.exists(output_file):
        try:
            # Count lines in the file to estimate processed chunks
            with open(output_file, "r") as f:
                # Subtract 1 for header
                processed_rows = sum(1 for _ in f) - 1
                start_chunk = processed_rows // chunk_size

            if start_chunk > 0:
                data_cleaning_logger.info(
                    f"Resuming from chunk {start_chunk} (approximately {processed_rows} rows already processed)"
                )
                mode = "a"
                header = False
            else:
                mode = "w"
                header = True
        except Exception as e:
            data_cleaning_logger.error(f"Error reading existing output file: {e}")
            mode = "w"
            header = True
    else:
        mode = "w"
        header = True

    total_emails_processed = 0
    total_threads_extracted = 0

    try:
        # Create a pandas reader object
        reader = pd.read_csv(input_file, chunksize=chunk_size, low_memory=False)

        # Skip already processed chunks
        for _ in range(start_chunk):
            try:
                next(reader)
            except StopIteration:
                data_cleaning_logger.info("All chunks already processed.")
                return

        # Process remaining chunks
        for chunk_number, chunk in enumerate(reader, start=start_chunk):
            if chunk_number > 0:
                return
            try:
                data_cleaning_logger.info(
                    f"Processing chunk {chunk_number + 1} with {len(chunk)} rows..."
                )

                # Set a global timeout for the entire chunk
                try:
                    with time_limit(300):  # 5 minute timeout per chunk
                        processed_chunk, threads_extracted = process_chunk(
                            chunk, data_cleaning_logger
                        )
                except TimeoutException:
                    data_cleaning_logger.error(
                        f"Timeout processing chunk {chunk_number + 1}. Skipping to next chunk."
                    )
                    continue

                # Check if we got any data
                if len(processed_chunk) == 0:
                    data_cleaning_logger.warning(
                        f"Chunk {chunk_number + 1} produced no data!"
                    )
                    continue

                # Write to CSV
                processed_chunk.to_csv(
                    output_file, mode=mode, index=False, header=header
                )

                # Update counters
                total_emails_processed += len(processed_chunk)
                total_threads_extracted += threads_extracted

                # Update mode for subsequent chunks
                mode = "a"
                header = False

                # Log progress
                data_cleaning_logger.info(
                    f"Chunk {chunk_number + 1} processed: {len(processed_chunk)} emails extracted."
                )

                # Force garbage collection
                del processed_chunk
                gc.collect()

                # Save checkpoint every 5 chunks
                if (chunk_number + 1) % 5 == 0:
                    data_cleaning_logger.info(
                        f"Checkpoint: {total_emails_processed} emails processed so far."
                    )

            except Exception as e:
                data_cleaning_logger.error(
                    f"Error processing chunk {chunk_number + 1}: {str(e)}"
                )
                data_cleaning_logger.error(traceback.format_exc())
                data_cleaning_logger.error("Continuing with next chunk...")
                continue
    except Exception as e:
        data_cleaning_logger.error(f"Critical error in main loop: {str(e)}")
        data_cleaning_logger.error(traceback.format_exc())
    finally:
        data_cleaning_logger.info("Processing complete or interrupted!")
        data_cleaning_logger.info(f"Total emails processed: {total_emails_processed}")
        data_cleaning_logger.info(
            f"Total email threads extracted: {total_threads_extracted}"
        )
        data_cleaning_logger.info(f"Dataset saved to: {output_file}")


if __name__ == "__main__":
    # File paths
    PROJECT_ROOT_DIR = project_root()
    INPUT_FILE = f"{PROJECT_ROOT_DIR}/data_pipeline/data/enron_emails.csv"
    OUTPUT_FILE = f"{PROJECT_ROOT_DIR}/data_pipeline/data/processed_enron_emails.csv"
    LOG_PATH = f"{PROJECT_ROOT_DIR}/data_pipeline/logs/data_clean_log.log"
    LOGGER_NAME = "data_cleaning_logger"
    data_clean(INPUT_FILE, OUTPUT_FILE, LOG_PATH, LOGGER_NAME)
