# model_pipeline/validation.py
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from config import LABELED_CSV
import mlflow
from get_project_root import project_root
from output_verifier import verify_all_outputs
import os
from llm_ranker import rank_all_outputs
from llm_generator import process_email_body
from fuzzywuzzy import fuzz
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re   
import string


# Initialize NLTK's Lemmatizer
lemmatizer = WordNetLemmatizer()

# Define stopwords list
STOPWORDS = set(stopwords.words("english"))

def clean_text(text):
    """Normalize text by removing stopwords, punctuation, and lemmatizing words."""
    text = text.lower()  # Convert to lowercase
    text = re.sub(r"\s+", " ", text)  # Remove extra spaces
    text = text.translate(str.maketrans("", "", string.punctuation))  # Remove punctuation
    words = text.split()  # Tokenize
    words = [lemmatizer.lemmatize(word) for word in words if word not in STOPWORDS]  # Lemmatize & remove stopwords
    return " ".join(words)

def is_text_match(pred, true, threshold=85):
    """Check if two texts are similar after cleaning and applying fuzzy matching."""
    norm_pred = clean_text(pred)
    norm_true = clean_text(true)

    # Fast exact match
    if norm_pred == norm_true:
        return True

    # Fuzzy match
    similarity_score = fuzz.ratio(norm_pred, norm_true)
    return similarity_score >= threshold

def validate_outputs(predicted):
    """Compare predicted outputs with labeled data."""

    PROJECT_ROOT = project_root()
    prompt_file_path = os.path.join(
        PROJECT_ROOT, "data_pipeline", "data", "enron_balanced_short_emails.csv"
    )

    labeled_df = pd.read_csv(prompt_file_path)
    results = {"summary": [], "action_item": [], "draft_reply": []}
    true_labels = {"summary": [], "action_item": [], "draft_reply": []}

    for _, row in labeled_df.iterrows():
        msg_id = row["Message-ID"]
        if True: #msg_id in predicted:
            for task in results.keys():
                pred = predicted[task]
                true = " " #row[task]
                results[task].append(1 if is_text_match(pred, true) else 0)
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


def main():
 
    body = """
        Checked out
        ---------- Forwarded message ---------
        From: Try <try8200@gmail.com>
        Date: Sun, Mar 9, 2025 at 8:41 PM
        Subject: Fwd: Test
        To: Shubh Desai <shubhdesai111@gmail.com>



        Check out this
        ---------- Forwarded message ---------
        From: Shubh Desai <shubhdesai111@gmail.com>
        Date: Sun, Mar 9, 2025 at 8:37 PM
        Subject: Re: Test
        To: Try <try8200@gmail.com>


        Hey, once again

        On Sun, Mar 9, 2025 at 8:36 PM Try <try8200@gmail.com> wrote:
        hello Shubh

        On Sun, Mar 9, 2025 at 8:35 PM Shubh Desai <shubhdesai111@gmail.com> wrote:
        Hello Try
        we have a meeting tomorrow at 10am, related to the project and its important to discuss the project and its progress
        Also we have a important deadline for the project on 30th march of this month. So we need to speed up the process and complete the project on time.

    """ 
        
    tasks = ["summary", "action_item", "draft_reply"]
    userEmail = "try8200@gmail.com"

    llm_outputs = process_email_body(body, tasks, userEmail)
    ranked_outputs = rank_all_outputs(llm_outputs, tasks, body)
    best_outputs = verify_all_outputs(ranked_outputs, tasks, body, userEmail)

    # 3. Now pass `predicted_outputs` and the labeled CSV to run_validation
    metrics = run_validation(best_outputs)

    # 4. Optionally, do something else with 'metrics', or just let the script finish
    print("Validation complete. Summary of metrics:", metrics)

if __name__ == "__main__":
    main()