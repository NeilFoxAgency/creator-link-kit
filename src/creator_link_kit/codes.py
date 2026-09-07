"""Reconcile planned discount codes against shipped campaign URLs.

Creator campaigns often issue one unique store code per placement. Generation
already refuses duplicate codes inside a batch, but live description CSVs and
Shopify/GA exports can still ship a missing, extra, or reused code. This
module stays offline and only compares identifier strings.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from .config import Convention
from .links import Issue

# Query keys commonly used by shops and link builders for promo codes.
# Keep the list explicit so generic "id" / "ref" parameters are not treated
# as commerce codes.
DISCOUNT_QUERY_KEYS = frozenset(
    {
        "discount",
        "discount_code",
        "code",
        "coupon",
        "coupon_code",
        "promo",
        "promo_code",
        "voucher",
    }
)


def _fold(value: str) -> str:
    return value.strip().casefold()


def planned_codes_from_rows(
    rows: Iterable[Mapping[str, str | None]],
    *,
    column: str,
) -> tuple[dict[str, str], list[Issue]]:
    """Return {folded: canonical} planned codes plus CLK205 duplicate issues."""

    planned: dict[str, str] = {}
    seen_rows: dict[str, int] = {}
    issues: list[Issue] = []
    for index, row in enumerate(rows, start=2):
        raw = row.get(column)
        if raw is None:
            continue
        code = raw.strip()
        if not code:
            continue
        key = _fold(code)
        if key in seen_rows:
            issues.append(
                Issue(
                    "CLK205",
                    "error",
                    (
                        f"discount code {code!r} is duplicated in the codes file "
                        f"(also row {seen_rows[key]}); a code must identify one "
                        "placement"
                    ),
                    parameter=column,
                    row=index,
                )
            )
            continue
        seen_rows[key] = index
        planned[key] = code
    return planned, issues


def load_planned_codes(path: str | Path, convention: Convention) -> tuple[dict[str, str], list[Issue]]:
    source = Path(path)
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("codes CSV has no header")
        fieldnames = [name.strip() for name in reader.fieldnames if name]
        column = convention.batch.discount_code_column
        if column not in fieldnames:
            candidates = ("discount_code", "code", "coupon", "promo", "discount")
            column = next((name for name in candidates if name in fieldnames), "")
        if not column:
            raise ValueError(
                "codes CSV has no discount-code column; expected "
                f"{convention.batch.discount_code_column!r} or one of "
                "discount_code, code, coupon, promo, discount"
            )
        rows = list(reader)
    return planned_codes_from_rows(rows, column=column)


def discount_values_in_url(url: str) -> list[tuple[str, str]]:
    """Return (query_key, value) pairs that look like discount codes."""

    try:
        parsed = urlsplit(url)
    except ValueError:
        return []
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    found: list[tuple[str, str]] = []
    for key, value in pairs:
        if key.casefold() in DISCOUNT_QUERY_KEYS and value.strip():
            found.append((key, value.strip()))
    return found


def reconcile_codes(
    urls: Sequence[str],
    planned: Mapping[str, str],
) -> list[Issue]:
    """Compare shipped URL discount query values with the planned set."""

    shipped: dict[str, list[tuple[int, str, str, str]]] = {}
    issues: list[Issue] = []
    for row, raw in enumerate(urls, start=1):
        url = raw.strip()
        if not url:
            continue
        for key, value in discount_values_in_url(url):
            folded = _fold(value)
            shipped.setdefault(folded, []).append((row, url, key, value))
            if folded not in planned:
                issues.append(
                    Issue(
                        "CLK204",
                        "warning",
                        (
                            f"shipped discount {value!r} is not in the planned "
                            "codes file; confirm it is not a test or leftover code"
                        ),
                        parameter=key,
                        row=row,
                        url=url,
                    )
                )

    for folded, canonical in planned.items():
        if folded in shipped:
            continue
        issues.append(
            Issue(
                "CLK203",
                "error",
                (
                    f"planned discount code {canonical!r} never appears as a "
                    "discount/coupon/promo query value in the audited links"
                ),
                parameter="discount_code",
            )
        )
    return issues
