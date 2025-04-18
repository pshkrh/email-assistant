"""
Utility module to get the root directory of the project.

This is useful for constructing absolute paths throughout the codebase.
"""

import os


def project_root():
    """
    Returns the absolute path to the project's root directory.

    This is calculated as two levels up from the location of this script.

    Returns:
        str: Absolute path to the root of the project.
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
