# model_pipeline/config.py
import os
import json
from get_project_root import project_root

# Project root directory path
PROJECT_ROOT = project_root()

# Check if running in Cloud Run
IN_CLOUD_RUN = os.environ.get("K_SERVICE") is not None
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "email-assistant-449706")

# Data directory path where all the data and yaml files are stored
DATA_DIR = os.path.join(PROJECT_ROOT, "model_pipeline", "data")

# Data files path
ENRON_CSV = os.path.join(DATA_DIR, "enron_emails.csv")
LABELED_CSV_PATH = os.path.join(DATA_DIR, "labeled_enron.csv")
PREDICTED_CSV_PATH = os.path.join(
    DATA_DIR, "predicted_enron.csv"
)  # pred csv for 100 mails
LABELED_SAMPLE_CSV_PATH = os.path.join(DATA_DIR, "labeled_enron_sample.csv")
PREDICTED_SAMPLE_CSV_PATH = os.path.join(DATA_DIR, "predicted_enron_sample.csv")

# LLM Configuration Files Path
STRUCTURE_PROMPTS_YAML = os.path.join(DATA_DIR, "llm_output_structure.yaml")
RANKER_CRITERIA_YAML = os.path.join(DATA_DIR, "llm_ranker_criteria.yaml")
GENERATOR_PROMPTS_YAML = os.path.join(DATA_DIR, "llm_generator_prompts.yaml")
ALTERNATE_GENERATOR_PROMPTS_YAML = os.path.join(
    DATA_DIR, "llm_generator_prompts_alternate.yaml"
)

# Credentials directory path where all the credentials are stored
CREDENTIALS_DIR = os.path.join(PROJECT_ROOT, "model_pipeline", "credentials")
os.makedirs(CREDENTIALS_DIR, exist_ok=True)  # Ensure the directory exists

# Secret Manager IDs (for Cloud Run)
GMAIL_API_SECRET_ID = os.environ.get("GMAIL_API_SECRET_ID", "gmail-credentials")
GMAIL_NOTIFICATION_SECRET_ID = os.environ.get(
    "GMAIL_NOTIFICATION_SECRET_ID", "gmail-notification"
)
SERVICE_ACCOUNT_SECRET_ID = os.environ.get(
    "SERVICE_ACCOUNT_SECRET_ID", "service-account-credentials"
)

# Credential paths
GMAIL_API_CREDENTIALS = os.path.join(CREDENTIALS_DIR, "MailMateCredential.json")
TOKEN_DIR = os.path.join(CREDENTIALS_DIR, "user_tokens")
SERVICE_ACCOUNT_FILE = os.path.join(CREDENTIALS_DIR, "GoogleCloudCredential.json")

# Model .env path
MODEL_ENV_PATH = os.path.join(PROJECT_ROOT, "model_pipeline", ".env")

# Gmail API Configuration
GMAIL_SCOPES = json.loads(
    os.environ.get("GMAIL_SCOPES", '["https://www.googleapis.com/auth/gmail.readonly"]')
)
FLASK_PORT = int(os.environ.get("FLASK_PORT", 8000))

# MLflow Configuration
MLFLOW_LOG_DIR = os.path.join(PROJECT_ROOT, "model_pipeline", "logs")
MLFLOW_EXPERIMENT_NAME = os.environ.get(
    "MLFLOW_EXPERIMENT_NAME", "MailMate_Email_Assistant"
)

# DB configurations
DB_NAME = os.environ.get("DB_NAME", "mail_mate_user_data")
USER = os.environ.get("DB_USER", "postgres")
PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
HOST = os.environ.get("DB_HOST", "34.57.73.104")
PORT = os.environ.get("DB_PORT", "5432")
