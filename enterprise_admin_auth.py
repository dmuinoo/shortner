# enterprise_admin_auth.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt  # pyjwt

# Lee config sin obligarte a refactor
def _get_admin_jwt_secret() -> str:
    # 1) ENV
    if os.getenv("ADMIN_JWT_SECRET"):
        return os.getenv("ADMIN_JWT_SECRET", "")
    # 2) settings/config
    try:
        import settings  # type: ignore
        if hasattr(settings, "ADMIN_JWT_SECRET"):
            return getattr(settings, "ADMIN_JWT_SECRET")
        if hasattr(settings, "settings") and hasattr(settings.settings, "admin_jwt_secret"):
            return getattr(settings.settings, "admin_jwt_secret")
    except Exception:
        pass
    try:
        import config  # type: ignore
        if hasattr(config, "settings") and hasattr(config.settings, "admin_jwt_secret"):
            return getattr(config.settings, "admin_jwt_secret")
    except Exception:
        pass
    return "CHANGE_ME_ADMIN_JWT_SECRET"


def _get_admin_jwt_issuer() -> str:
    return os.getenv("ADMIN_JWT_ISSUER", "shortener-admin")


def _get_admin_ttl_minutes() -> int:
    v = os.getenv("ADMIN_JWT_TTL_MINUTES")
    if v:
        return int(v)
    try:
        import config  # type: ignore
        if hasattr(config, "settings") and hasattr(config.settings, "admin_jwt_ttl_minutes"):
            return int(getattr(config.settings, "admin_jwt_ttl_minutes"))
    except Exception:
        pass
    return 60


def _get_local_admin_user() -> str:
    return os.getenv("LOCAL_ADMIN_USER", "admin")


def _get_local_admin_password() -> str:
    return os.getenv("LOCAL_ADMIN_PASSWORD", "admin")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_admin_token(*, subject: str, source: str = "local") -> str:
    secret = _get_admin_jwt_secret()
    ttl = _get_admin_ttl_minutes()
    payload = {
        "iss": _get_admin_jwt_issuer(),
        "sub": subject,
        "src": source,
        "iat": int(now_utc().timestamp()),
        "exp": int((now_utc() + timedelta(minutes=ttl)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_admin_token(token: str) -> Dict[str, Any]:
    secret = _get_admin_jwt_secret()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=_get_admin_jwt_issuer(),
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


bearer = HTTPBearer(auto_error=False)


class AdminPrincipal:
    def __init__(self, *, subject: str, source: str):
        self.subject = subject
        self.source = source


def admin_login_local(username: str, password: str) -> str:
    """
    Valida contra credenciales locales (ENV). Devuelve JWT.
    """
    if username != _get_local_admin_user() or password != _get_local_admin_password():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    subject = f"local:{username}"
    return create_admin_token(subject=subject, source="local")


def require_admin(request: Request, creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> AdminPrincipal:
    """
    Dependency para proteger endpoints admin.
    """
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin bearer token")

    payload = verify_admin_token(creds.credentials)
    subject = str(payload.get("sub"))
    source = str(payload.get("src", "local"))

    # Contexto útil para audit
    request.state.admin_subject = subject
    request.state.admin_source = source

    return AdminPrincipal(subject=subject, source=source)
