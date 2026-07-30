"""CSV batch generation."""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from string import Formatter

from .config import Convention
from .links import build_url


@dataclass(frozen=True)
class BatchSummary:
    total: int
    ok: int
    failed: int


def _template_fields(template: str) -> set[str]:
    return {
        field_name for _, field_name, _, _ in Formatter().parse(template) if field_name
    }


def _render_discount_code(row: dict[str, str], convention: Convention) -> str | None:
    template = convention.batch.discount_code_template
    if not template:
        return None
    missing = sorted(field for field in _template_fields(template) if field not in row)
    if missing:
        raise ValueError(
            "discount_code_template references missing column(s): " + ", ".join(missing)
        )
    code = template.format_map(row).strip()
    if not code:
        raise ValueError("discount code is empty after template expansion")
    if len(code) > convention.max_value_length:
        raise ValueError(
            f"discount code exceeds {convention.max_value_length} characters"
        )
    pattern = convention.batch.discount_code_pattern
    if pattern and re.fullmatch(pattern, code) is None:
        raise ValueError(f"discount code {code!r} does not match pattern {pattern!r}")
    return code


def generate_rows(
    rows: Iterable[dict[str, str]], convention: Convention
) -> tuple[list[dict[str, str]], BatchSummary]:
    output: list[dict[str, str]] = []
    ok = 0
    failed = 0
    seen_codes: dict[str, int] = {}
    code_column = convention.batch.discount_code_column
    emit_codes = bool(convention.batch.discount_code_template)

    for index, source_row in enumerate(rows, start=1):
        row = dict(source_row)
        try:
            params: dict[str, str] = {}
            for key, template in convention.batch.param_map.items():
                missing = sorted(
                    field for field in _template_fields(template) if field not in row
                )
                if missing:
                    raise ValueError(
                        f"template for {key} references missing column(s): "
                        + ", ".join(missing)
                    )
                params[key] = template.format_map(row)
            url_column = convention.batch.url_column
            base_url = row.get(url_column, "").strip() if url_column else ""
            generated = build_url(base_url or convention.base_url, params, convention)
            row.update(generated_url=generated, status="ok", issues="")
            if emit_codes:
                code = _render_discount_code(row, convention)
                assert code is not None
                # Uniqueness is case-insensitive so GRETA15 and greta15 collide.
                key = code.casefold()
                if key in seen_codes:
                    raise ValueError(
                        f"discount code {code!r} duplicates row {seen_codes[key]}"
                    )
                seen_codes[key] = index
                row[code_column] = code
            ok += 1
        except (KeyError, ValueError) as exc:
            row.update(generated_url="", status="error", issues=str(exc))
            if emit_codes and code_column not in row:
                row[code_column] = ""
            failed += 1
        output.append(row)
    return output, BatchSummary(total=len(output), ok=ok, failed=failed)


def batch_csv(
    roster_path: str | Path,
    output_path: str | Path | None,
    convention: Convention,
) -> tuple[list[dict[str, str]], BatchSummary]:
    roster = Path(roster_path)
    with roster.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("roster CSV has no header")
        rows, summary = generate_rows(reader, convention)
        fieldnames = list(reader.fieldnames)

    extras = ["generated_url", "status", "issues"]
    if convention.batch.discount_code_template:
        extras.insert(1, convention.batch.discount_code_column)
    for extra in extras:
        if extra not in fieldnames:
            fieldnames.append(extra)

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(rows)
    return rows, summary
