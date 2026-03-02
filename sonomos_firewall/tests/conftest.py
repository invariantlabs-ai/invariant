"""
conftest.py
"""

import os


def pytest_configure(config):
    # Sonomos Firewall runs local-only; set LOCAL_POLICY for compatibility
    os.environ["LOCAL_POLICY"] = "1"
