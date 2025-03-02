import pandas as pd


def create_body_length_groups():
    df = pd.read_csv("./data_pipeline/data/enron_emails.csv")
    df["Body_Length"] = df["Body"].apply(len)

    bins = [1, 1000, 10000, 100000, 500000, 2011422]
    labels = ["Short", "Medium", "Long", "Very Long", "Extremely Long"]

    df["Body_Length_Group"] = pd.cut(
        df["Body_Length"], bins=bins, labels=labels, right=True
    )

    # df.to_csv("./data_pipeline/data/body_groups.csv", index=False)


"""
Will create more functions using FairLearn after model creation
as it will be required to biasness detection and statistics
"""
