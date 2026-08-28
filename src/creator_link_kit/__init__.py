"""Creator Link Kit package."""

from .config import ConfigError, Convention, convention_fingerprint, load_convention
from .links import AuditResult, Issue, audit_urls, build_url, validate_url
from .models import (
    AuditIssue,
    LinkAudit,
    LinkIdentifiers,
    LinkProvider,
    LinkProvisionRequest,
    LinkSpecification,
    ProvisionedLink,
)
from .query_invisible import install as _install_clk121
from .spec import build_link_specification

_install_clk121()

# Re-bind after install so package-level validate_url includes CLK121.
from .links import validate_url as validate_url

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
    "load_convention",
    "validate_url",
]

__version__ = "0.2.0"
