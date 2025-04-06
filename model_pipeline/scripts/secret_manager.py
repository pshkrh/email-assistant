from google.cloud import secretmanager
import json
import os
import logging

logger = logging.getLogger(__name__)


def access_secret(project_id, secret_id, version_id="latest"):
    """
    Access the secret from Google Secret Manager

    Args:
        project_id (str): Your Google Cloud project ID
        secret_id (str): Your secret ID
        version_id (str): The version of the secret

    Returns:
        The secret payload as a string
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        logger.info(f"Successfully accessed secret {secret_id}")
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Error accessing secret {secret_id}: {e}")
        raise


def get_credentials_from_secret(project_id, secret_id, save_to_file=None):
    """
    Gets credentials JSON from Secret Manager and optionally saves to a file

    Args:
        project_id (str): Your Google Cloud project ID
        secret_id (str): Your secret ID
        save_to_file (str, optional): Path to save the credentials

    Returns:
        dict: The credentials as a dictionary
    """
    try:
        logger.info(f"Getting credentials from Secret Manager: {secret_id}")
        creds_json = access_secret(project_id, secret_id)
        creds_dict = json.loads(creds_json)

        # Optionally save to file (for local development or for libraries that need file paths)
        if save_to_file:
            os.makedirs(os.path.dirname(save_to_file), exist_ok=True)
            with open(save_to_file, "w") as f:
                json.dump(creds_dict, f)
            logger.info(f"Credentials saved to file: {save_to_file}")

        return creds_dict
    except Exception as e:
        logger.error(f"Error getting credentials from Secret Manager: {e}")
        raise
