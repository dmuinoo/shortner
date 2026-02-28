# config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

def _get_str(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v != "" else default


def _get_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return default if v is None or v.strip() == "" else int(v)


def _get_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _require(name: str) -> str:
    v = _get_str(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


@dataclass(frozen=True)
class Settings:
    # No secretos (defaults OK)
    url_key_length: int = _get_int("URL_KEY_LENGTH", 8)
    url_key_alphabet: str = _get_str("URL_KEY_ALPHABET", "ABCDEFGHJKLMNPQRSTUVWXYZ23456789")  # no confusos
    secret_key_length: int = _get_int("SECRET_KEY_LENGTH", 16)
    secret_key_alphabet: str = _get_str("SECRET_KEY_ALPHABET", "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    custom_key_min_len: int = _get_int("CUSTOM_KEY_MIN_LEN", 3)
    custom_key_max_len: int = _get_int("CUSTOM_KEY_MAX_LEN", 32)
    custom_key_alphabet: str = _get_str("CUSTOM_KEY_ALPHABET", "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    rate_limit_max_requests: int = _get_int("RATE_LIMIT_MAX_REQUESTS", 100)
    rate_limit_window_seconds: int = _get_int("RATE_LIMIT_WINDOW_SECONDS", 60)

    days_maintain: int = _get_int("DAYS_MAINTAIN", 180)
    base_url: str = _get_str("BASE_URL", "http://127.0.0.1:8000")
    db_url: str = _get_str("DB_URL", "sqlite:///./shortener.db") or "sqlite:///./shortener.db"
    max_target_url_length: int = _get_int("MAX_TARGET_URL_LENGTH", 2048)
    deny_private_nets: bool = _get_bool("DENY_PRIVATE_NETS", True)
    resolve_dns: bool = _get_bool("RESOLVE_DNS", True)
    validate_target_on_redirect: bool = _get_bool("VALIDATE_TARGET_ON_REDIRECT", True)

    # Secretos (NO defaults en prod; en dev puedes ponerlos en .env)
    # Si quieres permitir arrancar en dev sin .env, pon default "dev-..." pero NO en prod.
    hmac_secret_key: str = _require("HMAC_SECRET_KEY")
    api_key_hmac_secret: str = _require("API_KEY_HMAC_SECRET")

    # Bootstrap / admin
    root_admin_key: str | None = _get_str("ROOT_ADMIN_KEY", None)
    superuser_username: str = _get_str("SUPERUSER_USERNAME", "admin")
    superuser_password_hash: str | None = _get_str("SUPERUSER_PASSWORD_HASH", None)

    # JWT admin (si lo estás usando)
    admin_jwt_secret: str = _get_str("ADMIN_JWT_SECRET", "")  # si lo exiges: usa _require
    admin_jwt_ttl_minutes: int = _get_int("ADMIN_JWT_TTL_MINUTES", 60)


settings = Settings()

