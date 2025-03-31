import spacy
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from config import LABELED_CSV, PREDICTED_CSV

# # Load spaCy model for Named Entity Recognition (NER)
# nlp = spacy.load("en_core_web_sm")

# # Define negation phrases to remove irrelevant rows
# negation_phrases = ("No", "None", "Not", "Nothing", "N/A", "Nil", "- No", "- None", "- Not", "- Nothing")

# def remove_no_action_items(df):
#     """
#     Removes rows where 'action_item' suggests no specific action items.
#     Filters based on predefined negation phrases and generic "no action" phrases.
#     """
#     # Convert 'action_item' column to string
#     df["action_item"] = df["action_item"].astype(str)

#     # Define phrases that indicate NO actionable items
#     no_action_keywords = [
#         "no action items",
#         "none",
#         "no actionable items",
#         "no direct action items",
#         "none.",
#     ]

#     # Build case-insensitive regex pattern
#     pattern = "|".join(no_action_keywords)

#     # Remove rows where 'action_item' contains a no-action phrase
#     filtered_df = df[~df["action_item"].str.contains(f"(?i){pattern}", na=False)]

#     # Remove rows where 'action_item' starts with a negation phrase
#     filtered_df = filtered_df[~filtered_df["action_item"].str.startswith(negation_phrases, na=False)]

#     # Remove rows where 'action_item' is empty or whitespace
#     filtered_df = filtered_df[filtered_df["action_item"].str.strip() != ""]

#     return filtered_df

# def extract_named_entities(text):
#     """
#     Extract named entities from text using spaCy.
#     Returns a set of entity strings (e.g., {"John Doe", "Houston"}).
#     """
#     if not isinstance(text, str):
#         text = ""
#     doc = nlp(text)
#     return {ent.text.strip() for ent in doc.ents if ent.text.strip()}

# def validate_action_item_ner(
#     labeled_csv,
#     predicted_csv,
#     ner_coverage_threshold=0.5
# ):
#     """
#     Compares 'action_item' from predicted CSV to labeled CSV using **only Named Entity Recognition (NER)**.
#     A row is "correct" if:
#       - At least `ner_coverage_threshold` (50% default) of labeled named entities appear in the predicted text.

#     Returns a dict with accuracy, precision, recall, and F1.
#     """
#     labeled_df = pd.read_csv(labeled_csv)
#     predicted_df = pd.read_csv(predicted_csv)

#     y_true = []
#     y_pred = []
#     matched_count = 0

#     for _, labeled_row in labeled_df.iterrows():
#         msg_id = labeled_row["Message-ID"]

#         # Find corresponding predicted row by Message-ID
#         matching_preds = predicted_df.loc[predicted_df["Message-ID"] == msg_id]
#         if matching_preds.empty:
#             continue

#         # Assume only one match per ID
#         pred_row = matching_preds.iloc[0]
#         matched_count += 1

#         true_ai = labeled_row["action_item"]
#         pred_ai = pred_row["action_item"]

#         # Extract Named Entities
#         true_ents = extract_named_entities(true_ai)
#         pred_ents = extract_named_entities(pred_ai)

#         # If no true entities, define coverage as 1.0 (nothing to match)
#         ner_coverage = 1.0 if len(true_ents) == 0 else len(true_ents.intersection(pred_ents)) / len(true_ents)

#         # Assign 1 (correct) if NER coverage meets threshold, else 0
#         y_true.append(1)
#         y_pred.append(1 if ner_coverage >= ner_coverage_threshold else 0)

#     if not y_true:
#         print("No matching rows found. Cannot compute metrics.")
#         return {}

#     # Compute standard metrics
#     accuracy_val = accuracy_score(y_true, y_pred) * 100
#     precision_val = precision_score(y_true, y_pred, zero_division=0) * 100
#     recall_val = recall_score(y_true, y_pred, zero_division=0) * 100
#     f1_val = f1_score(y_true, y_pred, zero_division=0) * 100

#     print(f"Matched rows: {matched_count}")
#     print(f"NER coverage threshold = {ner_coverage_threshold}")
#     print(f"Accuracy:  {accuracy_val:.2f}%")
#     print(f"Precision: {precision_val:.2f}%")
#     print(f"Recall:    {recall_val:.2f}%")
#     print(f"F1:        {f1_val:.2f}%")

