import time
import hmac
import hashlib
from collections import defaultdict, deque
from fastapi import HTTPException, Request, Depends, status, Security  # <-- CAMBIO
from sqlalchemy.orm import Session  # <-- CAMBIO
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session


from config import settings
from database import get_db  # <-- CAMBIO
import models  # <-- CAMBIO


# Definimos los schemes (Permite crear el boton Authorize)
x_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
x_root_key_scheme = APIKeyHeader(name="X-Root-Key", auto_error=False)


# Sliding window in-memory: {identity: deque[timestamps]}
_requests_log = defaultdict(lambda: deque())


def hash_api_key(raw_api_key: str) -> str:  # <-- CAMBIO
    """
    Hash estable (HMAC-SHA256) para no almacenar la API key en claro.
    """
    mac = hmac.new(
        settings.api_key_hmac_secret.encode("utf-8"),  # <-- CAMBIO
        raw_api_key.encode("utf-8"),
        hashlib.sha256,
    )
    return mac.hexdigest()


def _rate_limit_identity(request: Request) -> str:  # <-- CAMBIO
    # Prefer API key hash (tenant-scoped) si existe; si no, IP
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"api:{hash_api_key(api_key)}"  # <-- CAMBIO
    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


def rate_limit(request: Request) -> None:
    """
    Rate limit basado en variables de entorno:
      - RATE_LIMIT_MAX_REQUESTS
      - RATE_LIMIT_WINDOW_SECONDS

    Aplica por API key si existe, o por IP como fallback.
    """  # <-- CAMBIO: rate limit identity-aware
    ident = _rate_limit_identity(request)  # <-- CAMBIO
    now = time.time()

    window = settings.rate_limit_window_seconds
    limit = settings.rate_limit_max_requests

    q = _requests_log[ident]

    # Drop old timestamps
    while q and (now - q[0]) > window:
        q.popleft()

    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="Too Many Requests")

    q.append(now)


def sign_message(message: str) -> str:
    """
    Firma HMAC (opcional). Usa HMAC_SECRET_KEY desde .env.
    """
    mac = hmac.new(
        settings.hmac_secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    )
    return mac.hexdigest()


def verify_signature(message: str, signature: str) -> bool:
    expected = sign_message(message)
    return hmac.compare_digest(expected, signature)


def require_root_admin(root_key: str = Security(x_root_key_scheme)) -> None:  # <-- CAMBIO
    root = request.headers.get("x-root-key") or request.headers.get("x-admin-key")
    if not settings.root_admin_key:
        raise HTTPException(status_code=500, detail="ROOT_ADMIN_KEY not configured")
    if not root or not hmac.compare_digest(root, settings.root_admin_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_current_tenant(
    api_key: str = Security(x_api_key_scheme),
    db: Session = Depends(get_db),
) -> models.Tenant:  # <-- CAMBIO
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key")

    key_hash = hash_api_key(api_key)
    ak = (
        db.query(models.APIKey)
        .filter(models.APIKey.key_hash == key_hash, models.APIKey.is_active == True)
        .first()
    )
    if not ak:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # audit best-effort
    try:
        from datetime import datetime  # <-- CAMBIO
        ak.last_used_at = datetime.utcnow()  # <-- CAMBIO
        db.commit()
    except Exception:
        db.rollback()

    tenant = db.query(models.Tenant).filter(models.Tenant.id == ak.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found")

    return tenant
