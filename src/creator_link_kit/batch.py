"""CSV batch generation."""

from __future__ import annotations

import csv
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from string import Formatter

from .config import Convention
from .csvsafe import safe_row
from .models import LinkIdentifiers
from .spec import build_link_specification


@dataclass(frozen=True)
class BatchSummary:
    total: int
    ok: int
    failed: int


def _template_fields(template: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name
    }


def _duplicate_placement_ids(
    rows: list[dict[str, str]], placement_column: str
) -> set[str]:
    counts = Counter(
        row.get(placement_column, "").strip()
        for row in rows
        if row.get(placement_column, "").strip()
    )
    return {value for value, count in counts.items() if count > 1}


def _render_discount_code(row: dict[str, str], convention: Convention) -> str | None:
    template = convention.batch.discount_code_template
    if not template:
        return None
    missing = sorted(
        field for field in _template_fields(template) if field not in row
    )
    if missing:
        raise ValueError(
            "discount_code_template references missing column(s): "
            + ", ".join(missing)
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
    source_rows = [dict(source_row) for source_row in rows]
    output: list[dict[str, str]] = []
    ok = 0
    failed = 0

    placement_column = convention.batch.placement_id_column
    placement_column_present = any(
        placement_column in source_row for source_row in source_rows
    )
    duplicate_placements = (
        _duplicate_placement_ids(source_rows, placement_column)
        if placement_column_present
        else set()
    )

    seen_codes: dict[str, int] = {}
    code_column = convention.batch.discount_code_column
    emit_codes = bool(convention.batch.discount_code_template)

    for index, source_row in enumerate(source_rows, start=1):
        row = dict(source_row)
        try:
            if placement_column_present:
                placement_id = row.get(placement_column, "").strip()
                if not placement_id:
                    raise ValueError(
                        f"{placement_column} must be non-empty when the "
                        "column is present"
                    )
                if placement_id in duplicate_placements:
                    raise ValueError(
                        f"{placement_column} {placement_id!r} is duplicated "
                        "within batch"
                    )

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
            original_destination = base_url or convention.base_url
            identifiers = LinkIdentifiers.from_mapping(
                row,
                columns=convention.batch.id_columns or None,
            )
            specification = build_link_specification(
                original_destination,
                params,
                convention,
                identifiers=identifiers,
            )

            discount_code = _render_discount_code(row, convention)
            if discount_code is not None:
                code_key = discount_code.casefold()
                if code_key in seen_codes:
                    raise ValueError(
                        f"discount code {discount_code!r} duplicates row "
                        f"{seen_codes[code_key]}"
                    )
                seen_codes[code_key] = index
                row[code_column] = discount_code

            row.update(
                generated_url=specification.generated_destination,
                link_spec=specification.to_json(indent=None),
                status="ok",
                issues="",
            )
            ok += 1
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
            row.update(generated_url="", link_spec="", status="error", issues=str(exc))
            if emit_codes and code_column not in row:
                row[code_column] = ""
            failed += 1
        output.append(row)
    return output, BatchSummary(total=len(output), ok=ok, failed=failed)


def batch_csv(
    roster_path: str | Path,
    output_path: str | Path | None,
    convention: Convention,
    spec_output_path: str | Path | None = None,
) -> tuple[list[dict[str, str]], BatchSummary]:
    roster = Path(roster_path)
    with roster.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("roster CSV has no header")
        rows, summary = generate_rows(reader, convention)
        fieldnames = list(reader.fieldnames)

    extras = ["generated_url"]
    if convention.batch.discount_code_template:
        extras.append(convention.batch.discount_code_column)
    extras.extend(["link_spec", "status", "issues"])
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
            writer.writerows(safe_row(row) for row in rows)

    if spec_output_path is not None:
        spec_destination = Path(spec_output_path)
        spec_destination.parent.mkdir(parents=True, exist_ok=True)
        serialized = [row["link_spec"] for row in rows if row.get("link_spec")]
        content = "\n".join(serialized)
        if content:
            content += "\n"
        spec_destination.write_text(content, encoding="utf-8")

    return rows, summary