#     return {
#         "accuracy": accuracy_val,
#         "precision": precision_val,
#         "recall": recall_val,
#         "f1": f1_val
#     }

# def main():
#     print("Loading predicted CSV...")
#     predicted_df = pd.read_csv(PREDICTED_CSV)

#     # print(predicted_df.size )

#     print("Filtering out rows with no action items...")
#     filtered_pred_df = remove_no_action_items(predicted_df)

#     # Save the filtered predictions to a temporary file OR keep in memory
#     filtered_pred_csv = "filtered_predicted.csv"
#     filtered_pred_df.to_csv(filtered_pred_csv, index=False)

#     print(filtered_pred_df.size)

#     print("Running NER-based evaluation on filtered data...")
#     metrics = validate_action_item_ner(
#         LABELED_CSV,
#         filtered_pred_csv,
#         ner_coverage_threshold=0.5  # At least 50% of named entities must match
#     )

#     print("\nFinal Metrics:", metrics)

# if __name__ == "__main__":
#     main()




# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# only berts score
# import spacy
# import pandas as pd
# from bert_score import score
# from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
# from transformers import logging
# from config import LABELED_CSV, PREDICTED_CSV

# # Suppress Hugging Face warnings (pooler layer, etc.)
# logging.set_verbosity_error()

# # Define negation phrases to remove irrelevant rows
# negation_phrases = ("No", "None", "Not", "Nothing", "N/A", "Nil", "- No", "- None", "- Not", "- Nothing")

# def remove_no_action_items(df):
#     """
#     Removes rows where 'action_item' suggests no specific action items.
#     Filters based on predefined negation phrases and generic "no action" phrases.
#     """
#     # Convert 'action_item' column to string
#     df["action_item"] = df["action_item"].astype(str)

#     # Define phrases that indicate NO actionable items
#     no_action_keywords = [
#         "no action items",
#         "none",
#         "no actionable items",
#         "no direct action items",
#         "none.",
#     ]

#     # Build case-insensitive regex pattern
#     pattern = "|".join(no_action_keywords)

#     # Remove rows where 'action_item' contains a no-action phrase
#     filtered_df = df[~df["action_item"].str.contains(f"(?i){pattern}", na=False)]

#     # Remove rows where 'action_item' starts with a negation phrase
#     filtered_df = filtered_df[~filtered_df["action_item"].str.startswith(negation_phrases, na=False)]

#     # Remove rows where 'action_item' is empty or whitespace
#     filtered_df = filtered_df[filtered_df["action_item"].str.strip() != ""]

#     return filtered_df

# def compute_bert_score(pred_text, true_text, model_type="roberta-large"):
#     """
#     Compute BERTScore precision, recall, and F1 for a single predicted vs. true text pair.
#     Returns a tuple of (precision, recall, f1).
#     """
#     pred_text = str(pred_text) if isinstance(pred_text, str) else ""
#     true_text = str(true_text) if isinstance(true_text, str) else ""

#     # Compute BERTScore
#     P, R, F1 = score(
#         [pred_text],
#         [true_text],
#         model_type=model_type,
#         verbose=False
#     )

#     return float(P[0]), float(R[0]), float(F1[0])

# def validate_action_item_bert(
#     labeled_csv,
#     predicted_csv,
#     bert_threshold=0.8,
#     model_type="roberta-large"
# ):
#     """
#     Compares 'action_item' from predicted CSV to labeled CSV using **only BERTScore**.
#     A row is "correct" if BERTScore F1 >= bert_threshold.

#     Returns a dict with accuracy, precision, recall, and F1.
#     """
#     labeled_df = pd.read_csv(labeled_csv)
#     predicted_df = pd.read_csv(predicted_csv)

#     y_true = []
#     y_pred = []
#     matched_count = 0

#     for _, labeled_row in labeled_df.iterrows():
#         msg_id = labeled_row["Message-ID"]

#         # Find corresponding predicted row by Message-ID
#         matching_preds = predicted_df.loc[predicted_df["Message-ID"] == msg_id]
#         if matching_preds.empty:
#             continue

#         # Assume only one match per ID
#         pred_row = matching_preds.iloc[0]
#         matched_count += 1

