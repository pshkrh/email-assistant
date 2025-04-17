"""
Prompt Loading Module

This module provides functionality to load prompt templates from YAML configuration files.
These prompt templates are used for generating email summaries, action items, and draft replies.
"""

import yaml


def load_prompts(filename):
    """
    Load prompt templates from a YAML file.

    Args:
        filename (str): Path to the YAML file containing prompt templates

    Returns:
        dict: Dictionary of prompt templates organized by task

    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        yaml.YAMLError: If the YAML file has invalid syntax
    """
    # Open and parse the YAML file
    with open(filename, "r") as file:
        return yaml.safe_load(file)
