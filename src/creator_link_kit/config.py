"""Convention loading and validation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .models import IDENTIFIER_FIELDS
from .urls import authority_error


class ConfigError(ValueError):
    """Raised when a convention file is invalid."""


@dataclass(frozen=True)
class ParameterRule:
    allowed: tuple[str, ...] = ()
    pattern: str | None = None


@dataclass(frozen=True)
class BatchConfig:
    param_map: dict[str, str] = field(default_factory=dict)
    url_column: str | None = None
    id_columns: dict[str, str] = field(default_factory=dict)
    discount_code_template: str | None = None
    discount_code_pattern: str | None = None
    discount_code_column: str = "discount_code"

    @property
    def placement_id_column(self) -> str:
        return self.id_columns.get("placement_id", "placement_id")


_BATCH_OUTPUT_COLUMNS = frozenset({"generated_url", "link_spec", "status", "issues"})


@dataclass(frozen=True)
class Convention:
    version: int
    base_url: str
    owned_domains: tuple[str, ...]
    mode: str
    casing: str
    max_value_length: int
    required: tuple[str, ...]
    parameters: dict[str, ParameterRule]
    defaults: dict[str, str]
    batch: BatchConfig


def _expect_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be an object")
    return value


def _expect_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{label} must be a non-empty string")
    return value.strip()


def _normalize_owned_domain(value: str) -> str:
    normalized = value.strip().lower().lstrip(".").rstrip(".")
    if not normalized:
        raise ValueError("domain must contain a hostname")
    try:
        parsed = urlsplit("//" + normalized)
    except ValueError as exc:
        raise ValueError(f"domain cannot be parsed: {exc}") from exc
    if (
        authority_error(parsed) is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("domain must be a hostname without credentials, port, or path")
    if parsed.hostname is None or parsed.hostname.rstrip(".").lower() != normalized:
        raise ValueError("domain must be a valid hostname")
    return normalized


def domain_is_owned(host: str, owned_domains: tuple[str, ...]) -> bool:
    normalized = host.lower().rstrip(".")
    return any(
        normalized == domain or normalized.endswith("." + domain)
        for domain in owned_domains
    )


def _load_raw(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config: {exc}") from exc

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ConfigError(
                "YAML support requires 'pip install creator-link-kit[yaml]'"
            ) from exc
        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ConfigError(f"invalid YAML: {exc}") from exc
    else:
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ) from exc
    return _expect_mapping(raw, "config")


def convention_from_dict(raw: dict[str, Any]) -> Convention:
    version = raw.get("version")
    if version != 1:
        raise ConfigError("version must be 1")

    base_url = _expect_string(raw.get("base_url"), "base_url")
    try:
        parsed = urlsplit(base_url)
    except ValueError as exc:
        raise ConfigError(f"base_url cannot be parsed: {exc}") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("base_url must be an absolute http or https URL")
    base_authority_error = authority_error(parsed)
    if base_authority_error is not None:
        raise ConfigError(f"base_url{base_authority_error.removeprefix('URL')}")

    owned_raw = raw.get("owned_domains", [])
    if not isinstance(owned_raw, list) or not all(
        isinstance(item, str) and item.strip() for item in owned_raw
    ):
        raise ConfigError("owned_domains must be a list of non-empty strings")
    try:
        owned_domains = tuple(_normalize_owned_domain(item) for item in owned_raw)
    except ValueError as exc:
        raise ConfigError(f"owned_domains contains an invalid domain: {exc}") from exc
    if len(set(owned_domains)) != len(owned_domains):
        raise ConfigError("owned_domains contains duplicates")

    mode = raw.get("mode", "development")
    if not isinstance(mode, str) or mode not in {"development", "production"}:
        raise ConfigError("mode must be 'development' or 'production'")
    if mode == "production":
        if not owned_domains:
            raise ConfigError("production mode requires at least one owned domain")
        if not domain_is_owned(parsed.hostname or "", owned_domains):
            raise ConfigError("production base_url must use an owned domain")

    casing = raw.get("casing", "lowercase")
    if casing not in {"lowercase", "any"}:
        raise ConfigError("casing must be 'lowercase' or 'any'")

    max_value_length = raw.get("max_value_length", 80)
    if not isinstance(max_value_length, int) or max_value_length < 1:
        raise ConfigError("max_value_length must be a positive integer")

    params_raw = _expect_mapping(raw.get("parameters", {}), "parameters")
    parameters: dict[str, ParameterRule] = {}
    for key, rule_value in params_raw.items():
        if not isinstance(key, str) or not key.startswith("utm_"):
            raise ConfigError(f"parameter key {key!r} must start with 'utm_'")
        rule_raw = _expect_mapping(rule_value, f"parameters.{key}")
        allowed_raw = rule_raw.get("allowed", [])
        if not isinstance(allowed_raw, list) or not all(
            isinstance(item, str) and item != "" for item in allowed_raw
        ):
            raise ConfigError(f"parameters.{key}.allowed must be a string list")
        if len(set(allowed_raw)) != len(allowed_raw):
            raise ConfigError(f"parameters.{key}.allowed contains duplicates")
        pattern = rule_raw.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                raise ConfigError(f"parameters.{key}.pattern must be a string")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ConfigError(
                    f"parameters.{key}.pattern is invalid: {exc}"
                ) from exc
        parameters[key] = ParameterRule(tuple(allowed_raw), pattern)

    required_raw = raw.get("required", [])
    if not isinstance(required_raw, list) or not all(
        isinstance(item, str) for item in required_raw
    ):
        raise ConfigError("required must be a list of parameter names")
    if len(set(required_raw)) != len(required_raw):
        raise ConfigError("required contains duplicates")
    required = tuple(required_raw)
    unknown_required = [key for key in required if key not in parameters]
    if unknown_required:
        raise ConfigError(
            "required parameters need rules: " + ", ".join(unknown_required)
        )

    defaults_raw = _expect_mapping(raw.get("defaults", {}), "defaults")
    defaults: dict[str, str] = {}
    for key, value in defaults_raw.items():
        if key not in parameters:
            raise ConfigError(f"default {key!r} has no governing rule")
        if not isinstance(value, str):
            raise ConfigError(f"default {key!r} must be a string")
        defaults[key] = value

    batch_raw = _expect_mapping(raw.get("batch", {}), "batch")
    param_map_raw = _expect_mapping(batch_raw.get("param_map", {}), "batch.param_map")
    param_map: dict[str, str] = {}
    for key, value in param_map_raw.items():
        if key not in parameters:
            raise ConfigError(f"batch mapping {key!r} has no governing rule")
        if not isinstance(value, str):
            raise ConfigError(f"batch mapping {key!r} must be a string template")
        param_map[key] = value

    url_column = batch_raw.get("url_column")
    if url_column is not None:
        url_column = _expect_string(url_column, "batch.url_column")

    id_columns_raw = _expect_mapping(
        batch_raw.get("id_columns", {}), "batch.id_columns"
    )
    id_columns: dict[str, str] = {}
    for identifier, column in id_columns_raw.items():
        if identifier not in IDENTIFIER_FIELDS:
            allowed = ", ".join(IDENTIFIER_FIELDS)
            raise ConfigError(
                f"batch.id_columns key {identifier!r} must be one of: {allowed}"
            )
        id_columns[identifier] = _expect_string(
            column, f"batch.id_columns.{identifier}"
        )
    if len(set(id_columns.values())) != len(id_columns):
        raise ConfigError("batch.id_columns cannot map multiple IDs to one column")

    discount_code_template = batch_raw.get("discount_code_template")
    if discount_code_template is not None:
        discount_code_template = _expect_string(
            discount_code_template, "batch.discount_code_template"
        )

    discount_code_pattern = batch_raw.get("discount_code_pattern")
    if discount_code_pattern is not None:
        if not isinstance(discount_code_pattern, str):
            raise ConfigError("batch.discount_code_pattern must be a string")
        try:
            re.compile(discount_code_pattern)
        except re.error as exc:
            raise ConfigError(f"batch.discount_code_pattern is invalid: {exc}") from exc

    discount_code_column = _expect_string(
        batch_raw.get("discount_code_column", "discount_code"),
        "batch.discount_code_column",
    )
    if discount_code_column in _BATCH_OUTPUT_COLUMNS:
        raise ConfigError(
            "batch.discount_code_column cannot replace a reserved output column: "
            + discount_code_column
        )
    protected_columns = set(id_columns.values())
    if url_column:
        protected_columns.add(url_column)
    if discount_code_column in protected_columns:
        raise ConfigError(
            "batch.discount_code_column cannot replace an identifier or URL column: "
            + discount_code_column
        )

    convention = Convention(
        version=version,
        base_url=base_url,
        owned_domains=owned_domains,
        mode=mode,
        casing=casing,
        max_value_length=max_value_length,
        required=required,
        parameters=parameters,
        defaults=defaults,
        batch=BatchConfig(
            param_map=param_map,
            url_column=url_column,
            id_columns=id_columns,
            discount_code_template=discount_code_template,
            discount_code_pattern=discount_code_pattern,
            discount_code_column=discount_code_column,
        ),
    )

    # Validate defaults against the same rules used for real links.
    from .links import validate_params

    issues = validate_params(defaults, convention, require_all=False)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise ConfigError("invalid defaults: " + "; ".join(i.message for i in errors))
    return convention


def convention_fingerprint(convention: Convention) -> str:
    """Return a deterministic SHA-256 identifier for a normalized convention.

    The digest identifies the policy used to generate a specification. It is
    not a signature and contains no credentials or raw roster data.
    """

    payload = {
        "version": convention.version,
        "base_url": convention.base_url,
        "owned_domains": list(convention.owned_domains),
        "mode": convention.mode,
        "casing": convention.casing,
        "max_value_length": convention.max_value_length,
        "required": list(convention.required),
        "parameters": {
            key: {"allowed": list(rule.allowed), "pattern": rule.pattern}
            for key, rule in convention.parameters.items()
        },
        "defaults": dict(convention.defaults),
        "batch": {
            "param_map": dict(convention.batch.param_map),
            "url_column": convention.batch.url_column,
            "id_columns": dict(convention.batch.id_columns),
            "discount_code_template": convention.batch.discount_code_template,
            "discount_code_pattern": convention.batch.discount_code_pattern,
            "discount_code_column": convention.batch.discount_code_column,
        },
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_convention(path: str | Path) -> Convention:
    config_path = Path(path)
    return convention_from_dict(_load_raw(config_path))


def starter_convention() -> dict[str, Any]:
    return {
        "version": 1,
        "base_url": "https://shop.example.com/product",
        "owned_domains": ["example.com"],
        "mode": "production",
        "casing": "lowercase",
        "max_value_length": 100,
        "required": [
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_id",
            "utm_content",
        ],
        "parameters": {
            "utm_source": {"allowed": ["youtube", "instagram", "tiktok", "newsletter"]},
            "utm_medium": {"allowed": ["influencer", "social", "email", "cpc"]},
            "utm_campaign": {"pattern": "^[a-z0-9][a-z0-9-]{2,48}$"},
            "utm_id": {"pattern": "^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,99}$"},
            "utm_content": {"pattern": "^[a-z0-9][a-z0-9._-]{0,63}$"},
        },
        "defaults": {"utm_medium": "influencer"},
        "batch": {
            "param_map": {
                "utm_source": "{platform}",
                "utm_medium": "influencer",
                "utm_campaign": "{campaign_id}",
                "utm_id": "{campaign_id}",
                "utm_content": "{placement_id}",
            },
            "url_column": "landing_url",
            "id_columns": {
                "brand_id": "brand_id",
                "campaign_id": "campaign_id",
                "creator_id": "creator_id",
                "placement_id": "placement_id",
            },
            "discount_code_template": "{placement_id}",
            "discount_code_pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$",
            "discount_code_column": "discount_code",
        },
    }
