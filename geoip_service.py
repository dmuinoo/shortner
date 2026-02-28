# geoip_service.py  (NUEVO)

from __future__ import annotations

import time
import ipaddress
from functools import lru_cache
from typing import Optional

from config import get_settings

settings = get_settings()

try:
    import geoip2.database  # type: ignore
except Exception:
    geoip2 = None  # <-- CAMBIO: fallback si no está instalado


@lru_cache(maxsize=1)
def _get_reader():
    if not settings.geoip_enabled:
        return None
    if geoip2 is None:
        return None
    try:
        return geoip2.database.Reader(settings.geoip_mmdb_path)
    except Exception:
        return None


# cache simple: ip -> (ts, country_code)
_geo_cache: dict[str, tuple[float, Optional[str]]] = {}


def country_code_for_ip(ip: str) -> Optional[str]:
    """
    Devuelve country ISO code (p.ej. "ES") o None.
    Cache TTL para no penalizar rendimiento.
    """
    if not settings.geoip_enabled:
        return None

    try:
        ipaddress.ip_address(ip)
    except Exception:
        return None

    now = time.time()
    ttl = max(1, int(settings.geoip_cache_ttl_seconds))

    cached = _geo_cache.get(ip)
    if cached and (now - cached[0]) < ttl:
        return cached[1]

    reader = _get_reader()
    if reader is None:
        _geo_cache[ip] = (now, None)
        return None

    try:
        resp = reader.country(ip)
        code = resp.country.iso_code
    except Exception:
        code = None

    _geo_cache[ip] = (now, code)
    return code
