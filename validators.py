# validators.py  (NUEVO)

"""Validadores de entrada (seguridad).

Este módulo se centra en validar target_url contra:
- SSRF (localhost / redes privadas / IPs reservadas)
- Denylist/Allowlist de dominios
- Reglas básicas de URL (http/https, host obligatorio, sin credenciales, longitud)

Nota: no hace requests HTTP; solo valida sintaxis y resoluciones DNS opcionales.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from fastapi import HTTPException

from config import get_settings

settings = get_settings()


def _normalize_host(host: str) -> str:
    """Normaliza host a ASCII/punycode y lowercase."""
    h = host.strip().strip(".").lower()
    try:
        # idna convierte unicode domain -> punycode ascii
        return h.encode("idna").decode("ascii")
    except Exception:
        # Si falla IDNA, lo devolvemos tal cual para que el validador lo rechace luego
        return h


def _is_denied_domain(host_ascii: str) -> bool:
    deny = [d.strip().strip(".").lower() for d in settings.denylist_domains]
    deny = [d.encode("idna").decode("ascii") for d in deny if d]
    for d in deny:
        # Bloquea el dominio y cualquier subdominio: *.d
        if host_ascii == d or host_ascii.endswith("." + d):
            return True
    return False


def _is_allowed_domain(host_ascii: str) -> bool:
    allow = [d.strip().strip(".").lower() for d in settings.allowlist_domains]
    allow = [d.encode("idna").decode("ascii") for d in allow if d]
    if not allow:
        return True  # <-- CAMBIO: allowlist vacía => no restringimos

    for a in allow:
        if host_ascii == a or host_ascii.endswith("." + a):
            return True
    return False


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    """Decide si una IP debe bloquearse por SSRF/abuso."""
    if not settings.deny_private_nets:
        return False

    # Bloqueamos rangos típicos y reservados
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolve_and_check_dns(host_ascii: str) -> None:
    """Si resolve_dns está activado, resuelve host y bloquea si apunta a IP privada/reservada."""
    if not settings.resolve_dns:
        return

    try:
        # getaddrinfo puede devolver IPv4/IPv6
        infos = socket.getaddrinfo(host_ascii, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="target_url host does not resolve")
    except Exception:
        raise HTTPException(status_code=400, detail="target_url DNS resolution failed")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise HTTPException(
                status_code=400, detail="target_url resolves to a blocked IP range"
            )


def validate_target_url(raw_url: str) -> str:
    """Valida target_url y devuelve la URL normalizada (string).

    Lanza HTTPException(400, ...) con un motivo explícito.
    """
    s = str(raw_url).strip()

    if not s:
        raise HTTPException(status_code=400, detail="target_url is empty")

    if len(s) > settings.max_target_url_length:
        raise HTTPException(status_code=400, detail="target_url too long")  # <-- CAMBIO

    if " " in s or "\t" in s or "\n" in s or "\r" in s:
        raise HTTPException(status_code=400, detail="target_url contains whitespace")

    parts = urlsplit(s)

    # Solo http/https
    if parts.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=400, detail="target_url scheme must be http or https"
        )

    # Host obligatorio
    if not parts.hostname:
        raise HTTPException(status_code=400, detail="target_url must include a host")

    # Sin credenciales en URL: user:pass@host
    if parts.username is not None or parts.password is not None:
        raise HTTPException(
            status_code=400, detail="target_url must not contain credentials"
        )

    host_ascii = _normalize_host(parts.hostname)

    # Bloqueos explícitos
    if host_ascii in {"localhost"}:
        raise HTTPException(status_code=400, detail="target_url host is not allowed")

    # Denylist/Allowlist
    if _is_denied_domain(host_ascii):
        raise HTTPException(
            status_code=400, detail="target_url domain is blocked"
        )  # <-- CAMBIO

    if not _is_allowed_domain(host_ascii):
        raise HTTPException(
            status_code=400, detail="target_url domain is not in allowlist"
        )  # <-- CAMBIO

    # IP literal -> bloquear si es privada/reservada
    try:
        ip = ipaddress.ip_address(host_ascii)
    except ValueError:
        ip = None

    if ip is not None:
        if _is_blocked_ip(ip):
            raise HTTPException(status_code=400, detail="target_url IP is in a blocked range")
    else:
        # DNS resolve opcional para evitar evil.com -> 10.0.0.1
        _resolve_and_check_dns(host_ascii)  # <-- CAMBIO

    return s


def get_client_ip_from_request(request) -> str:
    """Extrae IP del cliente de forma razonable.

    Esto es útil para futura geolocalización/bloqueo por país.
    """
    if settings.trust_x_forwarded_for:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()  # <-- CAMBIO: IP original del cliente

    if request.client:
        return request.client.host

    return "unknown"
