# config.py

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env_name: str = "local"
    base_url: str = "http://127.0.0.1:8000"
    db_url: str = "sqlite:///./shortener.db"

    url_key_length: int = 6
    url_key_alphabet: str = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    secret_key_length: int = 16
    secret_key_alphabet: str = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    custom_key_min_len: int = 3
    custom_key_max_len: int = 32
    custom_key_alphabet: str = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    rate_limit_max_requests: int = 100
    rate_limit_window_seconds: int = 60

    hmac_secret_key: str = "super-secret-key-for-hmac"
    days_mantain: int = 180

    # Seguridad target_url
    max_target_url_length: int = 2048
    deny_private_nets: bool = True
    resolve_dns: bool = True
    validate_target_on_redirect: bool = True

    # DNS cache mode: "fixed" o "dns"
    dns_cache_mode: str = "fixed"  # <-- CAMBIO
    dns_cache_ttl_seconds: int = 300  # <-- CAMBIO (fixed)
    dns_cache_ttl_min_seconds: int = 30  # <-- CAMBIO (dns TTL clamp)
    dns_cache_ttl_max_seconds: int = 3600  # <-- CAMBIO (dns TTL clamp)

    # Redis opcional
    redis_url: str | None = None  # <-- CAMBIO (ej: "redis://localhost:6379/0")
    dns_cache_use_redis: bool = False  # <-- CAMBIO

    # Políticas listas
    default_app_policy: str = "allow"
    default_target_policy: str = "allow"
    app_allowlist_path: str = "lists/app_allowlist.txt"
    app_denylist_path: str = "lists/app_denylist.txt"
    target_allowlist_path: str = "lists/target_allowlist.txt"
    target_denylist_path: str = "lists/target_denylist.txt"

    # IP real detrás de proxy (del cliente final)
    trust_x_forwarded_for: bool = True  # <-- CAMBIO
    trusted_proxy_cidrs: list[str] = []  # <-- CAMBIO: si se rellena, solo confiamos XFF si el remote está aquí

    # GeoIP
    geoip_enabled: bool = True
    geoip_mmdb_path: str = "GeoLite2-Country.mmdb"
    geoip_cache_ttl_seconds: int = 3600

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    print(f"Loading settings for: {s.env_name}")
    return s