#         true_ai = labeled_row["action_item"]
#         pred_ai = pred_row["action_item"]

#         # Compute BERTScore F1
#         _, _, bert_f1 = compute_bert_score(pred_ai, true_ai, model_type=model_type)

#         # Assign 1 (correct) if BERT F1 meets threshold, else 0
#         y_true.append(1)
#         y_pred.append(1 if bert_f1 >= bert_threshold else 0)

#     if not y_true:
#         print("No matching rows found. Cannot compute metrics.")
#         return {}

#     # Compute standard metrics
#     accuracy_val = accuracy_score(y_true, y_pred) * 100
#     precision_val = precision_score(y_true, y_pred, zero_division=0) * 100
#     recall_val = recall_score(y_true, y_pred, zero_division=0) * 100
#     f1_val = f1_score(y_true, y_pred, zero_division=0) * 100

#     print(f"Matched rows: {matched_count}")
#     print(f"BERTScore F1 threshold = {bert_threshold}")
#     print(f"Accuracy:  {accuracy_val:.2f}%")
#     print(f"Precision: {precision_val:.2f}%")
#     print(f"Recall:    {recall_val:.2f}%")
#     print(f"F1:        {f1_val:.2f}%")

#     return {
#         "accuracy": accuracy_val,
#         "precision": precision_val,
#         "recall": recall_val,
#         "f1": f1_val
#     }

# def main():
#     print("Loading predicted CSV...")
#     predicted_df = pd.read_csv(PREDICTED_CSV)

#     print("Filtering out rows with no action items...")
#     filtered_pred_df = remove_no_action_items(predicted_df)

#     # Save the filtered predictions to a temporary file OR keep in memory
#     filtered_pred_csv = "filtered_predicted.csv"
#     filtered_pred_df.to_csv(filtered_pred_csv, index=False)

#     print("Running BERTScore evaluation on filtered data...")
#     metrics = validate_action_item_bert(
#         LABELED_CSV,
#         filtered_pred_csv,
#         bert_threshold=0.8   # BERTScore F1 must be >= 0.7
#     )

#     print("\nFinal Metrics:", metrics)

# if __name__ == "__main__":
#     main()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Both berts and ner

# import spacy
# import pandas as pd
# from bert_score import score
# from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
# from transformers import logging
# from config import LABELED_CSV, PREDICTED_CSV

# # Suppress Hugging Face warnings (pooler layer, etc.)
# logging.set_verbosity_error()

# # Load spaCy model for Named Entity Recognition
# nlp = spacy.load("en_core_web_sm")

# # Define negation phrases to remove irrelevant rows
# negation_phrases = ("No", "None", "Not", "Nothing", "N/A", "Nil", "- No", "- None", "- Not", "- Nothing")

# def remove_no_action_items(df):
#     """
#     Removes rows where 'action_item' suggests no specific action items.
#     Filters based on predefined negation phrases and generic "no action" phrases.
#     """
#     # Convert 'action_item' column to string
#     df["action_item"] = df["action_item"].astype(str)

#     # Define phrases that indicate NO actionable items
#     no_action_keywords = [
#         "no action items",
#         "none",
#         "no actionable items",
#         "no direct action items",
#         "none.",
#         "No",
#         "None",
#     ]

#     # Build case-insensitive regex pattern
#     pattern = "|".join(no_action_keywords)

#     # Remove rows where 'action_item' contains a no-action phrase
#     filtered_df = df[~df["action_item"].str.contains(f"(?i){pattern}", na=False)]

#     # Remove rows where 'action_item' starts with a negation phrase
#     filtered_df = filtered_df[~filtered_df["action_item"].str.startswith(negation_phrases, na=False)]

#     # Remove rows where 'action_item' is empty or whitespace
#     filtered_df = filtered_df[filtered_df["action_item"].str.strip() != ""]

#     return filtered_df

# def extract_named_entities(text):
#     """
#     Extract named entities from text using spaCy.
#     Returns a set of entity strings (e.g., {"John Doe", "Houston"}).
#     """
#     if not isinstance(text, str):
#         text = ""
#     doc = nlp(text)
#     return {ent.text.strip() for ent in doc.ents if ent.text.strip()}

