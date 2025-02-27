# Project Title: Data Version Control with DVC and Git

This repository demonstrates how to manage and version-control a dataset using **DVC** alongside **Git**. It includes:

- A sample dataset tracked by DVC.
- Python scripts (`dataframe.py`, `download_dataset.py`) for data processing and downloading.
- Step-by-step instructions for reproducibility.

## Table of Contents
1. [Requirements](#requirements)
2. [Installation and Setup](#installation-and-setup)
3. [Project Structure](#project-structure)
4. [Using DVC](#using-dvc)
   - [Adding Data](#adding-data)
   - [Updating Data](#updating-data)
   - [Switching Between Versions](#switching-between-versions)
5. [Git Integration](#git-integration)
6. [Reproducing this Project](#reproducing-this-project)
7. [Running the Scripts](#running-the-scripts)
8. [Submitting Your Work (Optional)](#submitting-your-work-optional)
9. [Further Reading](#further-reading)

---

## 1. Requirements

- **Git** (version control for code)
- **Python 3** (for running scripts and installing DVC)
- **DVC** (for data versioning)
- (Optional) A **virtual environment** tool like `venv` or `conda` to manage Python packages.

---

## 2. Installation and Setup

Follow these steps to get started:

1. **Clone the Repository (if applicable):**
   ```bash
   git clone <YOUR_REPOSITORY_URL>
   cd <YOUR_REPOSITORY_FOLDER>
   ```

2. **Set up a Python Environment (Optional but Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or venv\Scripts\activate  # On Windows
   deactivate # Close venv
   ```

3. **Install DVC**  
   ```bash
   pip install dvc
   ```

4. **Initialize Git** (if not already initialized):
   ```bash
   git init
   ```

5. **Initialize DVC:**
   ```bash
   dvc init
      # This creates a .dvc/ folder and updates .gitignore so that large data files aren’t accidentally tracked by Git.
   ```

---

## 3. Project Structure

```
.
├── data/
│   └── enron_emails.csv       # Large dataset tracked by DVC
│   └── enron_emails.csv.dvc   # DVC metafile tracking dataset
│   └── .gitignore             # Git ignore file (DVC updates this automatically)
│   └── README.md              # This readme file to learn how to use DVC
├── data_pipeline/scripts/
│   ├── dataframe.py           # Python script for dataset manipulation
│   └── download_dataset.py    # Python script for downloading data
├── .dvc/                      # DVC internal files (created by dvc init)
├── .gitignore                 # Git ignore file (folder/file don't want to git push)
├── README.md                  # This readme file
└── requirements.txt           # (Optional) For Python dependencies
```

---

## 4. Using DVC

### 4.1 Adding Data

1. **Add the dataset to DVC:**
   ```bash
   # Assume you have a dataset file at data/your_dataset.
   dvc add data/enron_emails.csv
   ```
2. **Commit the `.dvc` file to Git:**
   ```bash
   git add data/enron_emails.csv.dvc .gitignore
   git commit -m "Track dataset with DVC"
   ```
   This command:
   - Calculates a hash of your dataset.
   - Creates a .dvc file (e.g., data/enron_emails.csv.dvc) with metadata about the file.
   - Updates .gitignore so Git ignores the actual CSV but tracks the .dvc file.

### 4.2 Updating Data

1. Overwrite or update `data/enron_emails.csv`. 
      - If your dataset changes (e.g., new rows, new version):
2. Run:
   ```bash
   dvc add data/enron_emails.csv
   ```
3. Commit the changes:
   ```bash
   git add data/enron_emails.csv.dvc
   git commit -m "Update dataset"
   ```
- Each commit in Git now corresponds to a different dataset version in DVC.

### 4.3 Switching Between Versions

1. Checkout a specific Git commit:
   ```bash
   git checkout <COMMIT_HASH_OR_BRANCH>
   ```
2. Restore dataset version:
   ```bash
   dvc checkout
   ```
- DVC will retrieve or link the dataset version matching that Git commit.

---

## 5. Git Integration

### Files to Track with Git
- **Tracked:** `.py, config` files, `.dvc, dvc.yaml, dvc.lock` files, `.gitignore`
- **Ignored:**
	- Large data files (data/your_dataset).
	- DVC cache (.dvc/cache).
	- Any other large or generated files.


### Basic Git Commands
```bash
# See changes
git status

# Stage changes
git add <file_or_folder>

# Commit changes
git commit -m "Your commit message"

# Push to remote repository
git push origin main
```


---

## 6. Reproducing This Project

1. Clone the repository:
   ```bash
   git clone <YOUR_REPOSITORY_URL>
   cd <YOUR_REPOSITORY_FOLDER>
   ```
2. Install DVC and any Python dependencies:
   ```bash
   pip install dvc
   # pip install -r requirements.txt (if you have a requirements file)
   ```
3. Pull the data (assuming you have set up a DVC remote or have the .dvc/cache locally):
   ```bash
   dvc pull
   ```

---

## 7. Running the Scripts

1. Run `dataframe.py`:
   ```bash
   python src/dataframe.py
   ```
2. Run `download_dataset.py`:
   ```bash
   python src/download_dataset.py
   ```

---

## 8. Further Reading

- [DVC Documentation](https://dvc.org/doc)
- [Official Git Documentation](https://git-scm.com/doc)
- [DVC Remote Storage Options](https://dvc.org/doc/commands-reference/remote)

---

**Congratulations!** You now have a reproducible data versioning workflow using Git + DVC.

