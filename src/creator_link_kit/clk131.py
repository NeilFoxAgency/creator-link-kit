"""CLK131: ASCII control characters inside UTM values."""

from __future__ import annotations

import re
from collections.abc import Mapping

_CONTROL_IN_VALUE = re.compile(r"[\x00-\x1f\x7f]")
_CONTROL_NAMES = {
    0: "NUL",
    9: "TAB",
    10: "LF",
    11: "VT",
    12: "FF",
    13: "CR",
    127: "DEL",
}


def control_labels(value: str) -> str:
    labels: list[str] = []
    for char in value:
        code = ord(char)
        if code < 32 or code == 127:
            labels.append(_CONTROL_NAMES.get(code, f"U+{code:04X}"))
        if len(labels) == 3:
            break
    return ", ".join(labels)


def has_control_chars(value: str) -> bool:
    return _CONTROL_IN_VALUE.search(value) is not None


def clk131_message(value: str) -> str:
    labels = control_labels(value)
    return (
        f"value contains ASCII control character(s) ({labels}); "
        "remove line breaks, tabs, and other non-printable "
        "characters before publishing or analytics and CSV "
        "exports will split or mismatch the dimension"
    )


def install(links_module) -> None:
    """Wrap links.validate_params so CLK131 runs during build and audit."""

    original = links_module.validate_params
    if getattr(original, "_clk131_installed", False):
        return

    def validate_params(
        params: Mapping[str, str],
        convention,
        *,
        require_all: bool = True,
    ):
        issues = original(params, convention, require_all=require_all)
        extra = []
        for key, value in params.items():
            rule = convention.parameters.get(key)
            if rule is None or value == "":
                continue
            if has_control_chars(value):
                extra.append(
                    links_module.Issue(
                        "CLK131",
                        "error",
                        clk131_message(value),
                        key,
                    )
                )
        return extra + issues

    validate_params._clk131_installed = True  # type: ignore[attr-defined]
    links_module.validate_params = validate_params
