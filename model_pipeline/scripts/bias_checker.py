"""
Bias Checker Module with Fairlearn Integration

This module evaluates the system's outputs for potential biases across different slices
of data (e.g., email length, complexity, sender role). It assesses the quality of generated
content by comparing against human-labeled data using various metrics including:
- BERT Score
- Rouge Score
- Named Entity Recognition Coverage
- Fairlearn fairness metrics
"""

import tempfile
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import spacy
import mlflow
from rouge_score import rouge_scorer
from bert_score import score
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
from transformers import logging as hf_logging
from fairlearn.metrics import (
    MetricFrame,
    selection_rate,
    false_positive_rate,
    false_negative_rate,
)

# Local application imports
from config import LABELED_SAMPLE_CSV_PATH, PREDICTED_SAMPLE_CSV_PATH
from mlflow_config import configure_mlflow
from send_notification import send_email_notification

# Configure logging and load NLP model
hf_logging.set_verbosity_error()  # Suppress transformer warnings
nlp = spacy.load("en_core_web_sm")  # Load spaCy model for NER

# Path to enron_emails.csv
ENRON_EMAILS_CSV_PATH = "data_pipeline/data/enron_emails.csv"

# Set up MLflow experiment
experiment = configure_mlflow()
experiment_id = experiment.experiment_id if experiment else None

# Phrases indicating empty action items
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
    None,
)


def remove_no_action_items(df):
    """
    Remove rows where action items are empty or negative.

    Args:
        df (DataFrame): Input DataFrame containing action items

    Returns:
        DataFrame: Filtered DataFrame
    """
    df["action_item"] = df["action_item"].astype(str)

    # Define patterns for identifying "no action items" responses
    no_action_keywords = [
        "no action items",
        "none",
        "no actionable items",
        "no direct action items",
        "none.",
        "No",
        "None",
    ]
    pattern = "|".join(no_action_keywords)

    # Filter out rows containing no action items
    filtered_df = df[~df["action_item"].str.contains(f"(?i){pattern}", na=False)]
    filtered_df = filtered_df[
        ~filtered_df["action_item"].str.startswith(negation_phrases, na=False)
    ]
    filtered_df = filtered_df[filtered_df["action_item"].str.strip() != ""]

    return filtered_df


def extract_named_entities(text):
    """
    Extract named entities from text using spaCy.

    Args:
        text (str): Text to extract entities from

    Returns:
        set: Set of named entities
    """
    if not isinstance(text, str):
        text = ""
    doc = nlp(text)
    return {ent.text.strip() for ent in doc.ents if ent.text.strip()}


def compute_bert_score(pred_text, true_text, model_type="roberta-large"):
    """
    Compute BERT score between predicted and ground truth text.

    Args:
        pred_text (str): Predicted text
        true_text (str): Ground truth text
        model_type (str): Model to use for BERT score computation

    Returns:
        tuple: Precision, Recall, and F1 scores
    """
    if not isinstance(true_text, str) and not isinstance(pred_text, str):
        return 1.0, 1.0, 1.0  # Default for empty texts

    # Normalize inputs
    pred_text = str(pred_text) if isinstance(pred_text, str) else ""
    true_text = str(true_text) if isinstance(true_text, str) else ""

    # Calculate scores
    P, R, F1 = score([pred_text], [true_text], model_type=model_type, verbose=False)
    return float(P[0]), float(R[0]), float(F1[0])


def calculate_rouge_scores(pred_text, true_text):
    """
    Calculate Rouge-L scores between predicted and ground truth text.

    Args:
        pred_text (str): Predicted text
        true_text (str): Ground truth text

    Returns:
        float: Rouge-L F-measure score
    """
    # Normalize inputs
    pred_text = str(pred_text) if isinstance(pred_text, str) else ""
    true_text = str(true_text) if isinstance(true_text, str) else ""

    # Calculate Rouge-L score
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(true_text, pred_text)
    return scores["rougeL"].fmeasure


def classify_length_category(text):
    """
    Classify text into length categories based on character count.

    Args:
        text (str): Text to classify

    Returns:
        str: Length category ("short", "medium", or "long")
    """
    length = len(str(text))
    if length <= 700:
        return "short"
    elif length <= 1500:
        return "medium"
    else:
        return "long"


