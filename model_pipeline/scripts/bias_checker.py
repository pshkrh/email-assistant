import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
from rouge_score import rouge_scorer
from config import LABELED_CSV, PREDICTED_CSV, ENRON_CSV

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

def check_bias_by_body_length(labeled_csv, predicted_csv):
    """Evaluate model performance sliced by email body length category."""

    print("Loading datasets...")
    labeled_df = pd.read_csv(labeled_csv)
    predicted_df = pd.read_csv(predicted_csv)

    print(labeled_df.columns)
    print(predicted_csv)

    # Merge on Message-ID
    merged_df = pd.merge(labeled_df, predicted_df, on="Message-ID", suffixes=("_true", "_pred"))

    # Add slicing column based on 'Body_true' (or just 'Body' if same)
    merged_df["length_slice"] = merged_df["Body_true"].apply(classify_length_category)

    print(len(merged_df))
    print(merged_df.size)

    tasks = ["summary", "action_item", "draft_reply"]
    thresholds = {"rougeL": 0.7}

    for task in tasks:
        print(f"\n=== Evaluating Task: {task.upper()} by Body Length ===")

        y_true_col = f"{task}_true"
        y_pred_col = f"{task}_pred"

        # Generate binary correctness column
        def binary_score(row):
            return int(calculate_rouge_scores(row[y_pred_col], row[y_true_col]) >= thresholds["rougeL"])

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
                "accuracy": accuracy
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
                print(f"\n⚠️  Significant accuracy gap detected ({acc_gap:.2f}) between slices for task '{task}'.")
                # print("   ➤ Consider investigating why performance drops for certain email lengths.")

def main():

    check_bias_by_body_length(LABELED_CSV, PREDICTED_CSV)

if __name__ == "__main__":
    main()