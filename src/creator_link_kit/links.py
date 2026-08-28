"""URL building and auditing rules."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from difflib import get_close_matches
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention, domain_is_owned
from .invisible import first_invisible_label
from .urls import authority_error as _authority_error

# Canonical UTM keys recognized by GA4 and most analytics tools.
# Typos (utm_souce, utm-source, UTM_Source) are ignored silently by GA4.
_STANDARD_UTM_KEYS = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
)
