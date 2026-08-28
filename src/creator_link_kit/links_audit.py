"""URL audit helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from difflib import get_close_matches
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention, domain_is_owned
from .urls import authority_error as _authority_error
from .links_validate import (
    AuditResult,
    Issue,
    _FRAGMENT_UTM_PAIR,
    _HTML_ENTITY_QUERY_MARKERS,
    _STANDARD_UTM_KEYS,
    validate_params,
)


def validate_url(url: str, convention: Convention) -> list[Issue]:
    issues: list[Issue] = []

    # Scan the raw URL first. Numeric entities such as &#38; contain '#' and
    # would be treated as the start of a fragment by urlsplit, hiding the rest
    # of the query from parse_qsl. Named entities like &amp; stay in the query
    # string but still prevent proper UTM separation.
    for marker in _HTML_ENTITY_QUERY_MARKERS:
        if marker in url:
            issues.append(
                Issue(
                    "CLK117",
                    "error",
                    (
                        f"URL contains HTML entity {marker!r}; "
                        "UTM parameters after this point are not separated "
                        "for GA4 and similar tools. Replace with a bare '&'"
                    ),
                    url=url,
                )
            )
            break

    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        return [Issue("CLK001", "error", f"URL cannot be parsed: {exc}", url=url)]

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return [
            Issue(
                "CLK001",
                "error",
                "URL must be an absolute http or https URL",
                url=url,
            )
        ]
    authority_error = _authority_error(parsed)
    if authority_error is not None:
        return [Issue("CLK001", "error", authority_error, url=url)]
    if parsed.scheme == "http":
        issues.append(Issue("CLK002", "warning", "URL uses http instead of https"))
    if convention.owned_domains and not domain_is_owned(
        parsed.hostname or "", convention.owned_domains
    ):
        severity = "error" if convention.mode == "production" else "warning"
        issues.append(
            Issue(
                "CLK003",
                severity,
                f"destination host {parsed.hostname!r} is outside owned_domains",
            )
        )

    # UTM keys in the fragment never reach the server or GA4. SPA/CMS links
    # often put tracking after # by mistake; the link looks tagged but
    # attributes as direct/none.
    if parsed.fragment and _FRAGMENT_UTM_PAIR.search(parsed.fragment):
        issues.append(
            Issue(
                "CLK118",
                "error",
                (
                    "UTM parameters appear in the URL fragment (#...); "
                    "browsers and GA4 do not send the fragment to the server, "
                    "so attribution is lost. Move UTM parameters into the "
                    "query string before the fragment"
                ),
                url=url,
            )
        )

    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    # Near-miss keys that look like UTMs but are not the canonical forms.
    # GA4 ignores unknown parameter names, so these produce silent data loss.
    for key, _value in pairs:
        normalized = key.lower().replace("-", "_")
        if key in _STANDARD_UTM_KEYS:
            continue
        if normalized in _STANDARD_UTM_KEYS or (
            key.lower().startswith("utm")
            and get_close_matches(normalized, _STANDARD_UTM_KEYS, n=1, cutoff=0.75)
        ):
            suggestion = get_close_matches(
                normalized, list(_STANDARD_UTM_KEYS), n=1, cutoff=0.5
            )
            hint = f"; did you mean {suggestion[0]!r}?" if suggestion else ""
            issues.append(
                Issue(
                    "CLK114",
                    "error",
                    (
                        f"query parameter {key!r} looks like a misspelled UTM key"
                        f"{hint}; GA4 ignores unknown parameter names"
                    ),
                    parameter=key,
                )
            )

    utm_pairs = [(key, value) for key, value in pairs if key.startswith("utm_")]
    if not utm_pairs:
        issues.append(Issue("CLK004", "warning", "URL has no UTM parameters"))

    counts = Counter(key for key, _ in utm_pairs)
    for key, count in counts.items():
        if count > 1:
            issues.append(
                Issue(
                    "CLK103",
                    "error",
                    f"parameter appears {count} times in the query string",
                    key,
                )
            )

    # The last value mirrors how many analytics systems resolve repeated keys,
    # while CLK103 still makes the ambiguity a hard error.
    params = {key: value for key, value in utm_pairs}
    issues.extend(validate_params(params, convention))
    return [issue.with_context(url=url) for issue in issues]


def build_url(
    base_url: str,
    params: Mapping[str, str],
    convention: Convention,
) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute http or https URL")
    authority_error = _authority_error(parsed)
    if authority_error is not None:
        raise ValueError(authority_error)

    existing_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    existing_keys = {key for key, _ in existing_pairs}
    merged = dict(convention.defaults)
    merged.update(params)
    collisions = sorted(key for key in merged if key in existing_keys)
    if collisions:
        raise ValueError(
            "refusing to double-tag existing parameter(s): " + ", ".join(collisions)
        )

    issues = validate_params(merged, convention)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise ValueError(
            "; ".join(f"{i.code} {i.parameter}: {i.message}" for i in errors)
        )

    query = urlencode(existing_pairs + list(merged.items()), doseq=True)
    result = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment)
    )
    final_errors = [
        issue for issue in validate_url(result, convention) if issue.severity == "error"
    ]
    if final_errors:
        raise ValueError("; ".join(f"{i.code}: {i.message}" for i in final_errors))
    return result
