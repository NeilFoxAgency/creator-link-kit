"""URL building and auditing rules."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from difflib import get_close_matches
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention, domain_is_owned
from .nested import find_nested_tracking
from .urls import authority_error as _authority_error
