# model_pipeline/validation.py
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from config import LABELED_CSV
import mlflow


def validate_outputs(predicted, labeled):
    """Compare predicted outputs with labeled data."""
    labeled_df = pd.read_csv(LABELED_CSV)
    results = {"summary": [], "action_items": [], "draft_reply": []}
    true_labels = {"summary": [], "action_items": [], "draft_reply": []}

    for _, row in labeled_df.iterrows():
        msg_id = row["Message-ID"]
        if msg_id in predicted:
            for task in results.keys():
                pred = predicted[msg_id][task]
                true = row[task]
                results[task].append(1 if pred.strip() == true.strip() else 0)
                true_labels[task].append(true)

    metrics = {}
    with mlflow.start_run(nested=True):
        for task in results.keys():
            metrics[task] = {
                "accuracy": accuracy_score([1] * len(results[task]), results[task]),
                "f1": f1_score(
                    [1] * len(results[task]), results[task], zero_division=0
                ),
            }
            mlflow.log_metric(f"{task}_accuracy", metrics[task]["accuracy"])
            mlflow.log_metric(f"{task}_f1", metrics[task]["f1"])
    return metrics


def run_validation(predicted_outputs):
    """Run validation and print results."""
    metrics = validate_outputs(predicted_outputs)
    for task, scores in metrics.items():
        print(
            f"{task.capitalize()} - Accuracy: {scores['accuracy']:.2f}, F1: {scores['f1']:.2f}"
        )
