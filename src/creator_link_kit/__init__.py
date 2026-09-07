"""Creator Link Kit package."""

from .config import ConfigError, Convention, convention_fingerprint, load_convention
from .links import AuditResult, Issue, audit_urls, build_url
from .links import validate_url as _validate_url
from .models import (
    AuditIssue,
    LinkAudit,
    LinkIdentifiers,
    LinkProvider,
    LinkProvisionRequest,
    LinkSpecification,
    ProvisionedLink,
)
from .query_encoded import has_encoded_utm_delimiter
from .spec import build_link_specification
from . import links as _links

_CLK120_MESSAGE = (
    "URL contains a percent-encoded query delimiter before a "
    "UTM key (%26 or %3F). The following UTM pairs are absorbed "
    "into the previous value and never reach GA4. Replace "
    "encoded separators with a bare '&' or '?'"
)


def validate_url(url: str, convention: Convention):
    """Validate a URL and flag percent-encoded UTM delimiters (CLK120)."""
    issues = []
    if has_encoded_utm_delimiter(url):
        issues.append(
            Issue(
                "CLK120",
                "error",
                _CLK120_MESSAGE,
                url=url,
            )
        )
    issues.extend(_validate_url(url, convention))
    return issues


_links.validate_url = validate_url

__all__ = [
    "AuditIssue",
    "AuditResult",
    "ConfigError",
    "Convention",
    "Issue",
    "LinkAudit",
    "LinkIdentifiers",
    "LinkProvider",
    "LinkProvisionRequest",
    "LinkSpecification",
    "ProvisionedLink",
    "audit_urls",
    "build_link_specification",
    "build_url",
    "convention_fingerprint",
    "has_encoded_utm_delimiter",
    "load_convention",
    "validate_url",
]

__version__ = "0.2.0"
