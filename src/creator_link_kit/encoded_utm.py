"""Detect percent-encoded UTM separators that glue later pairs into one value."""

from __future__ import annotations

import re

# Spreadsheet/CMS exports often turn "&utm_" into "%26utm_". parse_qsl and
# GA4 split only on a raw "&", so the later pair never becomes its own key.
_ENCODED_UTM_SEPARATOR_IN_QUERY = re.compile(r"%26utm_", re.IGNORECASE)
_ENCODED_UTM_SEPARATOR_IN_VALUE = re.compile(
    r"(?:[?&]|%26)utm_(?:source|medium|campaign|term|content|id)=",
    re.IGNORECASE,
)

CLK119_MESSAGE = (
    "query string contains a percent-encoded UTM separator "
    "(%26utm_...); later UTM pairs stay glued inside an earlier "
    "value and GA4 will not split them. Replace %26 with a bare '&'"
)


def has_encoded_utm_separator(raw_query: str, pairs: list[tuple[str, str]]) -> bool:
    if raw_query and _ENCODED_UTM_SEPARATOR_IN_QUERY.search(raw_query):
        return True
    for _key, value in pairs:
        if value and _ENCODED_UTM_SEPARATOR_IN_VALUE.search(value):
            return True
    return False
