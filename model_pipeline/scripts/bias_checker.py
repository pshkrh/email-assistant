# model_pipeline/bias_checker.py
from fairlearn.metrics import MetricFrame, selection_rate
import pandas as pd
from config import ENRON_CSV
import mlflow


def check_bias(predicted_outputs, sensitive_feature="From"):
    """Check bias in LLM outputs using Fairlearn."""
    enron_df = pd.read_csv(ENRON_CSV)
    data = {"Message-ID": [], "Prediction": [], sensitive_feature: []}

    for msg_id, outputs in predicted_outputs.items():
        row = enron_df[enron_df["Message-ID"] == msg_id].iloc[0]
        data["Message-ID"].append(msg_id)
        data["Prediction"].append(len(outputs["summary"].split()))  # Proxy for quality
        data[sensitive_feature].append(row[sensitive_feature])

    df = pd.DataFrame(data)
    mf = MetricFrame(
        metrics={"selection_rate": selection_rate},
        y_true=df["Prediction"] > df["Prediction"].median(),
        y_pred=df["Prediction"] > df["Prediction"].median(),
        sensitive_features=df[sensitive_feature],
    )
    with mlflow.start_run(nested=True):
        mlflow.log_param("sensitive_feature", sensitive_feature)
        for group, rate in mf.by_group["selection_rate"].items():
            mlflow.log_metric(f"selection_rate_{group}", rate)
        mlflow.log_text(mf.by_group.to_string(), "bias_by_group.txt")
    print("Bias Analysis:")
    print(mf.by_group)
