"""CLK119: detect percent-encoded UTM query separators.

Excel, Slack, and CMS exports often encode '&' as '%26'. parse_qsl and GA4
split only on a raw '&', so a later UTM pair stays glued inside an earlier
value and the session attributes as direct/none.

This module wraps ``links.validate_url`` when the package is imported so
single-link checks, ``audit_urls``, and the CLI all surface CLK119 without
rewriting the large links module.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import parse_qsl, urlsplit

from .links import Issue, validate_url as _validate_url

_ENCODED_UTM_SEPARATOR = re.compile(r"%26utm_", re.IGNORECASE)
_GLUED_UTM_IN_VALUE = re.compile(
    r"&utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)


def detect_encoded_separators(url: str) -> list[Issue]:
    """Return CLK119 issues for *url*, or an empty list."""
    if _ENCODED_UTM_SEPARATOR.search(url):
        return [
            Issue(
                "CLK119",
                "error",
                (
                    "URL contains a percent-encoded UTM separator (%26utm_); "
                    "parse_qsl and GA4 split only on a raw '&', so later UTM "
                    "pairs stay glued inside an earlier value. Replace '%26' "
                    "with '&' when it separates UTM parameters"
                ),
                url=url,
            )
        ]
    try:
        parsed = urlsplit(url)
    except ValueError:
        return []
    for _key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if value and _GLUED_UTM_IN_VALUE.search(value):
            return [
                Issue(
                    "CLK119",
                    "error",
                    (
                        "A UTM value contains another '&utm_...' pair; "
                        "the later parameters were not split. This usually "
                        "means a percent-encoded '&' (%26) was copied from "
                        "Excel, Slack, or a CMS export"
                    ),
                    url=url,
                )
            ]
    return []


def validate_url_with_clk119(url: str, convention) -> list[Issue]:
    extras = detect_encoded_separators(url)
    issues = _validate_url(url, convention)
    if extras and not any(issue.code == "CLK119" for issue in issues):
        return extras + issues
    return issues


def install() -> Callable:
    """Replace ``links.validate_url`` with the CLK119-aware wrapper."""
    from . import links

    links.validate_url = validate_url_with_clk119  # type: ignore[method-assign]
    return links.validate_url


install()
