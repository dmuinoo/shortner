# crud.py

from datetime import datetime, timedelta  # <-- CAMBIO: usamos datetime.utcnow() para disabled_at y expires_at

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import update

from config import get_settings
import keygen, models, schemas

settings = get_settings()


def create_db_url(
    db: Session, url: schemas.URLBase, key: str | None = None
) -> models.URL:
    """
    Crea una URL acortada:
      - key: custom_key o generada de forma única (según settings)
      - secret_key: siempre generada con settings (length + alphabet)
      - expires_at: now + days_mantain
    """
    try:
        if key is None:
            # Fallback: generate a unique key (normally main passes one)
            key = keygen.create_unique_url_key(db)

        secret_key = keygen.create_secret_key()

        expires_days = (
            int(url.expires_in_days)
            if getattr(url, "expires_in_days", None) is not None
            else int(settings.days_mantain)
        )  # <-- CAMBIO: soporta caducidad por request (expires_in_days) o default de settings

        db_url = models.URL(
            target_url=str(url.target_url),
            key=key,
            secret_key=secret_key,
            expires_at=datetime.utcnow() + timedelta(days=expires_days),  # <-- CAMBIO: caducidad efectiva
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


def get_db_url_by_secret_key(
    db: Session, secret_key: str, include_inactive: bool = False
) -> models.URL | None:
    q = db.query(models.URL).filter(models.URL.secret_key == secret_key)
    if not include_inactive:
        q = q.filter(models.URL.is_active == True)
    return q.first()  # <-- CAMBIO: soporte include_inactive para administración


def update_db_clicks(db: Session, db_url: models.URL) -> None:
    """
    Contador atómico de clicks.
    """
    db.execute(
        update(models.URL)
        .where(models.URL.id == db_url.id)
        .values(clicks=models.URL.clicks + 1)
    )
    db.commit()


def deactivate_db_url_by_secret_key(db: Session, secret_key: str) -> models.URL | None:
    db_url = get_db_url_by_secret_key(db, secret_key, include_inactive=True)  # <-- CAMBIO: admin puede tocar inactivas
    if not db_url:
        return None

    db_url.is_active = False
    db_url.disabled_at = datetime.utcnow()  # <-- CAMBIO: marca timestamp de desactivación
    db.commit()
    db.refresh(db_url)
    return db_url


def activate_db_url_by_secret_key(db: Session, secret_key: str) -> models.URL | None:
    db_url = get_db_url_by_secret_key(db, secret_key, include_inactive=True)  # <-- CAMBIO
    if not db_url:
        return None

    db_url.is_active = True
    db_url.disabled_at = None  # <-- CAMBIO: limpiar marca al reactivar
    db.commit()
    db.refresh(db_url)
    return db_url


def update_expiry_by_secret_key(
    db: Session, secret_key: str, expires_in_days: int | None
) -> models.URL | None:
    db_url = get_db_url_by_secret_key(db, secret_key, include_inactive=True)  # <-- CAMBIO
    if not db_url:
        return None

    if expires_in_days is None:
        db_url.expires_at = None  # <-- CAMBIO: permitir “sin caducidad”
    else:
        db_url.expires_at = datetime.utcnow() + timedelta(days=int(expires_in_days))  # <-- CAMBIO: set explícito

    db.commit()
    db.refresh(db_url)
    return db_url
