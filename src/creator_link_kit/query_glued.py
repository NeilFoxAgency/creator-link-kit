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
    # Only inspect the query (and, defensively, anything after ?).
    query_start = url.find("?")
    if query_start == -1:
        haystack = url
    else:
        haystack = url[query_start:]
        hash_at = haystack.find("#")
        if hash_at != -1:
            haystack = haystack[:hash_at]
    return bool(_GLUED_UTM.search(haystack) or _SPACED_UTM.search(haystack))
