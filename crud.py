# crud.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone  # <-- CAMBIO: usamos datetime.now(timezone.utc) para disabled_at y expires_at
import secrets  # <-- CAMBIO

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import update

from config import settings
from security import hash_api_key  # <-- CAMBIO: hashing API keys
import keygen, models, schemas



# -------------------------
# URLs
# -------------------------

def create_db_url(
    db: Session, url: schemas.URLBase, key: str | None = None, *, tenant_id: int | None = None  # <-- CAMBIO
) -> models.URL:
    """
    Crea una URL acortada:
      - key: custom_key o generada de forma única (según settings)
      - secret_key: siempre generada con settings (length + alphabet)
      - expires_at: now + expires_in_days (request) o settings.days_mantain
      - tenant_id: ownership (si viene autenticado)
    """
    try:
        if key is None:
            key = keygen.create_unique_url_key(db)

        secret_key = keygen.create_secret_key()

        expires_days = (
            int(url.expires_in_days)
            if getattr(url, "expires_in_days", None) is not None
            else int(settings.days_mantain)
        )  # <-- CAMBIO

        db_url = models.URL(
            target_url=str(url.target_url),
            key=key,
            secret_key=secret_key,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
            tenant_id=tenant_id,  # <-- CAMBIO
        )

        db.add(db_url)
        db.commit()
        db.refresh(db_url)
        return db_url

    except IntegrityError:
        db.rollback()
        raise


def get_db_url_by_key(db: Session, url_key: str) -> models.URL | None:
    return (
        db.query(models.URL)
        .filter(models.URL.key == url_key, models.URL.is_active == True)
        .first()
    )


def get_db_url_by_key_any(db: Session, url_key: str) -> models.URL | None:  # <-- CAMBIO
    return db.query(models.URL).filter(models.URL.key == url_key).first()


def get_db_url_by_secret_key(
    db: Session, secret_key: str, include_inactive: bool = False
) -> models.URL | None:
    q = db.query(models.URL).filter(models.URL.secret_key == secret_key)
    if not include_inactive:
        q = q.filter(models.URL.is_active == True)
    return q.first()


def get_db_url_by_key_for_tenant(db: Session, url_key: str, tenant_id: int) -> models.URL | None:  # <-- CAMBIO
    return (
        db.query(models.URL)
        .filter(models.URL.key == url_key, models.URL.tenant_id == tenant_id)
        .first()
    )


def list_urls_for_tenant(db: Session, tenant_id: int, limit: int = 100, offset: int = 0):  # <-- CAMBIO
    return (
        db.query(models.URL)
        .filter(models.URL.tenant_id == tenant_id)
        .order_by(models.URL.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_db_clicks(db: Session, db_url: models.URL) -> None:
    """Contador atómico de clicks."""
    db.execute(
        update(models.URL)
        .where(models.URL.id == db_url.id)
        .values(clicks=models.URL.clicks + 1)
    )
    db.commit()


def deactivate_db_url_by_secret_key(db: Session, secret_key: str) -> models.URL | None:
    db_url = get_db_url_by_secret_key(db, secret_key, include_inactive=True)
    if not db_url:
        return None

    db_url.is_active = False
    db_url.disabled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_url)
    return db_url


def activate_db_url_by_secret_key(db: Session, secret_key: str) -> models.URL | None:
    db_url = get_db_url_by_secret_key(db, secret_key, include_inactive=True)
    if not db_url:
        return None

    db_url.is_active = True
    db_url.disabled_at = None
    db.commit()
    db.refresh(db_url)
    return db_url


def deactivate_db_url_for_tenant(db: Session, url_key: str, tenant_id: int) -> models.URL | None:  # <-- CAMBIO
    db_url = get_db_url_by_key_for_tenant(db, url_key, tenant_id)
    if not db_url:
        return None
    db_url.is_active = False
    db_url.disabled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_url)
    return db_url


def activate_db_url_for_tenant(db: Session, url_key: str, tenant_id: int) -> models.URL | None:  # <-- CAMBIO
    db_url = get_db_url_by_key_for_tenant(db, url_key, tenant_id)
    if not db_url:
        return None
    db_url.is_active = True
    db_url.disabled_at = None
    db.commit()
    db.refresh(db_url)
    return db_url


def update_expiry_by_secret_key(
    db: Session, secret_key: str, expires_in_days: int | None
) -> models.URL | None:
    db_url = (
        db.query(models.URL)
        .filter(models.URL.secret_key == secret_key)
        .first()
    )
    
    if not db_url:
        return None

    if expires_in_days is None:
        db_url.expires_at = None
    else:
        now = datetime.now(timezone.utc)
        db_url.expires_at = now + timedelta(days=expires_in_days)

    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return db_url


def update_expiry_for_tenant(db: Session, url_key: str, tenant_id: int, expires_in_days: int | None) -> models.URL | None:  # <-- CAMBIO
    db_url = get_db_url_by_key_for_tenant(db, url_key, tenant_id)
    if not db_url:
        return None
    if expires_in_days is None:
        db_url.expires_at = None
    else:
        db_url.expires_at = datetime.now(timezone.utc) + timedelta(days=int(expires_in_days))
    db.commit()
    db.refresh(db_url)
    return db_url


# -------------------------
# Tenants + API keys
# -------------------------

def create_tenant(db: Session, name: str) -> models.Tenant:  # <-- CAMBIO
    t = models.Tenant(name=name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def get_tenant_by_name(db: Session, name: str) -> models.Tenant | None:  # <-- CAMBIO
    return db.query(models.Tenant).filter(models.Tenant.name == name).first()


def get_tenant_by_id(db: Session, tenant_id: int) -> models.Tenant | None:  # <-- CAMBIO
    return db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()


def create_api_key(db: Session, tenant_id: int, name: str = "default") -> tuple[str, models.APIKey]:  # <-- CAMBIO
    raw = secrets.token_urlsafe(32)  # <-- CAMBIO: API key en claro (solo se devuelve al crear)
    key_hash = hash_api_key(raw)  # <-- CAMBIO
    ak = models.APIKey(tenant_id=tenant_id, name=name, key_hash=key_hash, is_active=True)
    db.add(ak)
    db.commit()
    db.refresh(ak)
    return raw, ak


def get_api_key_by_hash(db: Session, key_hash: str) -> models.APIKey | None:  # <-- CAMBIO
    return (
        db.query(models.APIKey)
        .filter(models.APIKey.key_hash == key_hash, models.APIKey.is_active == True)
        .first()
    )


def touch_api_key_last_used(db: Session, api_key_id: int) -> None:  # <-- CAMBIO
    db.execute(
        update(models.APIKey)
        .where(models.APIKey.id == api_key_id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    db.commit()


def list_api_keys_for_tenant(db: Session, tenant_id: int) -> list[models.APIKey]:  # <-- CAMBIO
    return (
        db.query(models.APIKey)
        .filter(models.APIKey.tenant_id == tenant_id)
        .order_by(models.APIKey.created_at.desc())
        .all()
    )


def disable_api_key(db: Session, tenant_id: int, api_key_id: int) -> models.APIKey | None:  # <-- CAMBIO
    ak = (
        db.query(models.APIKey)
        .filter(models.APIKey.id == api_key_id, models.APIKey.tenant_id == tenant_id)
        .first()
    )
    if not ak:
        return None
    ak.is_active = False
    db.commit()
    db.refresh(ak)
    return ak
