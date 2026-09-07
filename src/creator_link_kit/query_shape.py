"""Query-string shape checks that must run on the raw URL.

These defects are invisible after urlsplit/parse_qsl because a second '?' is
not a new query string; it is absorbed into a parameter value.
"""

from __future__ import annotations

CLK119_CODE = "CLK119"
CLK119_MESSAGE = (
    "URL contains more than one '?' before the fragment; "
    "only the first '?' starts the query string, so later "
    "UTM pairs are absorbed into a parameter value and lost "
    "to GA4. Replace the extra '?' with '&'"
)


def has_extra_question_mark(url: str) -> bool:
    """Return True when a second '?' appears before any fragment."""
    without_fragment = url.split("#", 1)[0]
    return without_fragment.count("?") > 1
