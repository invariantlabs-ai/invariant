"""
conftest.py
"""

import os

import pytest


def pytest_configure(config):
    if (
        os.environ.get("INVARIANT_API_ENDPOINT", None) is None
        and os.environ.get("LOCAL_POLICY", "0") != "1"
    ):
        pytest.exit(
            "Please specify an INVARIANT_API_ENDPOINT variable to test either your local setup ('http://localhost:9002') or a deployed version (e.g. 'https://explorer.invariantlabs.ai') of Guardrails."
        )
