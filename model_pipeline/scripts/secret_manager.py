"""
Secret Manager Module

This module provides functions to access and retrieve secrets from Google Cloud Secret Manager.
It supports retrieving API keys, credentials, and other sensitive information securely.
"""

import json
import os
import logging

from google.cloud import secretmanager

# Configure logger
logger = logging.getLogger(__name__)


def access_secret(project_id, secret_id, version_id="latest"):
    """
    Access the secret from Google Secret Manager.

    Args:
        project_id (str): Your Google Cloud project ID
        secret_id (str): Your secret ID
        version_id (str): The version of the secret (default: "latest")

    Returns:
        str: The secret payload as a string

    Raises:
        Exception: If secret access fails
    """
    try:
        # Initialize Secret Manager client
        client = secretmanager.SecretManagerServiceClient()

        # Build the resource name
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

        # Access the secret version
        response = client.access_secret_version(request={"name": name})

        # Log success (without revealing the secret)
        logger.info(f"Successfully accessed secret {secret_id}")

        # Return decoded payload
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        # Log error and re-raise
        logger.error(f"Error accessing secret {secret_id}: {e}")
        raise


def get_credentials_from_secret(project_id, secret_id, save_to_file=None):
    """
    Gets credentials JSON from Secret Manager and optionally saves to a file.

    Args:
        project_id (str): Your Google Cloud project ID
        secret_id (str): Your secret ID
        save_to_file (str, optional): Path to save the credentials

    Returns:
        dict: The credentials as a dictionary

    Raises:
        Exception: If credential retrieval fails
    """
    try:
        logger.info(f"Getting credentials from Secret Manager: {secret_id}")

        # Get the secret as a string
        creds_json = access_secret(project_id, secret_id)

        # Convert to dictionary
        creds_dict = json.loads(creds_json)

        # Optionally save to file (for local development or for libraries that need file paths)
        if save_to_file:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_to_file), exist_ok=True)

            # Write credentials to file
            with open(save_to_file, "w") as f:
                json.dump(creds_dict, f)
            logger.info(f"Credentials saved to file: {save_to_file}")

        return creds_dict
    except Exception as e:
        # Log error and re-raise
        logger.error(f"Error getting credentials from Secret Manager: {e}")
        raise
