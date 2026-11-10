#!/usr/bin/env python3
"""Supabase JWT Bearer authentication and X-Admin-Key verification dependencies."""

from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt


_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """Verify a Supabase HS256 Bearer JWT and return the user's sub (UUID) and email."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization: Bearer <token> header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET", "").strip()
    if not jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured on the server.",
        )

    token = credentials.credentials.strip()
    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False, "require": ["sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    aud = payload.get("aud")
    valid_aud = (
        aud is None
        or aud == "authenticated"
        or (isinstance(aud, list) and "authenticated" in aud)
    )
    if not valid_aud:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token audience is not authorized.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing user subject (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("email")
    return {
        "sub": sub.strip(),
        "email": email.strip() if isinstance(email, str) and email.strip() else None,
    }


def require_admin_key(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    """Verify the X-Admin-Key header against ADMIN_KEY from environment variables."""
    expected = os.environ.get("ADMIN_KEY", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Database wipe disabled: ADMIN_KEY is not configured on the server.",
        )

    provided = (x_admin_key or "").strip()
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Key header.",
        )
