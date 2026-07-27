"""Audit report formatting."""

from __future__ import annotations

import csv
import html
import io
import json
from collections import defaultdict

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


def to_html(result: AuditResult) -> str:
    """Render a self-contained HTML audit report safe for offline sharing."""

    by_row: dict[int | None, list[Issue]] = defaultdict(list)
    for issue in result.issues:
        by_row[issue.row].append(issue)

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Creator Link Kit audit report</title>",
        "<style>",
        ":root { color-scheme: light dark; }",
        "body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; "
        "line-height: 1.45; margin: 1.5rem; max-width: 52rem; }",
        "h1 { font-size: 1.35rem; margin-bottom: 0.25rem; }",
        ".summary { margin: 1rem 0 1.5rem; padding: 0.75rem 1rem; "
        "border: 1px solid #ccc; border-radius: 0.4rem; }",
        ".row-block { margin-bottom: 1.25rem; }",
        ".row-url { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; "
        "font-size: 0.9rem; word-break: break-all; }",
        "ul { margin: 0.4rem 0 0; padding-left: 1.2rem; }",
        ".error { color: #b00020; }",
        ".warning { color: #8a5a00; }",
        "@media (prefers-color-scheme: dark) {",
        "  .summary { border-color: #555; }",
        "  .error { color: #ff8a9b; }",
        "  .warning { color: #ffcc66; }",
        "}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Creator Link Kit audit report</h1>",
        '<p class="summary">',
        f"{result.checked} links checked: {result.clean} clean, "
        f"{len(result.errors)} error(s), {len(result.warnings)} warning(s)",
        "</p>",
    ]

    if not result.issues:
        parts.append("<p>No issues found.</p>")
    else:
        for row in sorted(by_row.keys(), key=lambda value: (value is None, value or 0)):
            issues = by_row[row]
            sample_url = issues[0].url or ""
            row_label = f"Row {row}" if row is not None else "Unspecified row"
            parts.append('<section class="row-block">')
            parts.append(f"<h2>{html.escape(row_label)}</h2>")
            if sample_url:
                parts.append(
                    f'<p class="row-url">{html.escape(sample_url)}</p>'
                )
            parts.append("<ul>")
            for issue in issues:
                severity_class = html.escape(issue.severity)
                parameter = (
                    f" [{html.escape(issue.parameter)}]" if issue.parameter else ""
                )
                parts.append(
                    f'<li class="{severity_class}">'
                    f"<strong>{html.escape(issue.severity.upper())}</strong> "
                    f"{html.escape(issue.code)}{parameter}: "
                    f"{html.escape(issue.message)}"
                    "</li>"
                )
            parts.append("</ul>")
            parts.append("</section>")

    parts.extend(["</body>", "</html>", ""])
    return "\n".join(parts)
