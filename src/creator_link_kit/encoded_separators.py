"""Detect percent-encoded UTM separators that glue later pairs together."""

from __future__ import annotations

import re

_ENCODED_UTM_SEP = re.compile(r"%26utm_", re.IGNORECASE)
_EMBEDDED_UTM_PAIR = re.compile(
    r"(?:[?&]|%26)utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)


def has_encoded_utm_separator(query: str, pairs: list[tuple[str, str]]) -> bool:
    """True when a later UTM pair is glued on with an encoded ampersand.

    ``urllib.parse.parse_qsl`` and GA4 split only on a raw ``&``. Spreadsheet,
    Slack, and CMS exports often encode that separator as ``%26``, so later
    ``utm_*`` pairs stay inside the previous value and attribution is lost.
    """
    if _ENCODED_UTM_SEP.search(query):
        return True
    for _key, value in pairs:
        if value and _EMBEDDED_UTM_PAIR.search(value):
            return True
    return False
