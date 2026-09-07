"""CLK129: detect UTM key=value pairs that landed in the URL path."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from .links import Issue, validate_url as _validate_url

_PATH_UTM_PAIR = re.compile(
    r"utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)

_INSTALLED = False


def has_path_utm_pair(url: str) -> bool:
    """Return True when a standard UTM assignment appears in the path."""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return bool(_PATH_UTM_PAIR.search(parsed.path or ""))


def validate_url_with_path_utm(url: str, convention):
    issues = list(_validate_url(url, convention))
    if has_path_utm_pair(url) and not any(i.code == "CLK129" for i in issues):
        issues.append(
            Issue(
                "CLK129",
                "error",
                (
                    "UTM parameters appear in the URL path; "
                    "they are not part of the query string, so GA4 and "
                    "similar tools never record the campaign. Insert '?' "
                    "before the first UTM pair and use '&' between pairs"
                ),
                url=url,
            )
        )
    return issues


def install() -> None:
    """Bind CLK129 onto creator_link_kit.links.validate_url."""
    global _INSTALLED
    if _INSTALLED:
        return
    from . import links as links_mod

    links_mod.validate_url = validate_url_with_path_utm
    _INSTALLED = True
