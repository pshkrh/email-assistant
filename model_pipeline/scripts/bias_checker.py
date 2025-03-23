import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
from rouge_score import rouge_scorer
from config import LABELED_SAMPLE_CSV_PATH, PREDICTED_SAMPLE_CSV_PATH
from bert_score import score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from transformers import logging
import spacy

logging.set_verbosity_error()

# Load spaCy model for Named Entity Recognition
nlp = spacy.load("en_core_web_sm")

# Define negation phrases to remove irrelevant rows
negation_phrases = (
    "No",
    "None",
    "Not",
    "Nothing",
    "N/A",
    "Nil",
    "- No",
    "- None",
    "- Not",
    "- Nothing",
)


def remove_no_action_items(df):
    """
    Removes rows where 'action_item' suggests no specific action items.
    Filters based on predefined negation phrases and generic "no action" phrases.
    """
    # Convert 'action_item' column to string
    df["action_item"] = df["action_item"].astype(str)

    # Define phrases that indicate NO actionable items
    no_action_keywords = [
        "no action items",
        "none",
        "no actionable items",
        "no direct action items",
        "none.",
        "No",
        "None",
    ]

    # Build case-insensitive regex pattern
    pattern = "|".join(no_action_keywords)

    # Remove rows where 'action_item' contains a no-action phrase
    filtered_df = df[~df["action_item"].str.contains(f"(?i){pattern}", na=False)]

    # Remove rows where 'action_item' starts with a negation phrase
    filtered_df = filtered_df[
        ~filtered_df["action_item"].str.startswith(negation_phrases, na=False)
    ]

    # Remove rows where 'action_item' is empty or whitespace
    filtered_df = filtered_df[filtered_df["action_item"].str.strip() != ""]

    return filtered_df


def extract_named_entities(text):
    """
    Extract named entities from text using spaCy.
    Returns a set of entity strings (e.g., {"John Doe", "Houston"}).
    """
    if not isinstance(text, str):
        text = ""
    doc = nlp(text)
    return {ent.text.strip() for ent in doc.ents if ent.text.strip()}


def compute_bert_score(pred_text, true_text, model_type="roberta-large"):
    """
    Compute BERTScore precision, recall, and F1 for a single predicted vs. true text pair.
    Returns a tuple of (precision, recall, f1).
    """
    pred_text = str(pred_text) if isinstance(pred_text, str) else ""
    true_text = str(true_text) if isinstance(true_text, str) else ""

    # Compute BERTScore
    P, R, F1 = score([pred_text], [true_text], model_type=model_type, verbose=False)

    return float(P[0]), float(R[0]), float(F1[0])


def calculate_rouge_scores(pred_text, true_text):
    """Calculate ROUGE scores between predicted text and true text."""
    pred_text = str(pred_text) if isinstance(pred_text, str) else ""
    true_text = str(true_text) if isinstance(true_text, str) else ""
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(true_text, pred_text)
    return scores["rougeL"].fmeasure


def classify_length_category(text):
    """Categorize email by character length."""
    length = len(str(text))
    if length <= 700:
        return "short"
    elif length <= 1500:
        return "medium"
    else:
        return "long"


def check_bias_by_body_length(labeled_df, predicted_df):
    """Evaluate model performance sliced by email body length category."""

    # Merge on Message-ID
    merged_df = pd.merge(
        labeled_df, predicted_df, on="Message-ID", suffixes=("_true", "_pred")
    )

    # Add slicing column based on 'Body_true' (or just 'Body' if same)
    merged_df["length_slice"] = merged_df["Body_true"].apply(classify_length_category)

    tasks = ["summary", "action_item", "draft_reply"]
    thresholds = {"rougeL": 0.7}
    thresholds_ner = {"ner": 0.5}

    for task in tasks:
        print(f"\n=== Evaluating Task: {task.upper()} by Body Length ===")

        y_true_col = f"{task}_true"
        y_pred_col = f"{task}_pred"

        # Generate binary correctness column
        def binary_score(row):
            _, _, bert_f1 = compute_bert_score(
                row[y_pred_col], row[y_true_col], model_type="roberta-large"
            )
            # Extract Named Entities and compute coverage
            true_ents = extract_named_entities(row[y_pred_col])
            pred_ents = extract_named_entities(row[y_true_col])

            # If no true entities, define coverage as 1.0 (no entity to match)
            ner_coverage = (
                1.0
                if len(true_ents) == 0
                else len(true_ents.intersection(pred_ents)) / len(true_ents)
            )

            # Assign 1 (correct) if both thresholds are met, else 0

            return int(
                1
                if (
                    bert_f1 >= thresholds["rougeL"]
                    and ner_coverage >= thresholds_ner["ner"]
                )
                else 0
            )

            # return int(calculate_rouge_scores(row[y_pred_col], row[y_true_col]) >= thresholds["rougeL"])

        merged_df[f"y_true_{task}"] = 1  # ground-truth is always correct
        merged_df[f"y_pred_{task}"] = merged_df.apply(binary_score, axis=1)

        # Slice and evaluate metrics
        results = {}
        for group in ["short", "medium", "long"]:
            slice_df = merged_df[merged_df["length_slice"] == group]
            y_true = slice_df[f"y_true_{task}"]
            y_pred = slice_df[f"y_pred_{task}"]

            if len(slice_df) == 0:
                continue

            precision = precision_score(y_true, y_pred, zero_division=0)
            recall = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            accuracy = accuracy_score(y_true, y_pred)

            results[group] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "accuracy": accuracy,
            }

            print(f"\nSlice: {group}")
            print(f"  Precision: {precision:.3f}")
            print(f"  Recall:    {recall:.3f}")
            print(f"  F1 Score:  {f1:.3f}")
            print(f"  Accuracy:  {accuracy:.3f}")

        # Compare accuracy between best and worst slice
        if len(results) >= 2:
            acc_values = [v["accuracy"] for v in results.values()]
            max_acc = max(acc_values)
            min_acc = min(acc_values)
            acc_gap = max_acc - min_acc

            if acc_gap > 0.15:
                print(
                    f"\n⚠️  Significant accuracy gap detected ({acc_gap:.2f}) between slices for task '{task}'."
                )
                # print("   ➤ Consider investigating why performance drops for certain email lengths.")


def main(predicted_csv_path, labeled_csv_path):

    print("Loading datasets...")
    labeled_df = pd.read_csv(labeled_csv_path)
    predicted_df = pd.read_csv(predicted_csv_path)

    print("Filtering out rows with no action items...")
    predicted_df = remove_no_action_items(predicted_df)

    print(len(predicted_df))

    check_bias_by_body_length(labeled_df, predicted_df)


if __name__ == "__main__":
    main(PREDICTED_SAMPLE_CSV_PATH, LABELED_SAMPLE_CSV_PATH)
