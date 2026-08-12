"""Shared URL authority validation helpers."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import SplitResult

# DNS label: letters/digits, optional interior hyphen; not empty.
_DNS_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_MAX_HOSTNAME_LEN = 253


def _is_valid_hostname(host: str) -> bool:
    """Return True for a usable DNS name or IP literal."""

    if not host or len(host) > _MAX_HOSTNAME_LEN:
        return False
    if " " in host or "\t" in host or "_" in host:
        return False
    # Trailing dot is allowed in DNS but strip for validation.
    candidate = host.rstrip(".")
    if not candidate:
        return False
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        pass
    labels = candidate.split(".")
    if any(not label for label in labels):
        return False
    return all(_DNS_LABEL.fullmatch(label) for label in labels)


def authority_error(parsed: SplitResult) -> str | None:
    """Return a precise error for unsafe or malformed URL authorities."""

    if parsed.username is not None or parsed.password is not None:
        return "URL must not include embedded credentials"
    try:
        _ = parsed.port
    except ValueError as exc:
        return f"URL has an invalid port: {exc}"

    host = parsed.hostname
    if host is None or host == "":
        return "URL authority must include a hostname"
    if not _is_valid_hostname(host):
        return f"URL has a malformed hostname: {host!r}"
    return None
