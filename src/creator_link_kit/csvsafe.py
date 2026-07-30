"""Helpers for safely exporting untrusted values to spreadsheet-friendly CSV."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def safe_cell(value: Any) -> Any:
    """Prefix formula-like strings so spreadsheet apps treat them as text.

    CSV quoting alone does not stop Excel, Google Sheets, or LibreOffice from
    interpreting cells beginning with formula trigger characters. A leading
    apostrophe is the conventional, reversible neutralization used for exported
    untrusted text. Non-string values are returned unchanged.
    """

    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def safe_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of a row with every cell made spreadsheet-safe."""

    return {key: safe_cell(value) for key, value in row.items()}