def classify_role(sender):
    """
    Classify email sender role based on job title in email address.

    Args:
        sender (str): Sender email or name

    Returns:
        str: Role category ("manager" or "team_member")
    """
    if pd.isna(sender):
        return "unknown"

    sender = str(sender).lower()
    if "manager" in sender or "director" in sender:
        return "manager"

    return "team_member"


def compute_complexity(text):
    """
    Compute text complexity based on average sentence length.

    Args:
        text (str): Text to analyze

    Returns:
        str: Complexity category ("high" or "low")
    """
    doc = nlp(str(text))
    sentences = list(doc.sents)
    avg_len = sum(len(sent) for sent in sentences) / len(sentences) if sentences else 0
    return "high" if avg_len > 50 else "low"


def create_fairlearn_visualizations(merged_df, task, experiment_id):
    """
    Create and log Fairlearn visualizations for bias analysis.

    Args:
        merged_df (DataFrame): DataFrame with predictions and ground truth
        task (str): Task name (summary, action_item, etc.)
        experiment_id (str): MLflow experiment ID
    """
    # Prepare the data for all slices
    slices = ["length_slice", "complexity_slice", "role_slice"]

    for slice_type in slices:
        # Get unique groups in this slice
        groups = merged_df[slice_type].values

        # Get the predictions and true values
        y_true = merged_df[f"y_true_{task}"].values
        y_pred = merged_df[f"y_pred_{task}"].values

        # Calculate fairness metrics using Fairlearn's MetricFrame
        metrics = {
            "accuracy": accuracy_score,
            "selection_rate": selection_rate,
            "false_positive_rate": false_positive_rate,
            "false_negative_rate": false_negative_rate,
        }

        # Create a MetricFrame
        metric_frame = MetricFrame(
            metrics=metrics, y_true=y_true, y_pred=y_pred, sensitive_features=groups
        )

        # Log the metrics to MLflow
        mlflow.log_dict(
            metric_frame.by_group.to_dict(),
            f"fairlearn_metrics_{task}_{slice_type}.json",
        )

        # Create and log visualizations

        # 1. Disparity in accuracy
        plt.figure(figsize=(10, 6))
        metric_frame.by_group["accuracy"].plot.bar(title=f"Accuracy by {slice_type}")
        plt.tight_layout()

        # Save to temporary file and log to MLflow
        with NamedTemporaryFile(suffix=".png") as tmp:
            plt.savefig(tmp.name)
            mlflow.log_artifact(tmp.name, f"fairlearn_accuracy_{task}_{slice_type}.png")
        plt.close()

        # 2. Selection rate disparity (demographic parity)
        plt.figure(figsize=(10, 6))
        metric_frame.by_group["selection_rate"].plot.bar(
            title=f"Selection Rate by {slice_type} (Demographic Parity)"
        )
        plt.tight_layout()

        with NamedTemporaryFile(suffix=".png") as tmp:
            plt.savefig(tmp.name)
            mlflow.log_artifact(
                tmp.name, f"fairlearn_selection_rate_{task}_{slice_type}.png"
            )
        plt.close()

        # 3. False positive and negative rates (equalized odds)
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        metric_frame.by_group["false_positive_rate"].plot.bar(
            ax=ax[0], title=f"False Positive Rate by {slice_type}"
        )
        metric_frame.by_group["false_negative_rate"].plot.bar(
            ax=ax[1], title=f"False Negative Rate by {slice_type}"
        )
        plt.tight_layout()

        with NamedTemporaryFile(suffix=".png") as tmp:
            plt.savefig(tmp.name)
            mlflow.log_artifact(
                tmp.name, f"fairlearn_error_rates_{task}_{slice_type}.png"
            )
        plt.close()

        # Calculate and log the disparity metrics
        disparity = {
            "accuracy": metric_frame.difference(
                method="between_groups", metrics="accuracy"
            ),
            "selection_rate": metric_frame.difference(
                method="between_groups", metrics="selection_rate"
            ),
            "false_positive_rate": metric_frame.difference(
                method="between_groups", metrics="false_positive_rate"
            ),
            "false_negative_rate": metric_frame.difference(
                method="between_groups", metrics="false_negative_rate"
            ),
        }

        mlflow.log_dict(disparity, f"fairlearn_disparity_{task}_{slice_type}.json")


