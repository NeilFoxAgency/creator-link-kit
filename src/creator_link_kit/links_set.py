"""Audit-set checks and URL builders that depend on validate_url."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import Convention
from .links_rules import AuditResult, Issue, validate_params, validate_url
from .urls import authority_error as _authority_error


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
