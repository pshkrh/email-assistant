"""
Data Loader Module

This module provides functionality to load email datasets for testing
and validation purposes. It currently supports loading the Enron email dataset.
"""

import pandas as pd

from config import LABELED_SAMPLE_CSV_PATH


def load_enron_data():
    """
    Load the labeled Enron email dataset for model evaluation.

    The dataset contains email content with human-labeled summaries,
    action items, and draft replies for evaluation.

    Returns:
        DataFrame: Pandas DataFrame containing the labeled Enron email data
    """
    # Read the CSV file with labeled data
    df = pd.read_csv(LABELED_SAMPLE_CSV_PATH)
    return df
