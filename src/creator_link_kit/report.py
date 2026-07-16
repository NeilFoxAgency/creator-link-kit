"""Audit report formatting."""

from __future__ import annotations

import csv
import io
import json

from .links import AuditResult, Issue


def issue_dict(issue: Issue) -> dict[str, object]:
    return {
        "row": issue.row,
        "url": issue.url,
        "code": issue.code,
        "severity": issue.severity,
        "parameter": issue.parameter,
        "message": issue.message,
    }


def to_json(result: AuditResult) -> str:
    return json.dumps(
        {
            "checked": result.checked,
            "clean": result.clean,
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "issues": [issue_dict(issue) for issue in result.issues],
        },
        indent=2,
        sort_keys=True,
    )


def to_csv(result: AuditResult) -> str:
    buffer = io.StringIO()
    fieldnames = ["row", "url", "code", "severity", "parameter", "message"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(issue_dict(issue) for issue in result.issues)
    return buffer.getvalue()


def to_text(result: AuditResult) -> str:
    lines: list[str] = []
    current_row: int | None = None
    for issue in result.issues:
        if issue.row != current_row:
            current_row = issue.row
            lines.append(f"row {issue.row}: {issue.url}")
        parameter = f" [{issue.parameter}]" if issue.parameter else ""
        lines.append(
            f"  {issue.severity.upper():7} {issue.code}{parameter}: {issue.message}"
        )
    if not result.issues:
        lines.append("No issues found.")
    lines.append("")
    lines.append(
        f"{result.checked} links checked: {result.clean} clean, "
        f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)"
    )
    return "\n".join(lines)
