"""FastAPI dependency injection."""

from fastapi import Depends, Request

from app.auth.hmac_auth import verify_hmac


async def require_auth(request: Request) -> None:
    """Dependency that enforces HMAC authentication on a route."""
    await verify_hmac(request)