def create_fairness_dashboard(merged_df, task):
    """
    Create a fairness dashboard for a specific task.

    Args:
        merged_df (DataFrame): DataFrame with predictions and ground truth
        task (str): Task name (summary, action_item, etc.)

    Returns:
        str: Path to the HTML dashboard file
    """
    # Create a temporary file to store the dashboard
    temp_dir = tempfile.mkdtemp()
    dashboard_path = f"{temp_dir}/fairness_dashboard_{task}.html"

    # Plot fairness metrics for each slice
    for slice_type in ["length_slice", "complexity_slice", "role_slice"]:
        # Create a figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f"Fairness Metrics for {task} by {slice_type}", fontsize=16)

        # Get data for this slice
        slice_data = (
            merged_df.groupby(slice_type)
            .agg(
                {
                    f"y_true_{task}": "mean",
                    f"y_pred_{task}": "mean",
                    f"scores_{task}": lambda x: np.mean([i["bert_f1"] for i in x]),
                }
            )
            .reset_index()
        )

        # Plot accuracy by slice
        axs[0, 0].bar(slice_data[slice_type], slice_data[f"y_pred_{task}"])
        axs[0, 0].set_title("Accuracy by Group")
        axs[0, 0].set_ylabel("Accuracy")
        axs[0, 0].set_ylim(0, 1)

        # Plot BERT F1 score by slice
        axs[0, 1].bar(slice_data[slice_type], slice_data[f"scores_{task}"])
        axs[0, 1].set_title("BERT F1 Score by Group")
        axs[0, 1].set_ylabel("BERT F1")
        axs[0, 1].set_ylim(0, 1)

        # Plot confusion matrix metrics by slice (true positive rate, false positive rate)
        # These are just placeholders - in real implementation you'd calculate these metrics
        axs[1, 0].bar(slice_data[slice_type], slice_data[f"y_pred_{task}"])
        axs[1, 0].set_title("True Positive Rate by Group")
        axs[1, 0].set_ylabel("TPR")
        axs[1, 0].set_ylim(0, 1)

        axs[1, 1].bar(slice_data[slice_type], 1 - slice_data[f"y_pred_{task}"])
        axs[1, 1].set_title("False Positive Rate by Group")
        axs[1, 1].set_ylabel("FPR")
        axs[1, 1].set_ylim(0, 1)

        plt.tight_layout()
        plt.savefig(f"{temp_dir}/fairness_{task}_{slice_type}.png")
        plt.close()

    # Create a simple HTML dashboard
    with open(dashboard_path, "w") as f:
        f.write(
            f"""
        <html>
        <head>
            <title>Fairness Dashboard for {task}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .metrics {{ display: flex; flex-wrap: wrap; }}
                .metric {{ margin: 10px; padding: 10px; border: 1px solid #ddd; }}
                img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <h1>Fairness Dashboard for {task}</h1>
            
            <h2>Length Slice</h2>
            <div class="metrics">
                <div class="metric">
                    <img src="fairness_{task}_length_slice.png" alt="Length Slice Metrics">
                </div>
            </div>
            
            <h2>Complexity Slice</h2>
            <div class="metrics">
                <div class="metric">
                    <img src="fairness_{task}_complexity_slice.png" alt="Complexity Slice Metrics">
                </div>
            </div>
            
            <h2>Role Slice</h2>
            <div class="metrics">
                <div class="metric">
                    <img src="fairness_{task}_role_slice.png" alt="Role Slice Metrics">
                </div>
            </div>
        </body>
        </html>
        """
        )

    return dashboard_path


