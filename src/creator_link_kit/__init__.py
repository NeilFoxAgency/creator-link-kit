"""Creator Link Kit package."""

from .config import Convention, ConfigError, load_convention
from .links import AuditResult, Issue, audit_urls, build_url, validate_url

__all__ = [
    "AuditResult",
    "ConfigError",
    "Convention",
    "Issue",
    "audit_urls",
    "build_url",
    "load_convention",
    "validate_url",
]

__version__ = "0.1.0"
