import spacy
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from config import LABELED_SAMPLE_CSV_PATH, PREDICTED_SAMPLE_CSV_PATH
import numpy as np
from bert_score import score as bert_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import mlflow
from mlflow_config import configure_mlflow
from transformers import logging as hf_logging
from send_notification import send_email_notification

hf_logging.set_verbosity_error()

nlp = spacy.load("en_core_web_sm")
experiment = configure_mlflow()
experiment_id = experiment.experiment_id if experiment else None
bert_invalid_examples = []
tfidf_invalid_examples = []

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


def is_valid_text(text):
    return isinstance(text, str) and text.strip().lower() != "nan"


def extract_named_entities(text):
    if not is_valid_text(text):
        return set()
    doc = nlp(text)
    return {ent.text.lower() for ent in doc.ents}


def calculate_bert_score(pred_text, true_text):
    if (isinstance(true_text, float) and np.isnan(true_text)) and (
        isinstance(pred_text, float) and np.isnan(pred_text)
    ):
        return 1.0
    if not (is_valid_text(pred_text) and is_valid_text(true_text)):
        bert_invalid_examples.append({"pred_text": pred_text, "true_text": true_text})
        mlflow.log_param("bert_skip_invalid_input", True)
        return 0.0
    try:
        P, R, F1 = bert_score([pred_text], [true_text], lang="en", verbose=False)
        return F1.item()
    except Exception as e:
        mlflow.log_param("bert_error", str(e))
        return 0.0


def calculate_tfidf_similarity(pred_text, true_text):
    if (
        not (is_valid_text(pred_text) and is_valid_text(true_text))
        and np.isnan(pred_text)
        and np.isnan(true_text)
    ):
        mlflow.log_param("tfidf_skip_invalid_input", True)
        tfidf_invalid_examples.append({"pred_text": pred_text, "true_text": true_text})
        return 1.0
    try:
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([pred_text, true_text])
        return cosine_similarity(vectors[0], vectors[1])[0][0]
    except Exception as e:
        mlflow.log_param("tfidf_error", str(e))
        return 0.0


def calculate_named_entity_overlap(pred_text, true_text):
    pred_entities = extract_named_entities(pred_text)
    true_entities = extract_named_entities(true_text)
    if not true_entities:
        return 1.0
    return len(pred_entities.intersection(true_entities)) / len(true_entities)


def calculate_action_item_similarity(pred_text, true_text):
    if not is_valid_text(true_text):
        return 1.0
    if true_text.lstrip().startswith(negation_phrases):
        return 1.0
    bert_f1 = calculate_bert_score(pred_text, true_text)
    entity_overlap = calculate_named_entity_overlap(pred_text, true_text)
    return (0.6 * bert_f1) + (0.4 * entity_overlap)


def validate_outputs(predicted_df, labeled_df):
    results = {
        task: defaultdict(list) for task in ["summary", "action_item", "draft_reply"]
    }
    true_labels = {
        task: defaultdict(list) for task in ["summary", "action_item", "draft_reply"]
    }

    matched_count = 0
    skipped = 0

    for _, row in labeled_df.iterrows():
        msg_id = row["Message-ID"]

        if msg_id not in predicted_df["Message-ID"].values:
            continue

        matched_count += 1
        for task in results.keys():
            pred = predicted_df.loc[predicted_df["Message-ID"] == msg_id, task].values[
                0
            ]
            true = row[task]

            if task == "action_item":
                score = calculate_action_item_similarity(pred, true)
            else:
                score = (0.8 * calculate_bert_score(pred, true)) + (
                    0.2 * calculate_tfidf_similarity(pred, true)
                )

            for threshold in np.arange(0.6, 1.0, 0.05):
                results[task][threshold].append(1 if score >= threshold else 0)
                true_labels[task][threshold].append(1)

    mlflow.log_param("matched_rows", matched_count)
    mlflow.log_param("skipped_rows", skipped)

    metrics = {task: defaultdict(dict) for task in results.keys()}
    for task in results:
        for threshold in results[task]:
            y_pred = results[task][threshold]
            y_true = true_labels[task][threshold]
            metrics[task][threshold] = {
                "precision": precision_score(y_true, y_pred, zero_division=0) * 100,
                "recall": recall_score(y_true, y_pred, zero_division=0) * 100,
                "f1": f1_score(y_true, y_pred, zero_division=0) * 100,
                "accuracy": accuracy_score(y_true, y_pred) * 100,
            }

    return metrics


def run_validation(predicted_csv_path, labeled_csv_path):
    with mlflow.start_run(
        nested=True, experiment_id=experiment_id, run_name="output_validation"
    ):
        backend_uri = mlflow.get_tracking_uri()
        print(f"✅ MLflow Tracking URI: {backend_uri}")
        print(f"📌 MLflow Run ID: {mlflow.active_run().info.run_id}")
        print(f"🔗 View locally: mlflow ui --backend-store-uri '{backend_uri}'")
        mlflow.log_param("predicted_path", predicted_csv_path)
        mlflow.log_param("labeled_path", labeled_csv_path)
        predicted_df = pd.read_csv(predicted_csv_path)
        labeled_df = pd.read_csv(labeled_csv_path)

        metrics = validate_outputs(predicted_df, labeled_df)

        alert_triggered = False
        alert_messages = []

        for task in metrics:
            for threshold, scores in metrics[task].items():

                # Alert condition
                if scores["f1"] < 85.0:
                    alert_triggered = True
                    alert_messages.append(
                        f"⚠️ F1 for {task} at threshold {threshold:.2f} is {scores['f1']:.2f} (below 85.0)"
                    )

        mlflow.log_dict(metrics, "task_validation_metrics.json")

        if bert_invalid_examples:
            mlflow.log_dict(
                {"bert_skipped_inputs": bert_invalid_examples},
                "bert_skipped_inputs.json",
            )
            mlflow.log_metric("bert_skipped_count", len(bert_invalid_examples))

        if tfidf_invalid_examples:
            mlflow.log_dict(
                {"tfidf_skipped_inputs": tfidf_invalid_examples},
                "tfidf_skipped_inputs.json",
            )
            mlflow.log_metric("tfidf_skipped_count", len(tfidf_invalid_examples))

        if alert_triggered:
            alert_body = "\n".join(alert_messages)
            send_email_notification(
                error_type="ValidationThresholdAlert",
                error_message=alert_body,
                request_id="validation_run",
            )

        return metrics


if __name__ == "__main__":
    run_validation(PREDICTED_SAMPLE_CSV_PATH, LABELED_SAMPLE_CSV_PATH)