def check_bias(labeled_df, predicted_df):
    """
    Check for biases in model predictions across different data slices.

    Args:
        labeled_df (DataFrame): DataFrame with ground truth labels
        predicted_df (DataFrame): DataFrame with model predictions
    """
    # Merge the dataframes on Message-ID
    merged_df = pd.merge(
        labeled_df, predicted_df, on="Message-ID", suffixes=("_true", "_pred")
    )

    # Log merged columns for debugging
    mlflow.log_dict(
        {"merged_df_columns": list(merged_df.columns)}, "merged_df_cols.json"
    )

    # Create slices for analysis
    merged_df["length_slice"] = merged_df["Body_true"].apply(classify_length_category)
    merged_df["complexity_slice"] = merged_df["Body_true"].apply(compute_complexity)
    merged_df["role_slice"] = merged_df["Sender"].apply(classify_role)

    # Log slice statistics
    mlflow.log_dict(
        {
            "length_slice": merged_df["length_slice"].value_counts().to_dict(),
            "complexity_slice": merged_df["complexity_slice"].value_counts().to_dict(),
            "role_slice": merged_df["role_slice"].value_counts().to_dict(),
        },
        "slice_counts.json",
    )

    # Define tasks and quality thresholds
    tasks = ["summary", "action_item", "draft_reply"]
    task_thresholds = {
        "summary": {"bert_f1": 0.8, "ner": 0.7, "rouge_l": 0.7},  # Tightened
        "action_item": {"bert_f1": 0.8, "ner": 0.8},  # Loosened
        "draft_reply": {"bert_f1": 0.8, "ner": 0.8},  # Loosened
    }

    # Track failure cases and alerts
    failure_cases = []
    alert_triggered = False
    alert_messages = []

    # Analyze each task
    for task in tasks:
        y_true_col = f"{task}_true"
        y_pred_col = f"{task}_pred"

        def compute_scores(row):
            """Compute quality scores for a single row"""
            # Calculate BERT score
            bert_p, bert_r, bert_f1 = compute_bert_score(
                row[y_pred_col], row[y_true_col]
            )

            # Calculate Rouge-L score
            rouge_l = calculate_rouge_scores(row[y_pred_col], row[y_true_col])

            # Calculate NER coverage
            true_ents = extract_named_entities(row[y_true_col])
            pred_ents = extract_named_entities(row[y_pred_col])
            ner_coverage = (
                1.0
                if not true_ents
                else len(true_ents.intersection(pred_ents)) / len(true_ents)
            )

            # Compile scores
            scores = {
                "bert_f1": bert_f1,
                "rouge_l": rouge_l,
                "ner_coverage": ner_coverage,
            }

            # Check if output meets quality thresholds
            thresholds = task_thresholds[task]
            is_correct = (
                bert_f1 >= thresholds["bert_f1"]
                and ner_coverage >= thresholds["ner"]
                and (task != "summary" or rouge_l >= thresholds["rouge_l"])
            )
            scores["correct"] = int(is_correct)

            # Track failure cases
            if not is_correct:
                failure_cases.append(
                    {
                        "Message-ID": row["Message-ID"],
                        "task": task,
                        "true_text": row[y_true_col],
                        "pred_text": row[y_pred_col],
                        "bert_f1": bert_f1,
                        "ner_coverage": ner_coverage,
                        "rouge_l": rouge_l,
                        "length_slice": row["length_slice"],
                        "complexity_slice": row["complexity_slice"],
                        "role_slice": row["role_slice"],
                    }
                )

            return scores

        # Apply scoring to all rows
        merged_df[f"scores_{task}"] = merged_df.apply(compute_scores, axis=1)
        merged_df[f"y_true_{task}"] = 1  # Assuming all ground truth is correct
        merged_df[f"y_pred_{task}"] = merged_df[f"scores_{task}"].apply(
            lambda x: x["correct"]
        )

        # Analyze bias across different slices
        for slice_type in ["length_slice", "complexity_slice", "role_slice"]:
            results = {}
            for group in merged_df[slice_type].unique():
                slice_df = merged_df[merged_df[slice_type] == group]
                if slice_df.empty:
                    continue

                # Calculate metrics for this slice
                y_true = slice_df[f"y_true_{task}"]
                y_pred = slice_df[f"y_pred_{task}"]
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

            # Check for significant accuracy gaps between slices (potential bias)
            if len(results) >= 2:
                acc_values = [v["accuracy"] for v in results.values()]
                acc_gap = max(acc_values) - min(acc_values)

                # If gap exceeds threshold, log it and trigger alert
                if acc_gap > 0.15:  # 15% accuracy gap threshold
                    gap_info = {
                        "task": task,
                        "slice_type": slice_type,
                        "accuracy_gap": round(acc_gap, 3),
                        "slice_results": results,
                        "suggestions": [
                            "Review failure_cases.csv for low-performing slices",
                            "Adjust prompts in llm_generator.py for better coverage",
                            "Add diverse examples to training data",
                        ],
                    }
                    mlflow.log_dict(gap_info, f"accuracy_gap_{task}_{slice_type}.json")
                    alert_triggered = True
                    alert_msg = f"⚠️ Accuracy gap {acc_gap:.2f} in task '{task}' across {slice_type} slices"
                    alert_messages.append(alert_msg)

            # Log slice results
            mlflow.log_dict(results, f"bias_results_{task}_{slice_type}.json")

        # Generate Fairlearn visualizations for this task
        create_fairlearn_visualizations(merged_df, task, experiment_id)

        # Create and log fairness dashboard
        dashboard_path = create_fairness_dashboard(merged_df, task)
        mlflow.log_artifact(dashboard_path, f"fairness_dashboard_{task}")

        # Send alerts if triggered
        if alert_triggered:
            alert_body = "\n".join(alert_messages)
            send_email_notification(
                error_type="BiasAlert",
                error_message=alert_body,
                request_id="bias_checker",
            )

    # Save failure cases and full evaluation
    pd.DataFrame(failure_cases).to_csv("failure_cases.csv", index=False)
    mlflow.log_artifact("failure_cases.csv")
    merged_df.to_csv("bias_evaluation.csv", index=False)
    mlflow.log_artifact("bias_evaluation.csv")


