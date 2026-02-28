# target_validation.py

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit
from typing import Optional

from fastapi import HTTPException

from config import get_settings
from policy_lists import decide_by_policy
from dns_cache import get_cached, resolve_host, set_cached  # <-- CAMBIO

settings = get_settings()


def _normalize_host(host: str) -> str:
    h = host.strip().strip(".").lower()
    try:
        return h.encode("idna").decode("ascii")
    except Exception:
        return h


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    if not settings.deny_private_nets:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_target_url(raw_url: str, *, for_redirect: bool = False) -> str:
    s = str(raw_url).strip()

    if not s:
        raise HTTPException(status_code=400, detail="target_url is empty")
    if len(s) > settings.max_target_url_length:
        raise HTTPException(status_code=400, detail="target_url too long")
    if any(c in s for c in [" ", "\t", "\n", "\r"]):
        raise HTTPException(status_code=400, detail="target_url contains whitespace")

    parts = urlsplit(s)

    if parts.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="target_url scheme must be http or https")
    if not parts.hostname:
        raise HTTPException(status_code=400, detail="target_url must include a host")
    if parts.username is not None or parts.password is not None:
        raise HTTPException(status_code=400, detail="target_url must not contain credentials")

    host_ascii = _normalize_host(parts.hostname)

    if host_ascii in {"localhost"}:
        raise HTTPException(status_code=400, detail="target_url host is not allowed")

    # TARGET policy by host
    allowed_by_lists = decide_by_policy(
        default_policy=settings.default_target_policy,
        allow_path=settings.target_allowlist_path,
        deny_path=settings.target_denylist_path,
        host=host_ascii,
        ip=None,
    )
    if not allowed_by_lists:
        raise HTTPException(status_code=400, detail="target_url host blocked by policy")

    # literal IP?
    ip_lit: Optional[ipaddress._BaseAddress] = None
    try:
        ip_lit = ipaddress.ip_address(host_ascii)
    except ValueError:
        ip_lit = None

    if ip_lit is not None:
        allowed_ip = decide_by_policy(
            default_policy=settings.default_target_policy,
            allow_path=settings.target_allowlist_path,
            deny_path=settings.target_denylist_path,
            host=None,
            ip=str(ip_lit),
        )
        if not allowed_ip:
            raise HTTPException(status_code=400, detail="target_url IP blocked by policy")
        if _is_blocked_ip(ip_lit):
            raise HTTPException(status_code=400, detail="target_url IP is in a blocked range")
        return s

    # DNS resolve + cache
    if settings.resolve_dns:
        ips = get_cached(host_ascii)  # <-- CAMBIO
        if ips is None:
            ips, ttl = resolve_host(host_ascii)  # <-- CAMBIO (ttl puede venir del DNS o fixed)
            set_cached(host_ascii, ips, ttl)  # <-- CAMBIO

        for ip in ips:
            allowed_ip = decide_by_policy(
                default_policy=settings.default_target_policy,
                allow_path=settings.target_allowlist_path,
                deny_path=settings.target_denylist_path,
                host=None,
                ip=str(ip),
            )
            if not allowed_ip:
                raise HTTPException(status_code=400, detail="target_url resolves to blocked IP by policy")
            if _is_blocked_ip(ip):
                raise HTTPException(status_code=400, detail="target_url resolves to a blocked IP range")

    return s


def get_client_ip_from_request(request) -> str:
    """
    IP del cliente final (no del proxy), si hay proxy de confianza.
    """
    # Si tienes trusted_proxy_cidrs, solo confiar XFF cuando el remote es uno de tus proxies
    if settings.trusted_proxy_cidrs:
        try:
            remote = request.client.host if request.client else ""
            remote_ip = ipaddress.ip_address(remote)
            ok = any(remote_ip in ipaddress.ip_network(c, strict=False) for c in settings.trusted_proxy_cidrs)
        except Exception:
            ok = False
    else:
        ok = True

    if settings.trust_x_forwarded_for and ok:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()

    if request.client:
        return request.client.host
    return "unknown"
