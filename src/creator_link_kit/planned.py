"""Reconcile planned batch links against URLs that actually shipped.

Campaign ops generate a governed CSV with `clk batch`, then later audit
YouTube descriptions or a live export. Existing `clk audit` checks syntax and
cross-link consistency. It cannot answer: did every planned placement ship
the same destination and UTM set that was generated?

This module is opt-in and offline. It never calls a network, store API, or
analytics backend. Matching uses `utm_content` when present (the starter
maps that field to `placement_id`).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from urllib.parse import parse_qsl, urlsplit, urlencode, urlunsplit

from .config import Convention
from .links import Issue
from .urls import authority_error


_COMPARE_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_id")


def _fold(value: str, convention: Convention) -> str:
    if convention.casing == "lowercase":
        return value.casefold()
    return value


def parse_planned_link(url: str) -> tuple[str | None, dict[str, str], str | None]:
    """Return (destination, utm_map, error). Destination excludes UTM pairs."""
    raw = url.strip()
    if not raw:
        return None, {}, None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None, {}, "unparseable URL"
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None, {}, "not an absolute HTTP(S) URL"
    if authority_error(parsed) is not None:
        return None, {}, "malformed host"
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    utm = {key.lower(): value for key, value in pairs if key.lower().startswith("utm_")}
    non_utm = urlencode(sorted((k, v) for k, v in pairs if not k.lower().startswith("utm_")))
    destination = urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            non_utm,
            "",
        )
    )
    return destination, utm, None


def _key_for(utm: dict[str, str], destination: str | None, convention: Convention) -> str:
    content = utm.get("utm_content")
    if content:
        return f"content:{_fold(content, convention)}"
    if destination:
        return f"dest:{destination}"
    return "unknown:"


def reconcile_planned(
    planned_urls: Sequence[str],
    shipped_urls: Sequence[str],
    convention: Convention,
) -> list[Issue]:
    """Compare planned URLs to shipped URLs. Does not re-run syntax rules."""
    issues: list[Issue] = []
    planned_by_key: dict[str, list[tuple[int, str, str | None, dict[str, str]]]] = defaultdict(list)
    shipped_by_key: dict[str, list[tuple[int, str, str | None, dict[str, str]]]] = defaultdict(list)

    for index, raw in enumerate(planned_urls, start=1):
        url = raw.strip()
        if not url:
            continue
        dest, utm, err = parse_planned_link(url)
        if err:
            issues.append(
                Issue(
                    "CLK206",
                    "error",
                    f"planned URL could not be compared ({err})",
                    row=index,
                    url=url,
                )
            )
            continue
        planned_by_key[_key_for(utm, dest, convention)].append((index, url, dest, utm))

    for index, raw in enumerate(shipped_urls, start=1):
        url = raw.strip()
        if not url:
            continue
        dest, utm, err = parse_planned_link(url)
        if err:
            continue
        shipped_by_key[_key_for(utm, dest, convention)].append((index, url, dest, utm))

    for key, rows in planned_by_key.items():
        if len(rows) > 1 and key.startswith("content:"):
            issues.append(
                Issue(
                    "CLK210",
                    "error",
                    (
                        f"planned set repeats placement key {key.split(':', 1)[1]!r} "
                        f"on {len(rows)} rows; each placement_id must appear once"
                    ),
                    parameter="utm_content",
                    row=rows[0][0],
                    url=rows[0][1],
                )
            )

        if key not in shipped_by_key:
            label = key.split(":", 1)[1]
            issues.append(
                Issue(
                    "CLK206",
                    "error",
                    (
                        f"planned placement {label!r} is missing from the shipped "
                        "link set"
                    ),
                    parameter="utm_content" if key.startswith("content:") else None,
                    row=rows[0][0],
                    url=rows[0][1],
                )
            )
            continue

        planned_row, planned_url, planned_dest, planned_utm = rows[0]
        shipped_row, shipped_url, shipped_dest, shipped_utm = shipped_by_key[key][0]
        if planned_dest and shipped_dest and planned_dest != shipped_dest:
            issues.append(
                Issue(
                    "CLK207",
                    "error",
                    (
                        f"shipped destination {shipped_dest!r} does not match "
                        f"planned destination {planned_dest!r}"
                    ),
                    parameter="utm_content",
                    row=shipped_row,
                    url=shipped_url,
                )
            )
        drift = []
        for name in _COMPARE_KEYS:
            left = planned_utm.get(name)
            right = shipped_utm.get(name)
            if left is None and right is None:
                continue
            if left is None or right is None:
                drift.append(name)
                continue
            if _fold(left, convention) != _fold(right, convention):
                drift.append(name)
        if drift:
            issues.append(
                Issue(
                    "CLK208",
                    "warning",
                    (
                        "shipped UTM values differ from the planned link on "
                        + ", ".join(drift)
                    ),
                    parameter=drift[0],
                    row=shipped_row,
                    url=shipped_url,
                )
            )

    for key, rows in shipped_by_key.items():
        if key in planned_by_key:
            continue
        if not key.startswith("content:"):
            continue
        label = key.split(":", 1)[1]
        issues.append(
            Issue(
                "CLK209",
                "warning",
                f"shipped placement {label!r} was not in the planned link set",
                parameter="utm_content",
                row=rows[0][0],
                url=rows[0][1],
            )
        )

    return issues


def merge_audit_issues(
    base_issues: Iterable[Issue], extra: Iterable[Issue]
) -> tuple[Issue, ...]:
    return tuple(list(base_issues) + list(extra))
