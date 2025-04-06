# model_pipeline/config.py
import os
from get_project_root import project_root

# Project root directory path
PROJECT_ROOT = project_root()

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

# TODO: i have changed the path of the DATA_DIR, so have to change the path of the credentials as well
GMAIL_API_CREDENTIALS = os.path.join(CREDENTIALS_DIR, "MailMateCredential.json")
TOKEN_DIR = os.path.join(CREDENTIALS_DIR, "user_tokens")
SERVICE_ACCOUNT_FILE = os.path.join(CREDENTIALS_DIR, "GoogleCloudCredential.json")

# Model .env path

MODEL_ENV_PATH = os.path.join(PROJECT_ROOT, "model_pipeline", ".env")

# Gmail API Configuration
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
FLASK_PORT = 8000

# MLflow Configuration
MLFLOW_LOG_DIR = os.path.join(PROJECT_ROOT, "model_pipeline", "logs")
MLFLOW_EXPERIMENT_NAME = "MailMate_Email_Assistant"

# DB configurations
DB_NAME = "mail_mate_user_data"
USER = "postgres"
PASSWORD = "postgres"
HOST = "35.226.149.135"
PORT = "5432"
