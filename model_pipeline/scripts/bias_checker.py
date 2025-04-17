import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
from rouge_score import rouge_scorer
from config import LABELED_SAMPLE_CSV_PATH, PREDICTED_SAMPLE_CSV_PATH
from bert_score import score
from transformers import logging
import spacy
import matplotlib.pyplot as plt
import seaborn as sns
import json
import mlflow
from send_notification import send_email_notification

from mlflow_config import configure_mlflow

# Path to enron_emails.csv
ENRON_EMAILS_CSV_PATH = "data_pipeline/data/enron_emails.csv"

logging.set_verbosity_error()
nlp = spacy.load("en_core_web_sm")

experiment = configure_mlflow()
experiment_id = experiment.experiment_id if experiment else None

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
    df["action_item"] = df["action_item"].astype(str)
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
    filtered_df = df[~df["action_item"].str.contains(f"(?i){pattern}", na=False)]
    filtered_df = filtered_df[
        ~filtered_df["action_item"].str.startswith(negation_phrases, na=False)
    ]
    filtered_df = filtered_df[filtered_df["action_item"].str.strip() != ""]
    return filtered_df


def extract_named_entities(text):
    if not isinstance(text, str):
        text = ""
    doc = nlp(text)
    return {ent.text.strip() for ent in doc.ents if ent.text.strip()}


def compute_bert_score(pred_text, true_text, model_type="roberta-large"):
    if not isinstance(true_text, str) and not isinstance(pred_text, str):
        return 1.0, 1.0, 1.0
    pred_text = str(pred_text) if isinstance(pred_text, str) else ""
    true_text = str(true_text) if isinstance(true_text, str) else ""

    P, R, F1 = score([pred_text], [true_text], model_type=model_type, verbose=False)
    return float(P[0]), float(R[0]), float(F1[0])


def calculate_rouge_scores(pred_text, true_text):
    pred_text = str(pred_text) if isinstance(pred_text, str) else ""
    true_text = str(true_text) if isinstance(true_text, str) else ""
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(true_text, pred_text)
    return scores["rougeL"].fmeasure


def classify_length_category(text):
    length = len(str(text))
    if length <= 700:
        return "short"
    elif length <= 1500:
        return "medium"
    else:
        return "long"


def classify_role(sender):
    if pd.isna(sender):
        return "unknown"
    sender = str(sender).lower()
    if "manager" in sender or "director" in sender:
        return "manager"
    return "team_member"


def compute_complexity(text):
    doc = nlp(str(text))
    sentences = list(doc.sents)
    avg_len = sum(len(sent) for sent in sentences) / len(sentences) if sentences else 0
    return "high" if avg_len > 50 else "low"


def check_bias(labeled_df, predicted_df):
    merged_df = pd.merge(
        labeled_df, predicted_df, on="Message-ID", suffixes=("_true", "_pred")
    )
    mlflow.log_dict(
        {"merged_df_columns": list(merged_df.columns)}, "merged_df_cols.json"
    )
    merged_df["length_slice"] = merged_df["Body_true"].apply(classify_length_category)
    merged_df["complexity_slice"] = merged_df["Body_true"].apply(compute_complexity)
    merged_df["role_slice"] = merged_df["Sender"].apply(classify_role)

    mlflow.log_dict(
        {
            "length_slice": merged_df["length_slice"].value_counts().to_dict(),
            "complexity_slice": merged_df["complexity_slice"].value_counts().to_dict(),
            "role_slice": merged_df["role_slice"].value_counts().to_dict(),
        },
        "slice_counts.json",
    )

    tasks = ["summary", "action_item", "draft_reply"]
    task_thresholds = {
        "summary": {"bert_f1": 0.8, "ner": 0.7, "rouge_l": 0.7},  # Tightened
        "action_item": {"bert_f1": 0.8, "ner": 0.8},  # Loosened
        "draft_reply": {"bert_f1": 0.8, "ner": 0.8},  # Loosened
    }

    failure_cases = []
    alert_triggered = False
    alert_messages = []
    for task in tasks:
        y_true_col = f"{task}_true"
        y_pred_col = f"{task}_pred"

        def compute_scores(row):
            bert_p, bert_r, bert_f1 = compute_bert_score(
                row[y_pred_col], row[y_true_col]
            )
            rouge_l = calculate_rouge_scores(row[y_pred_col], row[y_true_col])
            true_ents = extract_named_entities(row[y_true_col])
            pred_ents = extract_named_entities(row[y_pred_col])
            ner_coverage = (
                1.0
                if not true_ents
                else len(true_ents.intersection(pred_ents)) / len(true_ents)
            )

            scores = {
                "bert_f1": bert_f1,
                "rouge_l": rouge_l,
                "ner_coverage": ner_coverage,
            }

            thresholds = task_thresholds[task]
            is_correct = (
                bert_f1 >= thresholds["bert_f1"]
                and ner_coverage >= thresholds["ner"]
                and (task != "summary" or rouge_l >= thresholds["rouge_l"])
            )
            scores["correct"] = int(is_correct)

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

        merged_df[f"scores_{task}"] = merged_df.apply(compute_scores, axis=1)
        merged_df[f"y_true_{task}"] = 1
        merged_df[f"y_pred_{task}"] = merged_df[f"scores_{task}"].apply(
            lambda x: x["correct"]
        )

        for slice_type in ["length_slice", "complexity_slice", "role_slice"]:
            results = {}
            for group in merged_df[slice_type].unique():
                slice_df = merged_df[merged_df[slice_type] == group]
                if slice_df.empty:
                    continue

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

            if len(results) >= 2:
                acc_values = [v["accuracy"] for v in results.values()]
                acc_gap = max(acc_values) - min(acc_values)
                if acc_gap > 0.15:
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

            mlflow.log_dict(results, f"bias_results_{task}_{slice_type}.json")

        # if alert_triggered:
        alert_body = "\n".join(alert_messages)
        send_email_notification(
            error_type="BiasAlert",
            error_message=alert_body,
            request_id="bias_checker",
        )

    pd.DataFrame(failure_cases).to_csv("failure_cases.csv", index=False)
    mlflow.log_artifact("failure_cases.csv")
    merged_df.to_csv("bias_evaluation.csv", index=False)
    mlflow.log_artifact("bias_evaluation.csv")


def main(predicted_csv_path, labeled_csv_path, enron_csv_path=ENRON_EMAILS_CSV_PATH):
    with mlflow.start_run(
        nested=True, experiment_id=experiment_id, run_name="bias_checker_run"
    ):
        mlflow.log_param("predicted_csv_path", predicted_csv_path)
        mlflow.log_param("labeled_csv_path", labeled_csv_path)
        mlflow.log_param("enron_csv_path", enron_csv_path)
        labeled_df = pd.read_csv(labeled_csv_path)
        predicted_df = pd.read_csv(predicted_csv_path)
        enron_df = pd.read_csv(enron_csv_path)[["Message-ID", "From"]].rename(
            columns={"From": "Sender"}
        )
        labeled_df = pd.merge(labeled_df, enron_df, on="Message-ID", how="left")
        if labeled_df["Sender"].isna().all():
            labeled_df["Sender"] = "unknown"

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

        predicted_df = remove_no_action_items(predicted_df)
        labeled_df = remove_no_action_items(labeled_df)

        check_bias(labeled_df, predicted_df)


if __name__ == "__main__":
    main(PREDICTED_SAMPLE_CSV_PATH, LABELED_SAMPLE_CSV_PATH)
