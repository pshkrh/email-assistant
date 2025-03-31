import pandas as pd

# Paths to files (adjust as needed)
LABELED_PATH = "model_pipeline\data\labeled_enron.csv"
PREDICTED_PATH = "model_pipeline\data\predicted_enron.csv"
OUTPUT_PATH = "model_pipeline\data\filtered_labeled_enron.csv"

def filter_labeled_data():
    print("Loading predicted Message-IDs...")
    predicted_df = pd.read_csv(PREDICTED_PATH)
    predicted_ids = predicted_df["Message-ID"].unique()

    print("Loading full labeled dataset...")
    labeled_df = pd.read_csv(LABELED_PATH)

    print("Filtering labeled data to only predicted Message-IDs...")
    filtered_labeled_df = labeled_df[labeled_df["Message-ID"].isin(predicted_ids)]

    print(f"Found {len(filtered_labeled_df)} matching rows.")
    filtered_labeled_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved filtered labeled data to: {OUTPUT_PATH}")

if __name__ == "__main__":
    filter_labeled_data()
