import os
import pandas as pd
import spacy
import nltk
from concurrent.futures import ProcessPoolExecutor
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from tqdm import tqdm  # Progress tracking

# Ensure NLTK punkt is downloaded
nltk.download("punkt")

# Paths
INPUT_CSV_PATH = "dataset/enron_emails.csv"
OUTPUT_CSV_PATH = "dataset/enron_action_items.csv"

# Load NLP Model with Increased max_length
nlp = spacy.load("en_core_web_sm")
nlp.max_length = 500000  # Increase the max length but stay within memory limits

def extract_action_items(text):
    """Extracts actionable sentences from an email body while handling very large inputs."""
    
    if not isinstance(text, str) or text.strip() == "":
        return ""

    # Handle excessively long texts
    text_length = len(text)
    if text_length > 1000000:
        print(f"Skipping overly long email ({text_length} characters)")
        return "Email too long, skipped."

    if text_length > 500000:  # If text is large, truncate to first 500K characters
        text = text[:500000]

    doc = nlp(text)
    action_sentences = []

    # Define action words
    action_words = {"should", "need", "must", "required", "action", "complete", "update", "fix"}

    for sent in doc.sents:
        if any(token.text.lower() in action_words for token in sent):
            action_sentences.append(sent.text.strip())

    # Summarization using SUMY (only if needed)
    if len(action_sentences) > 3:
        try:
            parser = PlaintextParser.from_string(" ".join(action_sentences), Tokenizer("english"))
            summarizer = LsaSummarizer()
            summarized_sentences = summarizer(parser.document, 3)  # Extract 3 key sentences
            return " | ".join([str(sent) for sent in summarized_sentences])
        except Exception as e:
            print(f"Summarization Error: {e}")
            return " | ".join(action_sentences)

    return " | ".join(action_sentences)  # Return extracted action items


def process_emails_for_action_items(input_csv, output_csv):
    """Processes all emails and extracts action items using multiprocessing."""
    
    if not os.path.exists(input_csv):
        print(f"Error: {input_csv} does not exist!")
        return

    df = pd.read_csv(input_csv, usecols=["Message-ID", "Body"])  # Load only required columns
    print(f"Processing {len(df)} emails...")

    # Use multiprocessing for faster execution
    with ProcessPoolExecutor(max_workers=8) as executor:
        results = list(tqdm(executor.map(extract_action_items, df["Body"]), total=len(df)))

    df["Action Items"] = results  # Assign extracted action items
    df.to_csv(output_csv, index=False, encoding="utf-8")  # Save output
    print(f"✅ Extraction Complete! Saved to {output_csv}")


if __name__ == "__main__":
    process_emails_for_action_items(INPUT_CSV_PATH, OUTPUT_CSV_PATH)
