"""API dependencies."""
from hmac import compare_digest

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    """Require a valid API key for all protected endpoints."""
    settings = get_settings()
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token or not compare_digest(token, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
