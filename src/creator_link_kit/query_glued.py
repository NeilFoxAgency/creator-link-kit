"""Detect UTM pairs concatenated without a real query delimiter.

Agency and brand teams often build campaign URLs in spreadsheets by
joining cells. A missing ``&`` produces:

    ?utm_source=youtubeutm_medium=influencer

``parse_qsl`` treats the second key as part of the first value. GA4
never sees ``utm_medium``. The link still *looks* tagged.

CLK120 covers percent-encoded ``&`` / ``?``. CLK127 (open) covers
literal ``;`` and ``,``. CLK128 inspects the raw query for a standard
UTM key glued onto a previous pair with no delimiter.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Convention
    from .links import Issue

_STANDARD_UTM = r"utm_(?:source|medium|campaign|term|content|id)"

# A second standard UTM key starts inside a previous pair's value,
# with no &, ?, #, or ; between the value and the next key.
_GLUED_UTM = re.compile(
    rf"(?:^|[?&#;]){_STANDARD_UTM}=[^?&#;]*?{_STANDARD_UTM}=",
    re.IGNORECASE,
)

# Same defect with a literal space or tab used as a "separator"
# (Sheets wrap / CONCAT). parse_qsl keeps the space inside the value.
_SPACED_UTM = re.compile(
    rf"(?:^|[?&#;]){_STANDARD_UTM}=[^\s?&#;]*[\t ]+{_STANDARD_UTM}=",
    re.IGNORECASE,
)


def has_glued_utm_pair(url: str) -> bool:
    """Return True when two standard UTM keys share one query pair."""

    if not url:
        return False
    query_start = url.find("?")
    if query_start == -1:
        haystack = url
    else:
        haystack = url[query_start:]
        hash_at = haystack.find("#")
        if hash_at != -1:
            haystack = haystack[:hash_at]
    return bool(_GLUED_UTM.search(haystack) or _SPACED_UTM.search(haystack))


def install() -> None:
    """Bind CLK128 onto ``links.validate_url`` so audit/build/CLI see it."""

    from . import links

    original = links.validate_url
    if getattr(original, "_clk128", False):
        return

    def wrapped(url: str, convention: Convention) -> list[Issue]:
        issues = list(original(url, convention))
        if has_glued_utm_pair(url) and not any(i.code == "CLK128" for i in issues):
            issues.insert(
                0,
                links.Issue(
                    "CLK128",
                    "error",
                    (
                        "UTM parameters are glued together without a query "
                        "delimiter; GA4 will not split the later keys. Insert "
                        "a bare '&' between each utm_* pair"
                    ),
                    url=url,
                ),
            )
        return issues

    wrapped._clk128 = True  # type: ignore[attr-defined]
    links.validate_url = wrapped
