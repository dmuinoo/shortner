# short/crud.py

from datetime import datetime, timedelta

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
            key = keygen.create_unique_random_key(db)

        secret_key = keygen.create_secret_key()

        db_url = models.URL(
            target_url=str(url.target_url),
            key=key,
            secret_key=secret_key,
            expires_at=datetime.utcnow() + timedelta(days=settings.days_mantain),
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


def get_db_url_by_secret_key(db: Session, secret_key: str) -> models.URL | None:
    return (
        db.query(models.URL)
        .filter(models.URL.secret_key == secret_key, models.URL.is_active == True)
        .first()
    )


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
    db_url = get_db_url_by_secret_key(db, secret_key)
    if not db_url:
        return None

    db_url.is_active = False
    db.commit()
    db.refresh(db_url)
    return db_url
