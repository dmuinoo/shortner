# policy_lists.py  (NUEVO)

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

import ipaddress

from config import settings


def _strip_comment(line: str) -> str:
    # elimina comentarios tipo "# ..."
    return line.split("#", 1)[0].strip()


def _to_host_or_token(token: str) -> str:
    """
    Acepta:
      - URL completa -> extrae hostname
      - dominio/FQDN -> devuelve tal cual
      - wildcard -> tal cual
      - IP/CIDR -> tal cual
    """
    t = token.strip()
    if "://" in t:
        parts = urlsplit(t)
        if parts.hostname:
            return parts.hostname.strip()
    return t


def _normalize_host(host: str) -> str:
    h = host.strip().strip(".").lower()
    try:
        return h.encode("idna").decode("ascii")
    except Exception:
        return h


@dataclass
class CompiledLists:
    # dominios exactos y sufijos (para wildcard *.example.com)
    domain_suffixes: set[str]
    domain_exact: set[str]
    # redes / IPs
    networks: list[ipaddress._BaseNetwork]


def _compile_file(path: str) -> CompiledLists:
    domain_suffixes: set[str] = set()
    domain_exact: set[str] = set()
    networks: list[ipaddress._BaseNetwork] = []

    if not os.path.exists(path):
        # no existe => listas vacías
        return CompiledLists(domain_suffixes, domain_exact, networks)

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = _strip_comment(raw)
            if not line:
                continue

            token = _to_host_or_token(line)
            if not token:
                continue

            token = token.strip()

            # IP o CIDR
            try:
                net = ipaddress.ip_network(token, strict=False)
                networks.append(net)
                continue
            except ValueError:
                pass

            # wildcard de dominio
            if token.startswith("*."):
                suf = _normalize_host(token[2:])
                if suf:
                    domain_suffixes.add(suf)
                continue

            # dominio exacto / FQDN / host
            domain_exact.add(_normalize_host(token))

    return CompiledLists(domain_suffixes, domain_exact, networks)


class ListsManager:
    """
    Loader con auto-reload por mtime (barato y profesional).
    """

    def __init__(self):
        self._cache = {}
        self._mtime = {}

    def load(self, path: str) -> CompiledLists:
        try:
            mtime = os.path.getmtime(path)
        except FileNotFoundError:
            mtime = None

        prev_mtime = self._mtime.get(path)
        if path in self._cache and prev_mtime == mtime:
            return self._cache[path]

        compiled = _compile_file(path)
        self._cache[path] = compiled
        self._mtime[path] = mtime
        return compiled


_lists_mgr = ListsManager()


def _match_domain(host_ascii: str, compiled: CompiledLists) -> bool:
    # exact match
    if host_ascii in compiled.domain_exact:
        return True
    # suffix match (*.example.com)
    for suf in compiled.domain_suffixes:
        if host_ascii == suf or host_ascii.endswith("." + suf):
            return True
    return False


def _match_ip(ip: ipaddress._BaseAddress, compiled: CompiledLists) -> bool:
    for net in compiled.networks:
        if ip in net:
            return True
    return False


def decide_by_policy(
    *,
    default_policy: str,
    allow_path: str,
    deny_path: str,
    host: Optional[str] = None,
    ip: Optional[str] = None,
) -> bool:
    """
    Devuelve True si PERMITE, False si BLOQUEA.

    - default_policy = "allow" => permite todo salvo denylist
    - default_policy = "deny"  => bloquea todo salvo allowlist
    """
    policy = (default_policy or "allow").strip().lower()
    if policy not in {"allow", "deny"}:
        policy = "allow"

    host_ascii = _normalize_host(host) if host else None

    ip_obj = None
    if ip:
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            ip_obj = None

    allow = _lists_mgr.load(allow_path)
    deny = _lists_mgr.load(deny_path)

    allow_hit = False
    deny_hit = False

    if host_ascii:
        allow_hit = allow_hit or _match_domain(host_ascii, allow)
        deny_hit = deny_hit or _match_domain(host_ascii, deny)

    if ip_obj is not None:
        allow_hit = allow_hit or _match_ip(ip_obj, allow)
        deny_hit = deny_hit or _match_ip(ip_obj, deny)

    if policy == "allow":
        return not deny_hit
    else:
        return allow_hit
