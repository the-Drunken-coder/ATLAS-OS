"""Utility functions for the framework."""

import os


def is_test_env() -> bool:
    """
    Return True when running under automated tests.

    This helper detects test environments via environment variables:
    - PYTEST_CURRENT_TEST: Set by pytest during test execution
    - ATLAS_TEST_MODE: Can be set manually for test scenarios

    Returns:
        bool: True if running in a test environment, False otherwise
    """
    return bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("ATLAS_TEST_MODE"))
