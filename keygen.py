import secrets
from sqlalchemy.orm import Session

from config import get_settings
import crud

settings = get_settings()


def create_random_key(length: int, alphabet: str) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_url_key() -> str:
    return create_random_key(settings.url_key_length, settings.url_key_alphabet)


def create_secret_key() -> str:
    return create_random_key(settings.secret_key_length, settings.secret_key_alphabet)


def create_unique_url_key(db: Session) -> str:
    key = create_url_key()
    while crud.get_db_url_by_key(db, key):
        key = create_url_key()
    return key
