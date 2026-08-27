"""Query-string shape checks that must run on the raw URL.

These defects are invisible after urlsplit/parse_qsl because a second '?' is
not a new query string; it is absorbed into a parameter value.
"""

from __future__ import annotations

from .links import Issue

CLK119_MESSAGE = (
    "URL contains more than one '?' before the fragment; "
    "only the first '?' starts the query string, so later "
    "UTM pairs are absorbed into a parameter value and lost "
    "to GA4. Replace the extra '?' with '&'"
)


def extra_question_mark_issue(url: str) -> Issue | None:
    without_fragment = url.split("#", 1)[0]
    if without_fragment.count("?") <= 1:
        return None
    return Issue("CLK119", "error", CLK119_MESSAGE, url=url)
