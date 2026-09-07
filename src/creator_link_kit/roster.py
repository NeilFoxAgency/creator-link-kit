"""Compare shipped campaign links against an expected placement roster."""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from .config import Convention


def normalize_placement(value: str, convention: Convention) -> str:
    stripped = value.strip()
    if convention.casing == "lowercase":
        return stripped.lower()
    return stripped


def load_expected_placement_ids(
    path: str | Path,
    convention: Convention,
) -> tuple[str, ...]:
    """Read unique non-empty placement IDs from a campaign roster CSV."""

    roster = Path(path)
    column = convention.batch.placement_id_column
    with roster.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("roster CSV has no header")
        if column not in reader.fieldnames:
            raise ValueError(
                f"roster is missing placement column {column!r}; "
                "pass a roster that includes the convention's placement_id column"
            )
        ordered: list[str] = []
        seen: set[str] = set()
        for row in reader:
            value = (row.get(column) or "").strip()
            if not value:
                continue
            key = normalize_placement(value, convention)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
    return tuple(ordered)


def roster_coverage_issues(
    urls: Iterable[str],
    expected_placements: Iterable[str],
    convention: Convention,
):
    """Compare shipped utm_content values against an expected placement roster.

    CLK201 is an error: a planned placement never appeared in the shipped set.
    CLK202 is a warning: a shipped utm_content is not on the roster. Extra live
    or test links are common, so this stays a warning unless --strict is used.
    """

    from .links import Issue, _utm_params

    shipped: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for row, raw_url in enumerate(urls, start=1):
        url = raw_url.strip()
        if not url:
            continue
        params = _utm_params(url)
        if not params:
            continue
        content = params.get("utm_content")
        if not content:
            continue
        shipped[normalize_placement(content, convention)].append((row, url, content))

    issues = []
    expected_keys: dict[str, str] = {}
    for placement in expected_placements:
        value = placement.strip()
        if not value:
            continue
        key = normalize_placement(value, convention)
        if key in expected_keys:
            continue
        expected_keys[key] = value
        if key not in shipped:
            issues.append(
                Issue(
                    "CLK201",
                    "error",
                    (
                        f"expected placement {value!r} was not found in shipped "
                        "links; the creator may have used a different URL or "
                        "the asset may not have published yet"
                    ),
                    parameter="utm_content",
                )
            )

    for key, rows in sorted(shipped.items()):
        if key in expected_keys:
            continue
        for row, url, content in rows:
            issues.append(
                Issue(
                    "CLK202",
                    "warning",
                    (
                        f"utm_content {content!r} is not in the expected roster; "
                        "confirm this is an intentional extra placement"
                    ),
                    parameter="utm_content",
                    row=row,
                    url=url,
                )
            )
    return issues
