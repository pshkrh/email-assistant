import os
import pandas as pd
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from tqdm import tqdm
from transformers import pipeline

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

# Extract Summaries using Sumy (LSA Model) for short texts
def extract_summary_lsa(text, num_sentences=2):
    """Summarizes text using Latent Semantic Analysis (LSA) method."""
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, num_sentences)
    return " ".join(str(sent) for sent in summary)

# Initialize the transformers summarizer using Facebook's BART model
transformers_summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Extract Summaries using Hugging Face Transformers for longer texts
def extract_summary_transformers(text):
    """Summarizes text using Hugging Face transformers pipeline."""
    # If text is very long, we truncate it to avoid exceeding model's max input length.
    words = text.split()
    if len(words) > 500:
        text = " ".join(words[:500])
    try:
        summary_result = transformers_summarizer(text, max_length=130, min_length=30, do_sample=False)
        summary_text = summary_result[0]['summary_text']
    except Exception as e:
        print(f"Error during transformers summarization: {e}")
        summary_text = ""
    return summary_text

# Helper function to format the summary into bullet points
def format_bullet_summary(summary_text):
    # Tokenize the summary into sentences using NLTK
    sentences = nltk.sent_tokenize(summary_text)
    # Prepend a bullet for each sentence
    bullet_points = "\n".join([f"- {sentence.strip()}" for sentence in sentences if sentence.strip()])
    return bullet_points

# Process Emails for Summarization
def process_summaries(df):
    summaries = []
    
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Generating Summaries"):
        body = str(row["Body"])
        if not body or body.strip() == "":
            summaries.append("")
            continue

        # Choose summarization method based on length
        if len(body.split()) > 100:  # Use transformers summarizer for longer texts
            summary_text = extract_summary_transformers(body)
        else:  # Use LSA summarizer for short texts
            summary_text = extract_summary_lsa(body)
        
        # Format the summary into bullet points
        formatted_summary = format_bullet_summary(summary_text)
        summaries.append(formatted_summary)

    df["Summary"] = summaries
    return df

# Save Summarized Data to CSV
def save_data(df):
    df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8")
    print(f"✅ Summarized data saved to {OUTPUT_CSV_PATH}")

if __name__ == "__main__":
    df = load_data()
    if df is not None:
        df = process_summaries(df)
        save_data(df)
