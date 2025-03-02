# MailMate – Your Email Assistant

## Team Members

- [Shubh Desai](https://github.com/username)
- [Pushkar Kurhekar](https://github.com/username)
- [Aalap Desai](https://github.com/desaiaalap)
- [Deep Prajapati](https://github.com/username)
- [Shubham Mendapara](https://github.com/username)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Dataset Information](#dataset-information)
3. [Installation & Prerequisites](#installation--prerequisites)
4. [Code Structure](#code-structure)
5. [Data Pipeline Overview](#data-pipeline-overview)

---

# Introduction

## In today’s fast-paced work environment, professionals struggle with **email overload**, spending hours reading, organizing, and responding to messages. Traditional email tools offer basic filtering and reply suggestions but lack **deep contextual understanding** and **smart prioritization**. **MailMate** is an AI-powered email assistant designed to **automate email summarization, generate intelligent draft replies, and extract action items**, allowing users to manage their inboxes efficiently.

# Dataset Information

The dataset used for this project is the **Enron Email Dataset**, a publicly available collection of **~500,000 emails** from the Enron Corporation. It is widely used for **Natural Language Processing (NLP)** tasks such as **email summarization, classification, and response generation**. The dataset contains structured fields, which are processed for model training and evaluation.

### **Data Sources**

- **Enron Email Dataset:** [Enron Dataset Link](https://www.cs.cmu.edu/~enron/)
- **Additional APIs:** Gmail API (for real-time email processing and integration)

### **Dataset Overview**

| **Attribute**    | **Details**                                                                      |
| ---------------- | -------------------------------------------------------------------------------- |
| **Dataset Name** | Enron Email Dataset                                                              |
| **Records**      | ~500,000 emails                                                                  |
| **Size**         | 1.7GB                                                                            |
| **Format**       | Plain text files                                                                 |
| **Fields**       | Sender, Recipient, Subject, Body, Date                                           |
| **Language**     | English                                                                          |
| **Usage**        | Training and fine-tuning NLP models for summarization and draft reply generation |

### **Data Card**

| **Variable Name** | **Role**   | **Type**      | **Description**                            | **Missing Values** |
| ----------------- | ---------- | ------------- | ------------------------------------------ | ------------------ |
| **Email_ID**      | Identifier | String        | Unique identifier for each email           | No                 |
| **Sender**        | Feature    | String        | Email address of the sender                | No                 |
| **Recipient(s)**  | Feature    | String (List) | Email addresses of the recipients          | Yes (Partial)      |
| **Subject**       | Feature    | String        | Subject line of the email                  | Yes (Few)          |
| **Body**          | Feature    | Text          | Full email content                         | No                 |
| **Date**          | Timestamp  | DateTime      | Date and time the email was sent           | No                 |
| **Attachments**   | Metadata   | String (List) | Names of attached files                    | Yes (Mostly)       |
| **Thread_ID**     | Identifier | String        | Identifies if an email is part of a thread | Yes (Partial)      |
| **Reply-To**      | Metadata   | String        | Indicates whether an email is a reply      | Yes (Few)          |

The dataset is **cleaned, preprocessed, and structured** to remove redundant metadata, normalize text, and extract meaningful insights for model training.

### **Data Rights and Privacy**

- The **Enron Email Dataset** is **publicly available** for research purposes.
- Any real-world user data will be accessed **only via API** with explicit **user consent**.
- **GDPR-compliant** security measures will be followed to ensure data privacy and compliance with international regulations.

---

# Installation & Prerequisites

### Prerequisites

1. **git** installed on your machine.
2. **Python == 3.11** installed (check using `python --version`).
3. **Docker** daemon/desktop installed and running (for containerizing the Airflow pipeline).

### User Installation

1. **Clone** the repository:

   ```bash
   git clone https://github.com/pshkrh/email-assistant.git
   cd email-assistant
   ```

2. **Check Python version** (3.11):

   ```bash
    python --version
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure DVC Setup**:

   - Create a Google Cloud Storage Bucket, follow this (https://www.mlwithramin.com/blog/dvc-lab1)
   - Save the credentials.json file at your desired location
   - In Terminal, at the root of the project i.e., email-assistant/, enter

   ```bash
     - dvc init
     - dvc remote add -d <desired_remote_name> gs://<your_bucket_name>
     - dvc remote modify <created_desired_remote_name> credentialpath <credentials.json_path_relative_to_email_assitant/>
   ```

5. **Run Airflow**:

   - Enter the following to your terminal from root_directory i.e., email-assistant/

   ```bash
   echo -e "AIRFLOW_UID=$(id -u)" > .env
   ```

   - FOR WINDOWS: Create a file called .env in the root folder same as docker-compose.yaml and set the user as follows:

   ```bash
   AIRFLOW_UID=50000
   ```

   - Create GMAIL API Oauth client and download its credential.json,

     - Select Application as Desktop and give scope of GmailAPIService - https://mail.google.com/, Follow this (https://support.google.com/googleapi/answer/6158849?hl=en)

     - Set these credentials as shown in .env file as shown in .env-sample file

     - You can skip creating GMAIL API Oauth client if you don't want to send email notifications, it will log error in anomaly task.

   - Initialize Database

   ```bash
   docker compose up airflow-init
   ```

   - Run Container

   ```bash
   docker compose up --build
   ```

6. **Run the DAG in Airflow**:

   - Keep watch for this line in terminal

   ```bash
   app-airflow-webserver-1  | 127.0.0.1 - - [17/Feb/2023:09:34:29 +0000] "GET /health HTTP/1.1" 200 141 "-" "curl/7.74.0"
   ```

   - Log into Airflow UI at **localhost:8080** using

   ```bash
    user:airflow
    password:airflow
   ```

   - Run the DAG by clicking on the play button on the right side of the window once you see **data_pipeline_dag**.

   - Task performance can be time consuming depending on the resources provided to docker.

7. **Shutdown** containers:

   ```bash
   docker compose down
   ```

8. **Store Data**:

   - From root email-assistant/

   ```bash
   dvc add data_pipeline/data/enron_emails.csv
   ```

   - Use dvc push to store it to your GCP bucket.

9. **Tests** :
   - To run tests from root diectory email_assistan/
   ```bash
   pytest data_pipeline/tests/*.py -v
   ```
   - For individual tests replace \* with test file name from data_pipeline/tests/

---

# Code Structure

## We are keeping main files at the root directory for easy access and understanding.

    - dags/ contains airflow code
    - data_pipeline/ contains scripts and data related to it.
    - logs/ contains airflow's logs

# Data Pipeline Overview

MailMate's **data pipeline** is designed to handle **end-to-end email processing**, ensuring efficient data ingestion, transformation, and model training. The pipeline is orchestrated using **Apache Airflow**, which automates workflows, maintains scalability, and ensures fault tolerance. The system follows **MLOps best practices**, including **data validation, version control, anomaly detection, and automated model retraining**.

---

### **Key Pipeline Components**

MailMate's pipeline consists of several stages to ensure clean, structured, and reproducible data for machine learning.

### **1️⃣ Data Acquisition**

📥 **Goal**: Fetch and store email data from external sources.

- **Enron Dataset Download**: The dataset is ingested from the **Enron Email Dataset**.
- **Gmail API Integration** : If enabled, real-time emails are fetched from a user's Gmail inbox (with explicit consent).
- **Storage Format**: Raw email data is stored in **csv files or structured databases** for easy access.
- **Airflow DAG Task**: `fetch_data_task` automates the **data acquisition process**, ensuring a seamless ingestion pipeline.

---

### **2️⃣ Data Preprocessing**

🛠️ **Goal**: Transform raw email data into a structured format.

- **Cleaning**:
  - Remove email footers, disclaimers, and signatures.
  - Strip HTML tags and unnecessary whitespace.
  - Remove special characters and stopwords to retain meaningful text.
- **Named Entity Recognition (NER)**:
  - Extract key entities such as names, dates, and Timezone.
  <!-- - **Feature Engineering**:
  - Extract metadata, such as email length, word frequency, and sentiment scores. -->
- **Airflow DAG Task**: `preprocess_data_task` automates the **data cleaning and transformation process**.

---

### **3️⃣ Schema Validation**

✔️ **Goal**: Ensure data consistency and enforce schema rules.

- Uses **Great Expectations** to validate the structure of incoming emails.
- Ensures fields like `sender`, `recipient`, `subject`, and `body` follow predefined formats.
- **Airflow DAG Task**: `validate_schema_task` runs **automatic schema validation** after preprocessing.
- **Detects schema drifts**, alerting the team if unexpected changes occur in the data.

---

### **4️⃣ Data Versioning (DVC)**

📂 **Goal**: Maintain version control of datasets for reproducibility.

- Uses **Data Version Control (DVC)** to track changes in email datasets.
- Ensures that different versions of the dataset are available for **model reproducibility**.
- Stores metadata, keeping track of file changes while allowing **rollbacks** if needed.
- **DVC ensures consistency** across different experiments and team members working with the data.
- **Airflow DAG Task**: `track_data_version_task` integrates **DVC into the pipeline**, ensuring that every dataset version is properly recorded.

---

### **5️⃣ Anomaly Detection**

⚠️ **Goal**: Identify irregularities in email patterns and alert the system.

- **Non-Null Constraints:**

  - Ensures that critical fields like `Message-ID`, `From`, and `Body` are never null.
  - `Date` should not be null in at least 95% of the cases.
  - `X-From` should not be null in at least 90% of the cases.

- **Email Format Validation:**
  - Validates that `From`, `To`, `Cc`, and `Bcc` follow proper email regex patterns with 95% accuracy.

**Uniqueness Check:**

- `Message-ID` should be unique across all records.

- **Automated Alert System**:
  - If anomalies exceed a threshold, **alerts are sent via email**.
- **Airflow DAG Task**: `detect_anomalies_task` runs **data integrity checks and alerts** the team in case of inconsistencies.

---

### 6️⃣ **Testing**

---

### Before pushing code to GitHub, it is essential to run tests locally to ensure the project builds successfully and meets code quality standards. Pylint helps enforce PEP 8 guidelines, while Pytest ensures that all functionality works as expected.

---

## **Code Quality & Linting**

**To run Pylint with Pytest for an integrated quality check:**

```bash
pytest data_pipeline/ --pylint -v
```

**To test specific modules, use from root directory:**

```bash
pytest data_pipeline/tests/<test_filename.py> --pylint -v

Like:

pytest data_pipeline/tests/test_download_dataset.py --pylint -v
```

**To run all tests, from root directory run:**

```bash
pytest data_pipeline/tests/*.py -v
```

---

- **Each stage is scheduled and monitored via Airflow**, ensuring an end-to-end automated workflow.
- **Gantt charts and logs** in Airflow help identify bottlenecks and optimize processing time.

MailMate's data pipeline is designed for **scalability, automation, and fault tolerance**. By integrating **Airflow, DVC, anomaly detection, and schema validation**, it ensures that email data is **clean, structured, and reliable** for **AI-powered summarization and automation**.

## Contact

For questions or collaboration:

- Open an issue on this GitHub repo.
- Or reach out to any of the team members directly.

---
