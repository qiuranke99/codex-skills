#!/usr/bin/env python3
"""Credential-free public HTTP(S) URL policy shared by every package surface."""

from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlsplit

from _contract_utils import ContractError


def public_http_host(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("URL must be a non-empty string")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ContractError(f"unsafe public URL: {exc}") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ContractError("only absolute http/https URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise ContractError("URL credentials are forbidden")
    if port is not None and not 1 <= port <= 65535:
        raise ContractError("URL has an invalid port")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local")):
        raise ContractError("local hostnames are forbidden")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not literal.is_global:
            raise ContractError(
                "private, loopback, link-local, reserved, or multicast IP literals are forbidden"
            )
    return host[4:] if host.startswith("www.") else host


def assert_safe_public_http_url(value: Any) -> None:
    public_http_host(value)
