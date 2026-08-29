"""Detect nested tracking inside UTM values and wrapper parameters."""

from __future__ import annotations

import re

# Nested tracking: a UTM *value* that is itself a URL or that embeds another
# UTM pair. This happens when a full tagged landing URL is pasted into
# utm_content, utm_term, a redirect parameter, or a second shortener field.
# Analytics then records the wrapper value instead of the intended dimension.
_EMBEDDED_ABSOLUTE_URL = re.compile(r"(?i)^https?://")
_EMBEDDED_UTM_PAIR = re.compile(
    r"(?i)(?:^|[?&#/])utm_(?:source|medium|campaign|term|content|id)="
)


def find_nested_tracking(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Return (parameter, message) pairs for nested tracking."""

    findings: list[tuple[str, str]] = []
    seen_params: set[str] = set()
    for key, value in pairs:
        if not value:
            continue
        looks_like_url = _EMBEDDED_ABSOLUTE_URL.search(value.strip()) is not None
        embeds_utm = _EMBEDDED_UTM_PAIR.search(value) is not None
        if not looks_like_url and not embeds_utm:
            continue
        if not key.startswith("utm_") and not embeds_utm:
            continue
        if key in seen_params:
            continue
        seen_params.add(key)
        if key.startswith("utm_"):
            reason = (
                f"UTM value for {key!r} embeds another URL or UTM pair; "
                "analytics will store the wrapper instead of the intended "
                "campaign dimension. Use a stable placement ID, not a URL"
            )
        else:
            reason = (
                f"query parameter {key!r} wraps a destination that already "
                "contains UTM parameters; the inner tags are not the page "
                "query string and will not attribute in GA4"
            )
        findings.append((key, reason))
    return findings
