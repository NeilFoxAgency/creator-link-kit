"""Optional QR code export for campaign links.

Requires the optional ``[qr]`` extra (segno). Core package stays
dependency-free; QR generation is offline and never sends URLs
or campaign data anywhere.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class QrDependencyError(RuntimeError):
    """Raised when the optional QR dependency is not installed."""


def _require_segno():
    try:
        import segno  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised via CLI path
        raise QrDependencyError(
            "QR export requires the optional dependency 'segno'. "
            "Install with: pip install 'creator-link-kit[qr]'"
        ) from exc
    return segno


_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def safe_filename(stem: str, *, max_length: int = 80) -> str:
    """Sanitize a handle or label for use as a file stem."""
    cleaned = _SAFE_NAME.sub("-", stem.strip()).strip("-._")
    if not cleaned:
        cleaned = "link"
    return cleaned[:max_length]


@dataclass(frozen=True)
class QrJob:
    url: str
    stem: str


@dataclass(frozen=True)
class QrSummary:
    total: int
    written: int
    failed: int
    paths: tuple[str, ...]


def make_qr_jobs_from_urls(
    urls: Iterable[str],
    *,
    prefix: str = "qr",
) -> list[QrJob]:
    jobs: list[QrJob] = []
    for index, raw in enumerate(urls, start=1):
        url = raw.strip()
        if not url:
            continue
        jobs.append(QrJob(url=url, stem=f"{prefix}-{index:03d}"))
    return jobs


def make_qr_jobs_from_csv(
    path: Path,
    *,
    url_column: str | None = None,
    name_column: str | None = None,
) -> list[QrJob]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        column = url_column
        if column is None:
            candidates = (
                "generated_url",
                "url",
                "link",
                "landing_url",
                "destination_url",
            )
            column = next(
                (name for name in candidates if name in reader.fieldnames), None
            )
        if column is None or column not in reader.fieldnames:
            raise ValueError(
                "could not identify URL column; pass --url-column explicitly"
            )
        label_column = name_column
        if label_column is None:
            for candidate in ("handle", "name", "creator", "utm_content"):
                if candidate in reader.fieldnames:
                    label_column = candidate
                    break
        jobs: list[QrJob] = []
        for index, row in enumerate(reader, start=1):
            url = (row.get(column) or "").strip()
            if not url:
                continue
            if label_column and (row.get(label_column) or "").strip():
                stem = safe_filename(row[label_column].strip())
            else:
                stem = f"qr-{index:03d}"
            jobs.append(QrJob(url=url, stem=stem))
        return jobs


def write_qr_codes(
    jobs: Iterable[QrJob],
    output_dir: Path,
    *,
    fmt: str = "svg",
    scale: int = 8,
    error: str = "m",
) -> QrSummary:
    """Write one QR file per job into *output_dir*.

    Formats: ``svg`` (vector, no extra deps beyond segno) or ``png``.
    """
    segno = _require_segno()
    fmt = fmt.lower().lstrip(".")
    if fmt not in {"svg", "png"}:
        raise ValueError("format must be 'svg' or 'png'")
    if scale < 1 or scale > 40:
        raise ValueError("scale must be between 1 and 40")
    if error not in {"l", "m", "q", "h"}:
        raise ValueError("error correction must be one of l, m, q, h")

    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    failed = 0
    paths: list[str] = []
    total = 0
    used_stems: dict[str, int] = {}

    for job in jobs:
        total += 1
        stem = job.stem
        if stem in used_stems:
            used_stems[stem] += 1
            stem = f"{stem}-{used_stems[job.stem]}"
        else:
            used_stems[stem] = 1
        destination = output_dir / f"{stem}.{fmt}"
        try:
            if not job.url.startswith(("http://", "https://")):
                raise ValueError("URL must be absolute http or https")
            qr = segno.make(job.url, error=error)
            if fmt == "svg":
                qr.save(str(destination), scale=scale, xmldecl=True)
            else:
                qr.save(str(destination), scale=scale)
            written += 1
            paths.append(str(destination))
        except Exception:
            failed += 1
    return QrSummary(
        total=total, written=written, failed=failed, paths=tuple(paths)
    )
