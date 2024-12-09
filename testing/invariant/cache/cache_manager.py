"""Cache Manager"""

import hashlib
import json
from typing import Any

import diskcache


class CacheManager:
    """Cache Manager class to store and retrieve responses from disk."""

    def __init__(self, cache_dir: str, expiry: int = 3600):
        self.cache = diskcache.Cache(cache_dir)
        self.expiry = expiry

    @staticmethod
    def __serialize(value):
        """Recursively serialize the value to make it JSON serializable."""
        if isinstance(value, (str, int, float)):  # Base case: primitive types
            return value
        if isinstance(value, list):  # Recursively serialize lists
            return [CacheManager.__serialize(item) for item in value]
        if isinstance(value, dict):  # Recursively serialize dicts
            return {k: CacheManager.__serialize(v) for k, v in value.items()}
        if isinstance(value, type):  # Handle class types (not instances)
            return f"{value.__module__}.{value.__name__}"
        # Fallback for other types
        return str(value)

    def get_cache_key(self, data: dict) -> str:
        """Generate a consistent cache key based on request data."""

        serializable_data = {k: CacheManager.__serialize(v) for k, v in data.items()}
        request_str = json.dumps(serializable_data, sort_keys=True)
        return hashlib.sha256(request_str.encode()).hexdigest()

    def get(self, key: str, default=None):
        """Retrieve a cached response."""
        return self.cache.get(key, default=default)

    def set(self, key: str, value: Any):
        """Store a response in the cache."""
        self.cache.set(key, value, expire=self.expiry)

    def delete(self, key: str):
        """Delete a cached response."""
        self.cache.pop(key)
