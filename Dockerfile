# FROM python:3.11

# # Set the working directory
# WORKDIR /app

# # Copy the requirements file and install dependencies
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the scripts folder instead of a single file
# COPY scripts /app/scripts/

# # Define the default command (update path to script)
# CMD ["python", "scripts/download_dataset.py"]

FROM apache/airflow:2.10.5

COPY airflow_requirements.txt /opt/airflow/requirements.txt
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt

USER ${AIRFLOW_UID:-50000}