def main(predicted_csv_path, labeled_csv_path, enron_csv_path=ENRON_EMAILS_CSV_PATH):
    """
    Main function to run bias checking.

    Args:
        predicted_csv_path (str): Path to CSV with model predictions
        labeled_csv_path (str): Path to CSV with ground truth labels
        enron_csv_path (str): Path to Enron emails dataset
    """
    with mlflow.start_run(
        nested=True, experiment_id=experiment_id, run_name="bias_checker_run"
    ):
        # Log MLflow configuration for reference
        backend_uri = mlflow.get_tracking_uri()
        print(f"✅ MLflow Tracking URI: {backend_uri}")
        print(f"📌 MLflow Run ID: {mlflow.active_run().info.run_id}")
        print(f"🔗 View locally: mlflow ui --backend-store-uri '{backend_uri}'")

        # Log parameters
        mlflow.log_param("predicted_csv_path", predicted_csv_path)
        mlflow.log_param("labeled_csv_path", labeled_csv_path)
        mlflow.log_param("enron_csv_path", enron_csv_path)

        # Load datasets
        labeled_df = pd.read_csv(labeled_csv_path)
        predicted_df = pd.read_csv(predicted_csv_path)

        # Get sender information from Enron dataset
        enron_df = pd.read_csv(enron_csv_path)[["Message-ID", "From"]].rename(
            columns={"From": "Sender"}
        )

        # Merge sender info with labeled data
        labeled_df = pd.merge(labeled_df, enron_df, on="Message-ID", how="left")
        if labeled_df["Sender"].isna().all():
            labeled_df["Sender"] = "unknown"

        # Verify all required columns are present
        required_cols = [
            "Message-ID",
            "Subject",
            "Body",
            "summary",
            "action_item",
            "draft_reply",
            "Sender",
        ]
        for df, name in [(labeled_df, "labeled"), (predicted_df, "predicted")]:
            missing = [col for col in required_cols if col not in df.columns]
            if missing and name == "predicted":
                missing = [col for col in missing if col != "Sender"]
            if missing:
                raise ValueError(f"Missing columns in {name} CSV: {missing}")

        # Filter out "no action items" cases for cleaner analysis
        predicted_df = remove_no_action_items(predicted_df)
        labeled_df = remove_no_action_items(labeled_df)

        # Run bias checking
        check_bias(labeled_df, predicted_df)


if __name__ == "__main__":
    main(PREDICTED_SAMPLE_CSV_PATH, LABELED_SAMPLE_CSV_PATH)
