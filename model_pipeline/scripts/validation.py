import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from config import LABELED_CSV, PREDICTED_CSV  # Use paths from config.py
import mlflow
import os
from output_verifier import verify_all_outputs
from llm_ranker import rank_all_outputs
from llm_generator import process_email_body
import numpy as np
from rouge_score import rouge_scorer

def calculate_rouge_scores(pred_text, true_text):
    """Calculate ROUGE scores between predicted text and true text."""
    
    # Ensure inputs are strings, handling NaN values
    pred_text = str(pred_text) if isinstance(pred_text, str) else ""
    true_text = str(true_text) if isinstance(true_text, str) else ""

    # Initialize ROUGE scorer
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

    # Compute ROUGE scores
    scores = scorer.score(true_text, pred_text)

    return {
        "rouge1": scores["rouge1"],
        "rouge2": scores["rouge2"],
        "rougeL": scores["rougeL"],
    }

def validate_outputs(predicted):
    """Compare predicted outputs with labeled data."""
    
    labeled_df = pd.read_csv(LABELED_CSV)

    results = {"summary": [], "action_item": [], "draft_reply": []}
    true_labels = {"summary": [], "action_item": [], "draft_reply": []}
    
    matched_count = 0  # Track matched messages

    for _, row in labeled_df.iterrows():
        msg_id = row["Message-ID"]

        if msg_id in predicted["Message-ID"].values:
            matched_count += 1
            for task in results.keys():
                pred = predicted.loc[predicted["Message-ID"] == msg_id, task].values[0]
                true = row[task]

                # Compute ROUGE scores
                rouge_scores = calculate_rouge_scores(pred, true)
                rougeL_f1 = rouge_scores["rougeL"].fmeasure
                results[task].append(1 if rougeL_f1 >= 0.7 else 0)
                true_labels[task].append(1)  # True labels should be all 1s

    print(f"Matched {matched_count} emails for validation.")

    metrics = {}
    with mlflow.start_run(nested=True):
        for task in results.keys():
            precision = precision_score(true_labels[task], results[task], zero_division=0) * 100
            recall = recall_score(true_labels[task], results[task], zero_division=0) * 100
            f1 = f1_score(true_labels[task], results[task], zero_division=0) * 100
            accuracy = accuracy_score(true_labels[task], results[task]) * 100

            metrics[task] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "accuracy": accuracy,
            }

            mlflow.log_metric(f"{task}_precision", precision)
            mlflow.log_metric(f"{task}_recall", recall)
            mlflow.log_metric(f"{task}_f1", f1)
            mlflow.log_metric(f"{task}_accuracy", accuracy)

    return metrics

def run_validation():
    """Run validation and print results."""
    print(f"Loading predictions from {PREDICTED_CSV}...")
    predicted_outputs = pd.read_csv(PREDICTED_CSV)

    print("Running validation...")
    metrics = validate_outputs(predicted_outputs)

    for task, scores in metrics.items():
        print(
            f"{task.capitalize()} - Recall: {scores['recall']:.2f}, Precision: {scores['precision']:.2f}, "
            f"F1: {scores['f1']:.2f}, Accuracy: {scores['accuracy']:.2f}"
        )
    return metrics

def pred_value():
    """Process email bodies and update predictions in CSV, dropping unprocessed rows."""

    userEmail = "demo@gmail.com"

    print(f"Loading data from {PREDICTED_CSV}...")
    pred_df = pd.read_csv(PREDICTED_CSV)

    # Define tasks
    tasks = ["summary", "action_item", "draft_reply"]

    # Initialize new columns dynamically
    for task in tasks:
        pred_df[task] = ""

    print("Starting email body processing...")

    # Limit processing to the first 100 rows
    max_rows = min(100, len(pred_df))

    # Track processed row indices
    processed_rows = set()

    # Iterate through the first 100 rows
    for index, row in pred_df.iloc[:max_rows].iterrows():
        body = row["Body"]
        
        print(f"Processing row {index + 1}/{max_rows}...")

        # Process the email body
        llm_outputs = process_email_body(body, tasks, userEmail)
        ranked_outputs = rank_all_outputs(llm_outputs, tasks, body)
        best_outputs = verify_all_outputs(ranked_outputs, tasks, body, userEmail)
        
        # Store results dynamically
        has_updated = False
        for task in tasks:
            output = best_outputs.get(task, "")
            pred_df.at[index, task] = output
            if output:  # Check if any output is non-empty
                has_updated = True
        
        if has_updated:
            processed_rows.add(index)  # Mark row as processed

    print("Processing complete. Filtering unprocessed rows...")

    # Keep only rows that were processed
    pred_df = pred_df.loc[processed_rows]

    # Save the updated DataFrame to CSV
    pred_df.to_csv(PREDICTED_CSV, index=False)

    print(f"Saved {len(pred_df)} processed rows to CSV.")

def clean_pred_file():
    """Remove rows where 'summary', 'action_item', and 'draft_reply' are empty from predicted_enron.csv"""

    print(f"Loading data from {PREDICTED_CSV}...")
    pred_df = pd.read_csv(PREDICTED_CSV)

    # Define columns to check
    tasks = ["summary", "action_item", "draft_reply"]

    # Drop rows where all task columns are empty
    cleaned_df = pred_df.dropna(subset=tasks, how="all")  # Removes rows where all tasks are NaN
    cleaned_df = cleaned_df[~(cleaned_df[tasks] == "").all(axis=1)]  # Removes rows where all tasks are empty strings

    # Save the cleaned DataFrame back
    cleaned_df.to_csv(PREDICTED_CSV, index=False)

    print(f"Removed {len(pred_df) - len(cleaned_df)} unprocessed rows. Final dataset: {len(cleaned_df)} rows.")

def main():
    """Run the pipeline: process emails, clean predictions, and validate."""
    # Uncomment if you want to re-run email processing
    # pred_value()

    # Uncomment if you want to clean empty predictions before validation
    # clean_pred_file()

    run_validation()

if __name__ == "__main__":
    main()