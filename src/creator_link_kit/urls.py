"""Shared URL authority validation helpers."""

from __future__ import annotations

import re
from ipaddress import ip_address
from urllib.parse import SplitResult

_DNS_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


def _hostname_error(hostname: str | None) -> str | None:
    if hostname is None or not hostname.rstrip("."):
        return "URL must include a hostname"

    normalized = hostname.rstrip(".")
    try:
        ip_address(normalized)
        return None
    except ValueError:
        pass

    try:
        ascii_hostname = normalized.encode("idna").decode("ascii")
    except UnicodeError:
        return "URL has an invalid hostname"
    labels = ascii_hostname.split(".")
    if len(ascii_hostname) > 253 or any(
        _DNS_LABEL.fullmatch(label) is None for label in labels
    ):
        return "URL has an invalid hostname"
    return None


def authority_error(parsed: SplitResult) -> str | None:
    """Return a precise error for unsafe or malformed URL authorities."""

    if parsed.username is not None or parsed.password is not None:
        return "URL must not include embedded credentials"
    try:
        _ = parsed.port
    except ValueError as exc:
        return f"URL has an invalid port: {exc}"
    return _hostname_error(parsed.hostname)