# def compute_bert_score(pred_text, true_text, model_type="roberta-large"):
#     """
#     Compute BERTScore precision, recall, and F1 for a single predicted vs. true text pair.
#     Returns a tuple of (precision, recall, f1).
#     """
#     pred_text = str(pred_text) if isinstance(pred_text, str) else ""
#     true_text = str(true_text) if isinstance(true_text, str) else ""

#     # Compute BERTScore
#     P, R, F1 = score(
#         [pred_text],
#         [true_text],
#         model_type=model_type,
#         verbose=False
#     )

#     return float(P[0]), float(R[0]), float(F1[0])

# def validate_action_item_ner_bert(
#     labeled_csv,
#     predicted_csv,
#     bert_threshold=0.7,
#     ner_coverage_threshold=0.5,
#     model_type="roberta-large"
# ):
#     """
#     Compares 'action_item' from predicted CSV to labeled CSV using:
#       1) BERTScore F1,
#       2) Named Entity coverage.
#     A row is "correct" if:
#       - BERTScore F1 >= bert_threshold, AND
#       - fraction of matched entities >= ner_coverage_threshold.

#     Returns a dict with accuracy, precision, recall, f1.
#     """
#     labeled_df = pd.read_csv(labeled_csv)
#     predicted_df = pd.read_csv(predicted_csv)

#     y_true = []
#     y_pred = []
#     matched_count = 0

#     for _, labeled_row in labeled_df.iterrows():
#         msg_id = labeled_row["Message-ID"]

#         # Find corresponding predicted row by Message-ID
#         matching_preds = predicted_df.loc[predicted_df["Message-ID"] == msg_id]
#         if matching_preds.empty:
#             continue

#         # Assume only one match per ID
#         pred_row = matching_preds.iloc[0]
#         matched_count += 1

#         true_ai = labeled_row["action_item"]
#         pred_ai = pred_row["action_item"]

#         # Compute BERTScore F1
#         _, _, bert_f1 = compute_bert_score(pred_ai, true_ai, model_type=model_type)

#         # Extract Named Entities and compute coverage
#         true_ents = extract_named_entities(true_ai)
#         pred_ents = extract_named_entities(pred_ai)

#         # If no true entities, define coverage as 1.0 (no entity to match)
#         ner_coverage = 1.0 if len(true_ents) == 0 else len(true_ents.intersection(pred_ents)) / len(true_ents)

#         # Assign 1 (correct) if both thresholds are met, else 0
#         y_true.append(1)
#         y_pred.append(1 if (bert_f1 >= bert_threshold and ner_coverage >= ner_coverage_threshold) else 0)

#     if not y_true:
#         print("No matching rows found. Cannot compute metrics.")
#         return {}

#     # Compute standard metrics
#     accuracy_val = accuracy_score(y_true, y_pred) * 100
#     precision_val = precision_score(y_true, y_pred, zero_division=0) * 100
#     recall_val = recall_score(y_true, y_pred, zero_division=0) * 100
#     f1_val = f1_score(y_true, y_pred, zero_division=0) * 100

#     print(f"Matched rows: {matched_count}")
#     print(f"BERTScore F1 threshold = {bert_threshold}")
#     print(f"NER coverage threshold = {ner_coverage_threshold}")
#     print(f"Accuracy:  {accuracy_val:.2f}%")
#     print(f"Precision: {precision_val:.2f}%")
#     print(f"Recall:    {recall_val:.2f}%")
#     print(f"F1:        {f1_val:.2f}%")

#     return {
#         "accuracy": accuracy_val,
#         "precision": precision_val,
#         "recall": recall_val,
#         "f1": f1_val
#     }

# def main():
#     print("Loading predicted CSV...")
#     predicted_df = pd.read_csv(PREDICTED_CSV)

#     print("Filtering out rows with no action items...")
#     filtered_pred_df = remove_no_action_items(predicted_df)

#     # Save the filtered predictions to a temporary file OR keep in memory
#     filtered_pred_csv = "filtered_predicted.csv"
#     filtered_pred_df.to_csv(filtered_pred_csv, index=False)

#     print("Running BERT + NER coverage evaluation on filtered data...")
#     metrics = validate_action_item_ner_bert(
#         LABELED_CSV,
#         filtered_pred_csv,
#         bert_threshold=0.7,        # BERTScore F1 must be >= 0.7
#         ner_coverage_threshold=0.5 # At least 50% of named entities must match
#     )

