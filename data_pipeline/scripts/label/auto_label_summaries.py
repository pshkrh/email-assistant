import os
import pandas as pd
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from summarizer import Summarizer
from tqdm import tqdm

# Ensure NLTK dependencies are downloaded
nltk.download("punkt")

# File Paths
INPUT_CSV_PATH = "dataset/enron_sampled_for_labeling.csv"
OUTPUT_CSV_PATH = "dataset/enron_summarized.csv"

# Load Email Dataset
def load_data():
    if not os.path.exists(INPUT_CSV_PATH):
        print(f"Error: {INPUT_CSV_PATH} not found!")
        return None

    df = pd.read_csv(INPUT_CSV_PATH, usecols=["Message-ID", "Subject", "Body"])
    print(f"Loaded {len(df)} emails for summarization.")
    return df

# Extract Summaries using Sumy (LSA Model)
def extract_summary_lsa(text, num_sentences=2):
    """Summarizes text using Latent Semantic Analysis (LSA) method."""
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, num_sentences)
    return " ".join(str(sent) for sent in summary)

# Extract Summaries using BERT Extractive Summarizer
bert_model = Summarizer()

def extract_summary_bert(text):
    """Summarizes text using a pre-trained BERT model."""
    return bert_model(text, ratio=0.3)  # 30% of original text as summary

# Process Emails for Summarization
def process_summaries(df):
    summaries = []
    
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Generating Summaries"):
        body = str(row["Body"])
        if not body or body.strip() == "":
            summaries.append("")
            continue

        # Choose summarization method
        if len(body.split()) > 100:  # Use BERT for longer texts
            summary = extract_summary_bert(body)
        else:  # Use LSA for short texts
            summary = extract_summary_lsa(body)

        summaries.append(summary)

    df["Summary"] = summaries
    return df

# Save Summarized Data
def save_data(df):
    df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8")
    print(f"✅ Summarized data saved to {OUTPUT_CSV_PATH}")

if __name__ == "__main__":
    df = load_data()
    if df is not None:
        df = process_summaries(df)
        save_data(df)
