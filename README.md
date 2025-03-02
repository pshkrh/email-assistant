
# MailMate – Your Email Assistant

## Team Members
- [Shubh Desai](https://github.com/username)  
- [Pushkar Kurhekar](https://github.com/username)  
- [Aalap Desai](https://github.com/username)  
- [Deep Prajapati](https://github.com/username)  
- [Shubham Mendapara](https://github.com/username)  

<p align="center">  
    <br>
    <a href="#">
        <img height=80 src="https://cdn.svgporn.com/logos/python.svg" alt="Python" title="Python" hspace=15/>
        <img height=80 src="https://cdn.svgporn.com/logos/airflow-icon.svg" alt="Airflow" title="Airflow" hspace=15/>
        <img height=80 src="https://cdn.svgporn.com/logos/docker-icon.svg" alt="Docker" title="Docker" hspace=15/>
        <img height=80 src="https://cdn.svgporn.com/logos/google-cloud.svg" alt="Google Cloud Platform" title="Google Cloud Platform" hspace=15/>
    </a>	
</p>

---

## Table of Contents
1. [Introduction](#introduction)  
2. [Dataset Information](#dataset-information)  
3. [Installation & Prerequisites](#installation--prerequisites)  
4. [Data Pipeline Overview](#data-pipeline-overview)  
5. [Machine Learning Pipeline](#machine-learning-pipeline)  
6. [Tools Used for MLOps](#tools-used-for-mlops)  
7. [Project Pipeline Flow](#project-pipeline-flow)  
8. [Model Insights & Monitoring](#model-insights--monitoring)  
9. [Cost Analysis](#cost-analysis)  
10. [Contributing / Development Guide](#contributing--development-guide)  
11. [License](#license)  
12. [Contact](#contact)  

---


# Introduction
In today’s fast-paced work environment, professionals struggle with **email overload**, spending hours reading, organizing, and responding to messages. Traditional email tools offer basic filtering and reply suggestions but lack **deep contextual understanding** and **smart prioritization**. **MailMate** is an AI-powered email assistant designed to **automate email summarization, generate intelligent replies, and extract action items**, allowing users to manage their inboxes efficiently.  

MailMate utilizes **Natural Language Processing (NLP)** and **Machine Learning (ML)** to provide **context-aware email insights**. It integrates with **Gmail, Outlook, or other email services** to streamline workflows by **highlighting key information, drafting accurate responses, and identifying critical follow-ups**. Unlike traditional tools, it doesn’t just scan emails—it **understands** them, helping users focus on essential tasks rather than sifting through long threads.  

### How MailMate Works  

MailMate performs a **series of AI-driven tasks** to enhance email management. It starts by **preprocessing emails**, removing unnecessary text (footers, disclaimers, redundant threads), and then applies **NLP models** for information extraction. Using **transformers**, it generates **concise summaries**, saving users from reading long conversations. The system then identifies **action items**, such as meeting requests, deadlines, or pending approvals, structuring them for easy tracking. Additionally, MailMate provides **smart reply suggestions**, allowing users to respond quickly while maintaining context and professionalism.  

To ensure **scalability and reliability**, MailMate follows **MLOps best practices**. The pipeline is orchestrated with **Apache Airflow**, ensuring seamless data processing. **Data Version Control (DVC)** tracks dataset updates, enabling reproducibility in model training. The system is deployed on **Google Cloud Platform (GCP) with Vertex AI**, ensuring real-time AI inference. MailMate also includes **bias detection mechanisms** using **Fairlearn** and **SliceFinder**, ensuring fair treatment across different user demographics.  

MailMate revolutionizes email management by **reducing clutter, improving productivity, and automating communication workflows**. With its AI-powered capabilities, it transforms inboxes from a burden into a **well-organized, high-priority communication hub**.  
 

---

# Dataset Information


The dataset used for this project is the **Enron Email Dataset**, a publicly available collection of **~500,000 emails** from the Enron Corporation. It is widely used for **Natural Language Processing (NLP)** tasks such as **email summarization, classification, and response generation**. The dataset contains structured fields, which are processed for model training and evaluation.

### **Data Sources**  
- **Enron Email Dataset:** [Enron Dataset Link](https://www.cs.cmu.edu/~enron/)  
- **Additional APIs:** Gmail API (for real-time email processing and integration) 


### **Dataset Overview**  

| **Attribute**   | **Details**  |
|----------------|-------------|
| **Dataset Name** | Enron Email Dataset |
| **Records** | ~500,000 emails |
| **Size** | 1.7GB |
| **Format** | Plain text files |
| **Fields** | Sender, Recipient, Subject, Body, Date |
| **Language** | English |
| **Usage** | Training and fine-tuning NLP models for summarization and draft reply generation | 

### **Data Card**  

| **Variable Name**  | **Role**     | **Type**        | **Description**                                  | **Missing Values** |
|--------------------|-------------|----------------|--------------------------------------------------|--------------------|
| **Email_ID**       | Identifier   | String         | Unique identifier for each email                 | No                 |
| **Sender**         | Feature      | String         | Email address of the sender                      | No                 |
| **Recipient(s)**   | Feature      | String (List)  | Email addresses of the recipients                | Yes (Partial)      |
| **Subject**        | Feature      | String         | Subject line of the email                        | Yes (Few)          |
| **Body**           | Feature      | Text           | Full email content                              | No                 |
| **Date**           | Timestamp    | DateTime       | Date and time the email was sent                 | No                 |
| **Attachments**    | Metadata     | String (List)  | Names of attached files                          | Yes (Mostly)       |
| **Thread_ID**      | Identifier   | String         | Identifies if an email is part of a thread       | Yes (Partial)      |
| **Reply-To**       | Metadata     | String         | Indicates whether an email is a reply            | Yes (Few)          |

The dataset is **cleaned, preprocessed, and structured** to remove redundant metadata, normalize text, and extract meaningful insights for model training.

### **Data Rights and Privacy**  
- The **Enron Email Dataset** is **publicly available** for research purposes.  
- Any real-world user data will be accessed **only via API** with explicit **user consent**.  
- **GDPR-compliant** security measures will be followed to ensure data privacy and compliance with international regulations.  

---

# Project Scope  

The detailed project report is available in the repository. You can access it using the link below:  

📄 **[Project Scope (PDF)](report/report.pdf)**  

Alternatively, if viewing from GitHub, you can navigate to the **report/** folder and open `report.pdf` manually.

---

# Installation & Prerequisites

### Prerequisites
1. **git** installed on your machine.  
2. **Python >= 3.8** installed (check using `python --version`).  
3. **Docker** daemon/desktop installed and running (for containerizing the Airflow pipeline).  
4. (Optional) **GPU** setup if you plan to train large-scale NLP models locally.

### User Installation

1. **Clone** the repository:
    ```bash
    git clone https://github.com/pshkrh/mlops-project.git
    cd mlops-project
    ```

2. **Check Python version** (>= 3.8):
    ```bash
    python --version
    ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Run Airflow**:
    ```bash
    docker compose up airflow-init
    docker compose up
    ```

5. **Run the DAG in Airflow**:  
   - Log into Airflow UI at **localhost:8080**  
   - Enable and trigger the **mailmate_data_pipeline** DAG.  

6. **Shutdown** containers:
    ```bash
    docker compose down
    ```

---

# Data Pipeline Overview  

MailMate's **data pipeline** is designed to handle **end-to-end email processing**, ensuring efficient data ingestion, transformation, and model training. The pipeline is orchestrated using **Apache Airflow**, which automates workflows, maintains scalability, and ensures fault tolerance. The system follows **MLOps best practices**, including **data validation, version control, anomaly detection, and automated model retraining**.

---

### **Key Pipeline Components**  

MailMate's pipeline consists of several stages to ensure clean, structured, and reproducible data for machine learning.

### **1️⃣ Data Acquisition**  
📥 **Goal**: Fetch and store email data from external sources.  

- **Enron Dataset Download**: The dataset is ingested from the **Enron Email Dataset**. A scheduled job runs periodically to pull new data if updates exist.  
- **Gmail API Integration** *(Optional)*: If enabled, real-time emails are fetched from a user's Gmail inbox (with explicit consent).  
- **Storage Format**: Raw email data is stored in **plain text files or structured databases** for easy access.  
- **Airflow DAG Task**: `fetch_data_task` automates the **data acquisition process**, ensuring a seamless ingestion pipeline.  

---

### **2️⃣ Data Preprocessing**  
🛠️ **Goal**: Transform raw email data into a structured format for NLP processing.  

- **Cleaning**:  
  - Remove email footers, disclaimers, and signatures.  
  - Strip HTML tags and unnecessary whitespace.  
- **Tokenization & Normalization**:  
  - Convert text to lowercase and apply tokenization techniques.  
  - Remove special characters and stopwords to retain meaningful text.  
- **Named Entity Recognition (NER)**:  
  - Extract key entities such as names, organizations, dates, and locations.  
- **Feature Engineering**:  
  - Extract metadata, such as email length, word frequency, and sentiment scores.  
- **Airflow DAG Task**: `preprocess_data_task` automates the **data cleaning and transformation process**.  

---

### **3️⃣ Schema Validation**  
✔️ **Goal**: Ensure data consistency and enforce schema rules.  

- Uses **Great Expectations** or **TensorFlow Data Validation (TFDV)** to validate the structure of incoming emails.  
- Ensures fields like `sender`, `recipient`, `subject`, and `body` follow predefined formats.  
- **Detects schema drifts**, alerting the team if unexpected changes occur in the data.  
- **Airflow DAG Task**: `validate_schema_task` runs **automatic schema validation** after preprocessing.  

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

- **Outlier Detection**: Flags **suspicious emails** based on:  
  - Abnormally long email body content.  
  - High email frequency from a single sender.  
  - Presence of spam keywords or phishing attempts.  
- **Missing Values & Corrupt Data Handling**:  
  - Identifies missing fields (e.g., `recipient` missing).  
  - Fixes minor corruptions (e.g., truncated emails).  
- **Automated Alert System**:  
  - If anomalies exceed a threshold, **alerts are sent via Slack or email**.  
- **Airflow DAG Task**: `detect_anomalies_task` runs **data integrity checks and alerts** the team in case of inconsistencies.  

---

### **6️⃣ Automated Model Training**  
🤖 **Goal**: Train and update AI models periodically with new data.  

- **Model Training Triggers**:  
  - New training cycle initiated when significant **new email data is added**.  
  - Periodic retraining to **adapt to evolving language patterns** in emails.  
- **Training Process**:  
  - Fine-tunes **T5, BART, or BERT-based** models for **email summarization**.  
  - Trains classification models to improve **action item extraction**.  
- **Model Versioning**:  
  - Stores each trained model in a **version-controlled repository**.  
  - Uses **MLflow** to track experiment results and performance metrics.  
- **Airflow DAG Task**: `train_model_task` automates **model training & deployment** when new data is available.  

---

### **Pipeline Flow in Airflow DAG**  

- **Each stage is scheduled and monitored via Airflow**, ensuring an end-to-end automated workflow.  
- **Gantt charts and logs** in Airflow help identify bottlenecks and optimize processing time.  



MailMate's data pipeline is designed for **scalability, automation, and fault tolerance**. By integrating **Airflow, DVC, anomaly detection, and schema validation**, it ensures that email data is **clean, structured, and reliable** for **AI-powered summarization and automation**.

 


---

# Tools Used for MLOps

1. **GitHub Actions**: Automated testing & linting.  
2. **Docker & Airflow**: Containerized environment, pipeline orchestration.  
3. **DVC**: Data version control.  
4. **MLflow**: Experiment tracking.  
5. **GCP**: Scalable model hosting.

---

# Project Pipeline Flow

[ Data Source (Enron/Gmail) ]
–> [ Preprocessing & Cleaning ]
–> [ DVC Storage ]
–> [ Airflow Orchestration ]
–> [ Model Training & Tuning ]
–> [ MLflow Tracking ]
–> [ Deployment on GCP Vertex AI ]
–> [ Monitoring & Alerting ]


---
# Testing  

Before pushing code to GitHub, it is essential to **run tests locally** to ensure the project builds successfully and meets code quality standards. **Pylint** helps enforce **PEP 8 guidelines**, while **Pytest** ensures that all functionality works as expected.  

---

### Code Quality & Linting**  

To run Pylint with Pytest for an integrated quality check: 

```bash
pytest --pylint
```

### Running Test Suites

To execute all test cases,  run:  

```bash
pytest
```

To test specific modules, use:

```bash
pytest tests/test_download_dataset.py -v
pytest tests/test_dataframe.py -v
```

---

## Timeline Planning
| **Phase** | **Duration** |
|----------|------------|
| **Week 1-3** | Data acquisition, EDA, cleaning, preprocessing |
| **Week 4-6** | Model training (summarization, classification, action item extraction) |
| **Week 7-9** | Backend integration, API setup, UI development |
| **Week 10+** | Final testing, deployment, and demo preparation |

---


## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Contact

For questions or collaboration:
- Open an issue on this GitHub repo.  
- Or reach out to any of the team members directly.

---