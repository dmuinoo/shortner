# Shortener/config.py

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env_name: str = "local"
    base_url: str = "http://127.0.0.1:8000"
    db_url: str = "sqlite:///./shortener.db"

    # Keys
    url_key_length: int = 6
    url_key_alphabet: str = (
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    secret_key_length: int = 16
    secret_key_alphabet: str = (
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    custom_key_min_len: int = 3
    custom_key_max_len: int = 32
    custom_key_alphabet: str = (
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    # Rate limit
    rate_limit_max_requests: int = 100
    rate_limit_window_seconds: int = 60

    # HMAC (si aplica)
    hmac_secret_key: str = "super-secret-key-for-hmac"

    days_mantain: int = 180

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    print(f"Loading settings for: {settings.env_name}")
    return settings
