# enterprise_security.py
from __future__ import annotations

import hmac
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Iterable, Optional, Tuple

from fastapi import Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from enterprise_models import ApiKey

# Intentamos leer un secreto desde tu settings/config actual sin forzarte a refactor.
# Ajusta si tu proyecto usa otra ruta/nombre.
def _get_hmac_secret() -> str:
    # 1) settings.py (muy común)
    try:
        import settings  # type: ignore
        if hasattr(settings, "API_KEY_HMAC_SECRET"):
            return getattr(settings, "API_KEY_HMAC_SECRET")
        if hasattr(settings, "settings") and hasattr(settings.settings, "API_KEY_HMAC_SECRET"):
            return getattr(settings.settings, "API_KEY_HMAC_SECRET")
    except Exception:
        pass

    # 2) config.py (también común)
    try:
        import config  # type: ignore
        if hasattr(config, "API_KEY_HMAC_SECRET"):
            return getattr(config, "API_KEY_HMAC_SECRET")
        if hasattr(config, "settings") and hasattr(config.settings, "api_key_hmac_secret"):
            return getattr(config.settings, "api_key_hmac_secret")
    except Exception:
        pass

    # 3) fallback (DEBES CAMBIARLO en prod)
    return "CHANGE_ME_SUPER_SECRET"


def _get_prefix_len() -> int:
    try:
        import settings  # type: ignore
        if hasattr(settings, "API_KEY_PREFIX_LEN"):
            return int(getattr(settings, "API_KEY_PREFIX_LEN"))
        if hasattr(settings, "settings") and hasattr(settings.settings, "API_KEY_PREFIX_LEN"):
            return int(getattr(settings.settings, "API_KEY_PREFIX_LEN"))
    except Exception:
        pass

    try:
        import config  # type: ignore
        if hasattr(config, "settings") and hasattr(config.settings, "api_key_prefix_len"):
            return int(getattr(config.settings, "api_key_prefix_len"))
    except Exception:
        pass

    return 8


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def api_key_hash(raw_key: str) -> str:
    """
    HMAC-SHA256 de la key completa. Guardamos hex digest.
    """
    secret = _get_hmac_secret().encode("utf-8")
    msg = raw_key.encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def generate_api_key() -> Tuple[str, str]:
    """
    Devuelve (raw_key, prefix).
    raw_key: string secreta para entregar al usuario SOLO una vez.
    prefix: primeros N chars, para lookup rápido en BD.
    """
    prefix_len = _get_prefix_len()
    raw = secrets.token_urlsafe(32)  # suficientemente larga
    prefix = raw[:prefix_len]
    return raw, prefix


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def verify_key_row(raw_key: str, row: ApiKey) -> bool:
    """
    Verifica la key contra el hash guardado.
    """
    computed = api_key_hash(raw_key)
    return constant_time_equals(computed, row.key_hash)


def extract_prefix(raw_key: str) -> str:
    prefix_len = _get_prefix_len()
    if len(raw_key) < prefix_len:
        return raw_key
    return raw_key[:prefix_len]


def require_api_key(
    request: Request,
    db: Session,
    x_api_key: Optional[str] = Header(default=None, convert_underscores=False),
) -> ApiKey:
    """
    Dependency FastAPI. Valida X-API-Key y devuelve el objeto ApiKey.
    Uso:
        @router.post("/v1/shorten")
        def shorten(..., api_key: ApiKey = Depends(lambda: require_api_key(request, db, x_api_key))):
            ...
    (En el siguiente archivo te lo dejo más limpio con Depends + get_db)
    """
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key")

    prefix = extract_prefix(x_api_key)

    # Buscamos por prefix y verificamos hash
    candidates: Iterable[ApiKey] = (
        db.query(ApiKey)
        .filter(ApiKey.prefix == prefix)
        .filter(ApiKey.revoked_at.is_(None))
        .all()
    )

    if not candidates:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    matched: Optional[ApiKey] = None
    for row in candidates:
        if verify_key_row(x_api_key, row):
            matched = row
            break

    if not matched:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Expiración
    if matched.expires_at is not None:
        # Normalizamos: si tu DB guarda naive UTC, lo tratamos como UTC
        exp = matched.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= now_utc():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    # Guardamos contexto útil en request.state (opcional)
    request.state.company_id = matched.company_id
    request.state.api_key_id = matched.id

    return matched
