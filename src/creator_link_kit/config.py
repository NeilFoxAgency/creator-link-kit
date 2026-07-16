"""Convention loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit


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


@dataclass(frozen=True)
class Convention:
    version: int
    base_url: str
    owned_domains: tuple[str, ...]
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
        except Exception as exc:
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
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("base_url must be an absolute http or https URL")

    owned_raw = raw.get("owned_domains", [])
    if not isinstance(owned_raw, list) or not all(
        isinstance(item, str) and item.strip() for item in owned_raw
    ):
        raise ConfigError("owned_domains must be a list of non-empty strings")
    owned_domains = tuple(item.lower().strip().lstrip(".") for item in owned_raw)

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
                raise ConfigError(f"parameters.{key}.pattern is invalid: {exc}") from exc
        parameters[key] = ParameterRule(tuple(allowed_raw), pattern)

    required_raw = raw.get("required", [])
    if not isinstance(required_raw, list) or not all(
        isinstance(item, str) for item in required_raw
    ):
        raise ConfigError("required must be a list of parameter names")
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
    if url_column is not None and not isinstance(url_column, str):
        raise ConfigError("batch.url_column must be a string")

    convention = Convention(
        version=version,
        base_url=base_url,
        owned_domains=owned_domains,
        casing=casing,
        max_value_length=max_value_length,
        required=required,
        parameters=parameters,
        defaults=defaults,
        batch=BatchConfig(param_map=param_map, url_column=url_column),
    )

    # Validate defaults against the same rules used for real links.
    from .links import validate_params

    issues = validate_params(defaults, convention, require_all=False)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise ConfigError("invalid defaults: " + "; ".join(i.message for i in errors))
    return convention


def load_convention(path: str | Path) -> Convention:
    config_path = Path(path)
    return convention_from_dict(_load_raw(config_path))


def starter_convention() -> dict[str, Any]:
    return {
        "version": 1,
        "base_url": "https://shop.example.com/product",
        "owned_domains": ["example.com"],
        "casing": "lowercase",
        "max_value_length": 80,
        "required": ["utm_source", "utm_medium", "utm_campaign"],
        "parameters": {
            "utm_source": {
                "allowed": ["youtube", "instagram", "tiktok", "newsletter"]
            },
            "utm_medium": {"allowed": ["influencer", "social", "email", "cpc"]},
            "utm_campaign": {"pattern": "^[a-z0-9][a-z0-9-]{2,48}$"},
            "utm_content": {"pattern": "^[a-z0-9][a-z0-9._-]{0,63}$"},
        },
        "defaults": {"utm_medium": "influencer"},
        "batch": {
            "param_map": {
                "utm_source": "{platform}",
                "utm_medium": "influencer",
                "utm_campaign": "product-launch",
                "utm_content": "{handle}",
            },
            "url_column": "landing_url",
        },
    }
