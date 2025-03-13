# model_pipeline/config.py
import os

# Paths
DATA_DIR = "../data"
ENRON_CSV = os.path.join(DATA_DIR, "enron_emails.csv")
LABELED_CSV = os.path.join(DATA_DIR, "labeled_enron.csv")
GMAIL_API_CREDENTIALS = os.path.join(DATA_DIR, "credentials/MailMateCredentials.json")
TOKEN_DIR = os.path.join(DATA_DIR, "credentials/user_tokens")

# LLM Configuration
OPENAI_API_KEY = "your-openai-api-key"

# Gmail API Configuration
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
FLASK_PORT = 8000

# MLflow Configuration
MLFLOW_EXPERIMENT_NAME = "MailMate_Email_Assistant"
