import pandas as pd
from config import DATA_DIR, LABELED_SAMPLE_CSV_PATH


def load_enron_data():
    df = pd.read_csv(LABELED_SAMPLE_CSV_PATH)
    return df
