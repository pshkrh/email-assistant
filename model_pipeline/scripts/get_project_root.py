"""
Project Root Module

This module provides a function to determine the root directory of the project.
This is useful for constructing absolute paths to project resources consistently.
"""

import os


def project_root():
    """
    Get the absolute path to the project root directory.

    This function calculates the project root by navigating up from the current
    file's directory. Specifically, it goes up two levels from the current file:
    - First level up: From this file's directory to its parent directory
    - Second level up: From that parent to the project root

    Returns:
        str: Absolute path to the project root directory
    """
    # Get the absolute path to the directory containing this file
    current_file_dir = os.path.dirname(__file__)

    # Navigate up two directory levels to get to the project root
    root_dir = os.path.abspath(os.path.join(current_file_dir, "..", ".."))

    return root_dir
