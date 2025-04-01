import pandas as pd

# Load the CSV file
file_path = "/Users/shubhammendapara/Work/Northeastern/IE_7374/Project/mlops-project/data_pipeline/data/new_pred_label_enron_email.csv"
df = pd.read_csv(file_path)

# Rename columns (example: changing 'old_column_name' to 'new_column_name')
df.rename(columns={'Action Type': 'action_item'}, inplace=True)
df.rename(columns={'Suggested Reply': 'draft_reply'}, inplace=True)
df.rename(columns={'Summary': 'summary'}, inplace=True)

# Drop a specific column (example: dropping 'column_to_remove')
df.drop(columns=['Action Label'], inplace=True)

# Save the updated CSV
df.to_csv(file_path, index=False)

print("Column name updated and specified column removed successfully!")
