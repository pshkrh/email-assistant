import os
import pandas as pd
import spacy
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from tqdm import tqdm

# Ensure NLTK punkt tokenizer is available
nltk.download("punkt")

# Load NLP Model
nlp = spacy.load("en_core_web_sm")

# File Paths
INPUT_CSV_PATH = "dataset/enron_summarized.csv"
OUTPUT_CSV_PATH = "dataset/enron_action_items.csv"

# Define Action Keywords
ACTION_KEYWORDS = {
    "please", "action", "follow up", "due date", "review", "complete",
    "approve", "fix", "resolve", "schedule", "deadline", "required", "must",
    "should", "update", "send", "submit"
}

def extract_action_items(text):
    """Extract action-related sentences from an email body."""
    if not isinstance(text, str) or text.strip() == "":
        return ""

    doc = nlp(text)
    action_sentences = []

    for sent in doc.sents:
        if any(token.text.lower() in ACTION_KEYWORDS for token in sent):
            action_sentences.append(sent.text.strip())

    # Use Sumy Summarization if multiple action items found
    if len(action_sentences) > 3:
        parser = PlaintextParser.from_string(" ".join(action_sentences), Tokenizer("english"))
        summarizer = LsaSummarizer()
        summarized_sentences = summarizer(parser.document, 3)  # Extract 3 key sentences
        return " | ".join([str(sent) for sent in summarized_sentences])

    return " | ".join(action_sentences)  # Return extracted action items

def process_emails_for_action_items(input_csv, output_csv):
    """Processes emails and extracts action items."""
    if not os.path.exists(input_csv):
        print(f"Error: {input_csv} does not exist!")
        return

    df = pd.read_csv(input_csv, usecols=["Message-ID", "Body"])  # Load necessary columns
    print(f"Processing {len(df)} emails...")

    results = []
    for _, row in tqdm(df.iterrows(), total=len(df)):
        action_items = extract_action_items(row["Body"])
        results.append(action_items)

    df["Action Items"] = results  # Add extracted action items
    df.to_csv(output_csv, index=False, encoding="utf-8")  # Save the output
    print(f"✅ Action items extracted and saved to {output_csv}")

if __name__ == "__main__":
    process_emails_for_action_items(INPUT_CSV_PATH, OUTPUT_CSV_PATH)
