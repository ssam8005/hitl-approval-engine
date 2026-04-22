"""
api/middleware.py — X-API-Key authentication dependency.

All mutation endpoints require X-API-Key header matching API_SECRET_KEY.
Read endpoints (GET /approvals) are also protected to prevent lead data exposure.
"""
from fastapi import Header, HTTPException, status


def require_auth(x_api_key: str = Header(...)):
    """FastAPI dependency — validates X-API-Key header."""
    from config import get_settings
    cfg = get_settings()
    if x_api_key != cfg.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
