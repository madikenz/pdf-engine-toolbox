"""Test the cache service."""

import json
import os
import tempfile
import time

from app.services import cache_service
from app.config import settings


def test_cache_put_and_get_bytes():
    """Should store and retrieve binary data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = settings.cache_dir
        settings.cache_dir = tmpdir
        settings.cache_enabled = True
        try:
            data = b"fake PDF content for cache test"
            src_hash = cache_service.content_hash(data)

            # Cache miss initially
            assert cache_service.get_cached(src_hash, "test_op") is None

            # Store
            cache_service.put_cached(src_hash, "test_op", data)

            # Cache hit
            result = cache_service.get_cached(src_hash, "test_op")
            assert result == data
        finally:
            settings.cache_dir = original_dir


def test_cache_put_and_get_json():
    """Should store and retrieve JSON (dict) data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = settings.cache_dir
        settings.cache_dir = tmpdir
        settings.cache_enabled = True
        try:
            data = {"suggested_label": "W-2", "confidence": 0.9}
            src_hash = cache_service.content_hash(b"some pdf content")

            cache_service.put_cached(src_hash, "classify", data)

            result = cache_service.get_cached(src_hash, "classify")
            assert isinstance(result, dict)
            assert result["suggested_label"] == "W-2"
            assert result["confidence"] == 0.9
        finally:
            settings.cache_dir = original_dir


def test_cache_params_differentiation():
    """Different params should produce different cache entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = settings.cache_dir
        settings.cache_dir = tmpdir
        settings.cache_enabled = True
        try:
            src_hash = cache_service.content_hash(b"test content")

            data_a = b"result with width=200"
            data_b = b"result with width=400"

            cache_service.put_cached(src_hash, "thumbnails", data_a, {"width": 200})
            cache_service.put_cached(src_hash, "thumbnails", data_b, {"width": 400})

            result_a = cache_service.get_cached(src_hash, "thumbnails", {"width": 200})
            result_b = cache_service.get_cached(src_hash, "thumbnails", {"width": 400})

            assert result_a == data_a
            assert result_b == data_b
        finally:
            settings.cache_dir = original_dir


def test_cache_ttl_expiry():
    """Expired entries should return None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = settings.cache_dir
        settings.cache_dir = tmpdir
        settings.cache_enabled = True
        try:
            src_hash = cache_service.content_hash(b"expiring data")

            # Store with a very short TTL
            cache_service.put_cached(src_hash, "short_lived", b"data", ttl=1)

            # Should be cached immediately
            assert cache_service.get_cached(src_hash, "short_lived") == b"data"

            # Wait for expiry
            time.sleep(1.5)

            # Should be expired
            assert cache_service.get_cached(src_hash, "short_lived") is None
        finally:
            settings.cache_dir = original_dir


def test_cache_disabled():
    """When cache is disabled, should always return None."""
    original_enabled = settings.cache_enabled
    settings.cache_enabled = False
    try:
        src_hash = cache_service.content_hash(b"test data")
        cache_service.put_cached(src_hash, "test_op", b"data")
        assert cache_service.get_cached(src_hash, "test_op") is None
    finally:
        settings.cache_enabled = original_enabled


def test_cache_list_data():
    """Should store and retrieve list data (e.g., blank page detection results)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = settings.cache_dir
        settings.cache_dir = tmpdir
        settings.cache_enabled = True
        try:
            data = [
                {"page_index": 0, "is_blank": False, "ink_ratio": 0.15},
                {"page_index": 1, "is_blank": True, "ink_ratio": 0.002},
            ]
            src_hash = cache_service.content_hash(b"pdf with blanks")

            cache_service.put_cached(src_hash, "detect_blank", data)

            result = cache_service.get_cached(src_hash, "detect_blank")
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[1]["is_blank"] is True
        finally:
            settings.cache_dir = original_dir


def test_content_hash_deterministic():
    """Same content should always produce the same hash."""
    data = b"deterministic content for hashing"
    h1 = cache_service.content_hash(data)
    h2 = cache_service.content_hash(data)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_content_hash_different():
    """Different content should produce different hashes."""
    h1 = cache_service.content_hash(b"content A")
    h2 = cache_service.content_hash(b"content B")
    assert h1 != h2
