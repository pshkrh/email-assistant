import os
import tarfile
import urllib.request
import warnings
warnings.filterwarnings('ignore')

DATASET_URL = "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz"
DATA_DIR = "dataset"
ARCHIVE_NAME = "enron_mail_20150507.tar.gz"

# Download the Enron dataset from the given URL.
def download_enron_dataset(url, save_path):
    if not os.path.exists(save_path):
        print("Downloading the Enron dataset...")
        urllib.request.urlretrieve(url, save_path)
        print("Download complete!")
    else:
        print("Dataset archive already exists, skipping download.")

# Extract the Enron dataset.
def extract_enron_dataset(archive_path, extract_to):

    if not os.path.exists(extract_to):
        os.makedirs(extract_to)

    print("Extracting the dataset...")
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=extract_to)
    print(f"Extraction complete! Files are saved in '{extract_to}'")

if __name__ == "__main__":
    # Step 1: Download dataset
    download_enron_dataset(ENRON_URL, ARCHIVE_NAME)

    # Step 2: Extract dataset
    extract_enron_dataset(ARCHIVE_NAME, DATA_DIR)
