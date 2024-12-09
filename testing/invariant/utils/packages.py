""" Utility functions for checking if programs and packages are installed. """

import importlib.util
import shutil


def is_program_installed(program_name: str) -> bool:
    """
    Check if a program is installed and available in the system PATH.

    Args:
        program_name (str): The name of the program to check for

    Returns:
        bool: True if the program is installed and accessible, False otherwise
    """
    return shutil.which(program_name) is not None


def is_package_installed(package_name: str) -> bool:
    """
    Check if a Python package is installed.

    Args:
        package_name (str): The name of the package to check for

    Returns:
        bool: True if the package is installed, False otherwise
    """
    return importlib.util.find_spec(package_name) is not None
