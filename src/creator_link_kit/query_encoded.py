"""Raw-URL query-shape checks that must run before urlsplit/parse_qsl."""

from __future__ import annotations

import re

# Percent-encoded query delimiters that hide later UTM keys inside an earlier
# value. "Encode this URL" tools, JSON string dumps, and spreadsheet formulas
# often turn "&utm_" into "%26utm_" (or "?utm_" into "%3Futm_"). parse_qsl
# decodes the separator into the previous value, so GA4 never sees the later
# keys. Detection stays on the raw URL so it is not hidden by decoding.
ENCODED_QUERY_DELIM_UTM = re.compile(
    r"%3[Ff]utm_(?:source|medium|campaign|term|content|id)="
    r"|%26utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)


def has_encoded_utm_delimiter(url: str) -> bool:
    """Return True if a percent-encoded ? or & precedes a UTM key."""
    return ENCODED_QUERY_DELIM_UTM.search(url) is not None
