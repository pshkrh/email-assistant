## Table of Contents

1. [Installation & Prerequisites](#installation--prerequisites)
2. [Model Pipeline Overview](#model-pipeline-overview)
3. [Code Structure](#code-structure)

# Installation & Prerequisites

### Prerequisites

1. **git** installed on your machine.
2. **Python == 3.11** installed (check using `python --version`).
3. **Docker** daemon/desktop installed and running (for containerizing the Airflow pipeline).

### User Installation

1. **Clone** the repository:

   ```bash
   git clone https://github.com/pshkrh/email-assistant.git
   cd email-assistant/model_pipeline
   ```

2. **Check Python version** (3.11):

   ```bash
    python --version
   ```

<!-- 3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ``` -->

3. Google Cloud Credentials

   - Create a credentials folder (if not present) inside model_pipeline/
   - Download Oauth client credentials,
     - Select Application as Desktop and give scope of GmailAPIService (https://mail.google.com/), Follow this (https://support.google.com/googleapi/answer/6158849?hl=en).
     - Store it with name MailMateCredential.json inside credentials folder
   - Create and download service account in Google cloud project
     - Store it with name GoogleCloudCredential.json inside credentials folder

4. Set Up .env

- Create .env in model_pipeline/ folder, check .env_sample

4. Run Docker
   - Build Image, docker build -t <IMAGE_NAME> .
   - Run Container, docker run -it --name=<CONTAINER_NAME> <IMAGE_NAME_YOU_GAVE>

# Code Structure

- model_pipeline/
  - This it the main folder for model_pipeline development
  - credentials/
    - This folder contains the OAuth, Service account and user GMAIL credentials
  - data/
    - This folder conatins the data to be used or saved
  - scripts/
    - This folder contains all the scripts used for model pipeline
      - config.py: Sets up configuration to used across files
      - data_loader.py: Loads enron data and returns dataframe
      - get_project_root.py: Returns project root directory
      - render_prompt.py: Renders prompt for llm_generator
      - render_criteria.py: Renders criteria for llm_ranker
      - fetch_gmail_threads.py: Get thread from gmail
      - main.py: Runs the pipeline
      - llm_generator.py: Sends request to LLM for provided tasks and return dictionary
      - llm_ranker.py: Sends request to LLM to rank llm_generator outputs
      - output_verifier.py: Verifies if the llm_ranker output is as expected
      - validation.py: Validates labeled and predicted data

---
