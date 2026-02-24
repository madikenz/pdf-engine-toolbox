"""HMAC-SHA256 request authentication."""

import hashlib
import hmac
import time

from fastapi import Request

from app.config import settings
from app.utils.errors import AuthenticationError


async def verify_hmac(request: Request) -> None:
    """Verify HMAC-SHA256 signature on incoming request.

    Expected headers:
        X-Timestamp: milliseconds since epoch
        X-Signature: hex(HMAC-SHA256(secret, timestamp:method:path:body_hash))
    """
    timestamp = request.headers.get("X-Timestamp")
    signature = request.headers.get("X-Signature")

    if not timestamp or not signature:
        raise AuthenticationError("Missing X-Timestamp or X-Signature headers")

    # Check timestamp freshness
    try:
        ts = int(timestamp)
    except ValueError:
        raise AuthenticationError("Invalid timestamp format")

    now_ms = int(time.time() * 1000)
    if abs(now_ms - ts) > settings.max_timestamp_drift_ms:
        raise AuthenticationError("Request timestamp expired")

    # Read body and compute hash
    body = await request.body()
    body_hash = hashlib.sha256(body).hexdigest()

    # Build the message string
    message = f"{timestamp}:{request.method}:{request.url.path}:{body_hash}"

    # Compute expected signature
    expected = hmac.new(
        settings.pdf_engine_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise AuthenticationError("Invalid signature")
