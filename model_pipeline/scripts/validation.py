import spacy
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from config import LABELED_CSV, PREDICTED_CSV  # Use paths from config.py
import mlflow
import numpy as np
from bert_score import score as bert_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

# Load spaCy Named Entity Recognition (NER) Model
nlp = spacy.load("en_core_web_sm")

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


def extract_named_entities(text):
    """Extract named entities (e.g., people, dates, locations, numbers) from text using spaCy."""
    doc = nlp(text)
    return set([ent.text.lower() for ent in doc.ents])  # Return lowercase entities


def calculate_bert_score(pred_text, true_text):
    """Compute BERTScore for predicted and true text."""
    P, R, F1 = bert_score([pred_text], [true_text], lang="en", verbose=False)
    return F1.item()  # Return the F1 score


def calculate_tfidf_similarity(pred_text, true_text):
    """Compute TF-IDF cosine similarity between predicted and true text."""
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([pred_text, true_text])
    similarity = cosine_similarity(vectors[0], vectors[1])[0][0]
    return similarity


def calculate_named_entity_overlap(pred_text, true_text):
    """Calculate Named Entity Overlap Score (NER) between predicted and true text."""
    pred_entities = extract_named_entities(pred_text)
    true_entities = extract_named_entities(true_text)

    if not true_entities:  # If no entities in true label, rely on BERTScore
        return 1.0

    overlap = len(pred_entities.intersection(true_entities)) / len(true_entities)
    return overlap  # Score between 0 (no match) and 1 (all entities match)


def calculate_action_item_similarity(pred_text, true_text):
    """Compute final similarity score for action items using Named Entities + BERTScore."""
    # Define negation phrases, including cases where they start with "- "
    if true_text.lstrip().startswith(negation_phrases):
        return 1.0
    bert_f1 = calculate_bert_score(pred_text, true_text)
    entity_overlap = calculate_named_entity_overlap(pred_text, true_text)

    # Weighted combination: Give more importance to entity overlap (factual correctness)
    final_score = (0.6 * bert_f1) + (0.4 * entity_overlap)
    return final_score


def validate_outputs(predicted):
    """Compare predicted outputs with labeled data using BERTScore and Named Entity Matching for action items."""

    labeled_df = pd.read_csv(LABELED_CSV)

    results = {
        "summary": defaultdict(list),
        "action_item": defaultdict(list),
        "draft_reply": defaultdict(list),
    }
    true_labels = {
        "summary": defaultdict(list),
        "action_item": defaultdict(list),
        "draft_reply": defaultdict(list),
    }

    matched_count = 0
    counter = 0

    for _, row in labeled_df.iterrows():
        msg_id = row["Message-ID"]

        if msg_id in predicted["Message-ID"].values:
            matched_count += 1
            for task in results.keys():
                pred = predicted.loc[predicted["Message-ID"] == msg_id, task].values[0]
                true = row[task]

                if task == "action_item":
                    if true.lstrip().startswith(negation_phrases):
                        counter += 1
                        continue
                    else:
                        final_score = calculate_action_item_similarity(pred, true)
                else:
                    pass
                    # # Compute BERTScore for summaries & draft replies
                    # bert_f1 = calculate_bert_score(pred, true)
                    # tfidf_sim = calculate_tfidf_similarity(pred, true)
                    # final_score = (0.8 * bert_f1) + (0.2 * tfidf_sim)  # Weighted similarity

                for threshold in np.arange(0.6, 1.0, 0.05):
                    if task == "action_item":
                        results[task][threshold].append(
                            1 if final_score >= threshold else 0
                        )
                        true_labels[task][threshold].append(1)
                    # results[task][threshold].append(1 if final_score >= threshold else 0)
                    # true_labels[task][threshold].append(1)

    print(f"Matched {matched_count} emails for validation.")
    print(f"Counter - {counter}")

    metrics = {
        "summary": defaultdict(dict),
        "action_item": defaultdict(dict),
        "draft_reply": defaultdict(dict),
    }
    with mlflow.start_run(nested=True):
        for task in results.keys():
            for threshold in np.arange(0.6, 1.0, 0.05):
                precision = (
                    precision_score(
                        true_labels[task][threshold],
                        results[task][threshold],
                        zero_division=0,
                    )
                    * 100
                )
                recall = (
                    recall_score(
                        true_labels[task][threshold],
                        results[task][threshold],
                        zero_division=0,
                    )
                    * 100
                )
                f1 = (
                    f1_score(
                        true_labels[task][threshold],
                        results[task][threshold],
                        zero_division=0,
                    )
                    * 100
                )
                accuracy = (
                    accuracy_score(
                        true_labels[task][threshold], results[task][threshold]
                    )
                    * 100
                )

                metrics[task][threshold] = {
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "accuracy": accuracy,
                }

                mlflow.log_metric(f"{task}_precision_{threshold}", precision)
                mlflow.log_metric(f"{task}_recall_{threshold}", recall)
                mlflow.log_metric(f"{task}_f1_{threshold}", f1)
                mlflow.log_metric(f"{task}_accuracy_{threshold}", accuracy)

    return metrics


def run_validation():
    """Run validation and print results."""
    print(f"Loading predictions from {PREDICTED_CSV}...")
    predicted_outputs = pd.read_csv(PREDICTED_CSV)

    print("Running validation...")
    metrics = validate_outputs(predicted_outputs)

    for task, thresholds in metrics.items():
        for threshold, scores in thresholds.items():
            print(
                f"{task.capitalize()} - {threshold} - Recall: {scores['recall']:.2f}, Precision: {scores['precision']:.2f}, "
                f"F1: {scores['f1']:.2f}, Accuracy: {scores['accuracy']:.2f}"
            )
    return metrics


if __name__ == "__main__":
    run_validation()
