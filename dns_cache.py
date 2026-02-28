# dns_cache.py  (NUEVO)

from __future__ import annotations

import json
import socket
import time
import ipaddress
from typing import Optional, Tuple, List

from fastapi import HTTPException

from config import settings


try:
    import dns.resolver  # type: ignore
except Exception:
    dns = None  # dnspython opcional


try:
    import redis  # type: ignore
except Exception:
    redis = None


_redis_client = None


def _get_redis():
    global _redis_client
    if not settings.dns_cache_use_redis or not settings.redis_url:
        return None
    if redis is None:
        return None
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


# cache local: host -> (expires_at_epoch, [ips])
_local: dict[str, tuple[float, list[str]]] = {}


def _clamp_ttl(ttl: int) -> int:
    mn = max(1, int(settings.dns_cache_ttl_min_seconds))
    mx = max(mn, int(settings.dns_cache_ttl_max_seconds))
    return max(mn, min(mx, ttl))


def resolve_host(host_ascii: str) -> Tuple[List[ipaddress._BaseAddress], int]:
    """
    Devuelve (ips, ttl_seconds_efectivo).
    - modo fixed: ttl=settings.dns_cache_ttl_seconds
    - modo dns: usa TTL del registro (requiere dnspython)
    """
    mode = (settings.dns_cache_mode or "fixed").lower()

    if mode == "dns":
        if dns is None:
            # fallback si no hay dnspython
            mode = "fixed"
        else:
            ttl = None
            ips: list[ipaddress._BaseAddress] = []
            r = dns.resolver.Resolver()
            # A
            try:
                ans = r.resolve(host_ascii, "A")
                ttl = ans.rrset.ttl
                for rr in ans:
                    ips.append(ipaddress.ip_address(rr.address))
            except Exception:
                pass
            # AAAA
            try:
                ans6 = r.resolve(host_ascii, "AAAA")
                ttl6 = ans6.rrset.ttl
                ttl = ttl6 if ttl is None else min(ttl, ttl6)
                for rr in ans6:
                    ips.append(ipaddress.ip_address(rr.address))
            except Exception:
                pass

            if not ips:
                raise HTTPException(status_code=400, detail="target_url host does not resolve")

            ttl_eff = _clamp_ttl(int(ttl) if ttl is not None else int(settings.dns_cache_ttl_seconds))
            return ips, ttl_eff

    # fixed mode (socket)
    try:
        infos = socket.getaddrinfo(host_ascii, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="target_url host does not resolve")
    except Exception:
        raise HTTPException(status_code=400, detail="target_url DNS resolution failed")

    ips: list[ipaddress._BaseAddress] = []
    for info in infos:
        ip_str = info[4][0]
        try:
            ips.append(ipaddress.ip_address(ip_str))
        except ValueError:
            continue

    if not ips:
        raise HTTPException(status_code=400, detail="target_url host does not resolve")

    return ips, int(settings.dns_cache_ttl_seconds)


def get_cached(host_ascii: str) -> Optional[List[ipaddress._BaseAddress]]:
    now = time.time()

    r = _get_redis()
    if r is not None:
        key = f"dns:{host_ascii}"
        raw = r.get(key)
        if raw:
            try:
                payload = json.loads(raw)
                expires_at = float(payload["expires_at"])
                if now < expires_at:
                    ips = [ipaddress.ip_address(x) for x in payload["ips"]]
                    return ips
            except Exception:
                pass

    cached = _local.get(host_ascii)
    if cached and now < cached[0]:
        return [ipaddress.ip_address(x) for x in cached[1]]

    return None


def set_cached(host_ascii: str, ips: List[ipaddress._BaseAddress], ttl: int) -> None:
    expires_at = time.time() + max(1, int(ttl))
    ip_strs = [str(ip) for ip in ips]

    _local[host_ascii] = (expires_at, ip_strs)

    r = _get_redis()
    if r is not None:
        key = f"dns:{host_ascii}"
        payload = {"expires_at": expires_at, "ips": ip_strs}
        r.setex(key, max(1, int(ttl)), json.dumps(payload))
