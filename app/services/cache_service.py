"""File-hash based cache for expensive PDF operations.

Caches results of CPU-intensive operations (OCR, thumbnails, render,
classify, detect-blank, office conversion) keyed by SHA-256 of the
source content + operation parameters. Results are stored on disk.

This avoids re-processing the same document when the same operation
is requested multiple times (e.g., regenerating thumbnails after
navigating away and back).
"""

import hashlib
import json
import os
import time
from typing import Any

import structlog

from app.config import settings

log = structlog.get_logger()


def _ensure_cache_dir() -> str:
    """Create cache directory if it doesn't exist."""
    os.makedirs(settings.cache_dir, exist_ok=True)
    return settings.cache_dir


def _cache_key(content_hash: str, operation: str, params: dict | None = None) -> str:
    """Build a deterministic cache key from content hash + operation + params."""
    key_parts = f"{content_hash}:{operation}"
    if params:
        # Sort keys for deterministic ordering
        key_parts += ":" + json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(key_parts.encode()).hexdigest()


def content_hash(data: bytes) -> str:
    """Compute SHA-256 hash of raw content bytes."""
    return hashlib.sha256(data).hexdigest()


def get_cached(
    source_hash: str,
    operation: str,
    params: dict | None = None,
) -> bytes | dict | None:
    """Look up a cached result.

    Returns:
        Cached bytes (for binary results) or dict (for JSON results),
        or None if not cached / expired / cache disabled.
    """
    if not settings.cache_enabled:
        return None

    cache_dir = _ensure_cache_dir()
    key = _cache_key(source_hash, operation, params)
    data_path = os.path.join(cache_dir, key + ".dat")
    meta_path = os.path.join(cache_dir, key + ".meta")

    if not os.path.exists(meta_path) or not os.path.exists(data_path):
        return None

    # Check TTL
    try:
        with open(meta_path, "r") as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    created_at = meta.get("created_at", 0)
    ttl = meta.get("ttl", settings.cache_ttl_seconds)
    if time.time() - created_at > ttl:
        # Expired - clean up
        _remove_entry(data_path, meta_path)
        return None

    # Read cached data
    try:
        with open(data_path, "rb") as f:
            raw = f.read()
    except OSError:
        return None

    result_type = meta.get("type", "bytes")
    if result_type == "json":
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    log.debug("cache_hit", operation=operation, key=key[:12])
    return raw


def put_cached(
    source_hash: str,
    operation: str,
    result: bytes | dict,
    params: dict | None = None,
    ttl: int | None = None,
) -> None:
    """Store a result in the cache.

    Args:
        source_hash: SHA-256 of source content
        operation: Operation name (e.g. "thumbnails", "ocr", "classify")
        result: Bytes (binary) or dict (JSON-serializable)
        params: Operation parameters for cache key
        ttl: Override TTL in seconds (defaults to config)
    """
    if not settings.cache_enabled:
        return

    cache_dir = _ensure_cache_dir()
    key = _cache_key(source_hash, operation, params)
    data_path = os.path.join(cache_dir, key + ".dat")
    meta_path = os.path.join(cache_dir, key + ".meta")

    result_type = "bytes"
    if isinstance(result, dict):
        raw = json.dumps(result).encode()
        result_type = "json"
    elif isinstance(result, list):
        raw = json.dumps(result).encode()
        result_type = "json"
    else:
        raw = result

    meta = {
        "created_at": time.time(),
        "ttl": ttl or settings.cache_ttl_seconds,
        "type": result_type,
        "operation": operation,
        "size": len(raw),
    }

    try:
        with open(data_path, "wb") as f:
            f.write(raw)
        with open(meta_path, "w") as f:
            json.dump(meta, f)
        log.debug("cache_put", operation=operation, key=key[:12], size=len(raw))
    except OSError as e:
        log.warning("cache_write_failed", error=str(e))

    # Prune if over size limit
    _prune_if_needed(cache_dir)


def _remove_entry(data_path: str, meta_path: str) -> None:
    """Remove a cache entry (data + meta files)."""
    for path in (data_path, meta_path):
        try:
            os.remove(path)
        except OSError:
            pass


def _prune_if_needed(cache_dir: str) -> None:
    """Remove oldest entries if total cache size exceeds limit."""
    max_bytes = settings.cache_max_size_mb * 1024 * 1024

    try:
        entries = []
        total_size = 0
        for fname in os.listdir(cache_dir):
            if not fname.endswith(".dat"):
                continue
            path = os.path.join(cache_dir, fname)
            stat = os.stat(path)
            entries.append((path, stat.st_mtime, stat.st_size))
            total_size += stat.st_size

        if total_size <= max_bytes:
            return

        # Sort by modification time (oldest first)
        entries.sort(key=lambda e: e[1])

        for path, _, size in entries:
            if total_size <= max_bytes:
                break
            meta_path = path.replace(".dat", ".meta")
            _remove_entry(path, meta_path)
            total_size -= size
            log.debug("cache_pruned", path=os.path.basename(path))
    except OSError:
        pass
