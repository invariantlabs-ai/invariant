"""Tests for the CacheManager class."""

import hashlib
import json
import tempfile
import time

import pytest

from invariant.testing.cache import CacheManager


@pytest.fixture(name="cache_manager")
def fiture_cache_manager():
    """Fixture to create a CacheManager instance with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield CacheManager(cache_dir=temp_dir, expiry=3600)


@pytest.fixture(name="cache_manager_with_small_ttl")
def fiture_cache_manager_with_small_ttl():
    """Fixture to create a CacheManager instance with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield CacheManager(cache_dir=temp_dir, expiry=1)


def test_cache_manager_set_and_get(cache_manager: CacheManager):
    """Test setting and getting cache values."""
    key = "test_key"
    value = {"data": "test_value"}
    cache_manager.set(key, value)
    cached_value = cache_manager.get(key)
    assert cached_value == value


def test_cache_manager_get_default(cache_manager: CacheManager):
    """Test getting a default value when the key is not in the cache."""
    key = "non_existent_key"
    default_value = {"default": "value"}
    cached_value = cache_manager.get(key, default=default_value)
    assert cached_value == default_value


def test_cache_manager_generate_cache_key(cache_manager: CacheManager):
    """Test generating a consistent cache key based on request data."""
    data = {"param1": "value1", "param2": 2}
    cache_key = cache_manager.get_cache_key(data)
    expected_key = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    assert cache_key == expected_key


def test_cache_manager_generate_cache_key_with_non_serializable_data(
    cache_manager: CacheManager,
):
    """Test generating a cache key with non-serializable data."""

    class CustomClass:
        """Custom class for testing."""

        pass

    data = {
        "key_list": ["hello", 1, 2.0, True],
        "key_dict": {"param1": "value1", "param2": CustomClass},
        "key_class": CustomClass,
        "key_bool": True,
        "key_int": 1,
        "key_float": 2.0,
        "key_str": "hello",
    }

    cache_key = cache_manager.get_cache_key(data)

    expected_data = {
        "key_bool": True,
        "key_class": "test_cache_manager.CustomClass",
        "key_dict": {
            "param1": "value1",
            "param2": "test_cache_manager.CustomClass",
        },
        "key_float": 2.0,
        "key_int": 1,
        "key_list": ["hello", 1, 2.0, True],
        "key_str": "hello",
    }

    expected_key = hashlib.sha256(json.dumps(expected_data, sort_keys=True).encode()).hexdigest()

    assert cache_key == expected_key


def test_cache_manager_expiry(cache_manager: CacheManager):
    """Test that cache values expire after the specified time."""
    key = "test_key"
    value = {"data": "test_value"}
    cache_manager.set(key, value)
    cached_value = cache_manager.get(key)
    assert cached_value == value

    # Simulate expiry by manually deleting the cache entry
    cache_manager.delete(key)
    cached_value = cache_manager.get(key)
    assert cached_value is None


def test_cache_manager_expiry_with_small_ttl(
    cache_manager_with_small_ttl: CacheManager,
):
    """Test that cache values expire after the specified time."""
    key = "test_key"
    value = {"data": "test_value"}
    cache_manager_with_small_ttl.set(key, value)
    assert cache_manager_with_small_ttl.get(key) == value

    time.sleep(1)

    cached_value = cache_manager_with_small_ttl.get(key)
    assert cached_value is None