#     print("\nFinal Metrics:", metrics)

# if __name__ == "__main__":
#     main()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# import pandas as pd
# from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
# from config import LABELED_CSV, PREDICTED_CSV  # Use paths from config.py
# import mlflow
# import os
from output_verifier import verify_all_outputs
from llm_ranker import rank_all_outputs
from llm_generator import process_email_body
# import numpy as np
# from rouge_score import rouge_scorer

# def calculate_rouge_scores(pred_text, true_text):
#     """Calculate ROUGE scores between predicted text and true text."""

#     # Ensure inputs are strings, handling NaN values
#     pred_text = str(pred_text) if isinstance(pred_text, str) else ""
#     true_text = str(true_text) if isinstance(true_text, str) else ""

#     # Initialize ROUGE scorer
#     scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)

#     # Compute ROUGE scores
#     scores = scorer.score(true_text, pred_text)

#     return {
#         "rouge1": scores["rouge1"],
#         "rouge2": scores["rouge2"],
#         "rougeL": scores["rougeL"],
#     }

# def validate_outputs(predicted):
#     """Compare predicted outputs with labeled data."""

#     labeled_df = pd.read_csv(LABELED_CSV)

#     results = {"summary": [], "action_item": [], "draft_reply": []}
#     true_labels = {"summary": [], "action_item": [], "draft_reply": []}

#     matched_count = 0  # Track matched messages

#     for _, row in labeled_df.iterrows():
#         msg_id = row["Message-ID"]

#         if msg_id in predicted["Message-ID"].values:
#             matched_count += 1
#             for task in results.keys():
#                 pred = predicted.loc[predicted["Message-ID"] == msg_id, task].values[0]
#                 true = row[task]

#                 # Compute ROUGE scores
#                 rouge_scores = calculate_rouge_scores(pred, true)
#                 rougeL_f1 = rouge_scores["rougeL"].fmeasure
#                 results[task].append(1 if rougeL_f1 >= 0.7 else 0)
#                 true_labels[task].append(1)  # True labels should be all 1s

#     print(f"Matched {matched_count} emails for validation.")

#     metrics = {}
#     with mlflow.start_run(nested=True):
#         for task in results.keys():
#             precision = precision_score(true_labels[task], results[task], zero_division=0) * 100
#             recall = recall_score(true_labels[task], results[task], zero_division=0) * 100
#             f1 = f1_score(true_labels[task], results[task], zero_division=0) * 100
#             accuracy = accuracy_score(true_labels[task], results[task]) * 100

#             metrics[task] = {
#                 "precision": precision,
#                 "recall": recall,
#                 "f1": f1,
#                 "accuracy": accuracy,
#             }

#             mlflow.log_metric(f"{task}_precision", precision)
#             mlflow.log_metric(f"{task}_recall", recall)
#             mlflow.log_metric(f"{task}_f1", f1)
#             mlflow.log_metric(f"{task}_accuracy", accuracy)

#     return metrics

# def run_validation():
#     """Run validation and print results."""
#     print(f"Loading predictions from {PREDICTED_CSV}...")
#     predicted_outputs = pd.read_csv(PREDICTED_CSV)

#     print("Running validation...")
#     metrics = validate_outputs(predicted_outputs)

#     for task, scores in metrics.items():
#         print(
#             f"{task.capitalize()} - Recall: {scores['recall']:.2f}, Precision: {scores['precision']:.2f}, "
#             f"F1: {scores['f1']:.2f}, Accuracy: {scores['accuracy']:.2f}"
#         )
#     return metrics

def pred_value():
    """Process email bodies and update predictions in CSV, dropping unprocessed rows."""

    userEmail = "unknown"

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

        for task in tasks:
            output = best_outputs.get(task, "")
            pred_df.at[index, task] = output
        #     if output:  # Check if any output is non-empty
        #         has_updated = True
        
        # if has_updated:
        #     processed_rows.add(index)  # Mark row as processed

    print("Processing complete. Filtering unprocessed rows...")

    # Keep only rows that were processed
    # pred_df = pred_df.loc[processed_rows]

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


pred_value()
