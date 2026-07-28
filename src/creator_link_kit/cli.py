"""Command-line interface."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

from . import __version__
from .batch import batch_csv
from .config import ConfigError, load_convention, starter_convention
from .links import audit_urls, build_url
from .qr import (
    QrDependencyError,
    make_qr_jobs_from_csv,
    make_qr_jobs_from_urls,
    write_qr_codes,
)
from .report import to_csv, to_json, to_text


def _param(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("parameters must use key=value")
    key, val = value.split("=", 1)
    if not key:
        raise argparse.ArgumentTypeError("parameter key cannot be empty")
    return key, val


def _read_audit_urls(path: Path, url_column: str | None) -> list[str]:
    if path.suffix.lower() == ".csv":
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
            return [row.get(column, "") for row in reader]
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clk",
        description="Generate and audit governed creator campaign links.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="write a starter convention")
    init_parser.add_argument("path", nargs="?", default="creator-links.json")
    init_parser.add_argument("--force", action="store_true")

    validate_parser = subparsers.add_parser(
        "validate-config", help="validate a convention file"
    )
    validate_parser.add_argument("--config", required=True)

    build_parser_ = subparsers.add_parser("build", help="build one validated link")
    build_parser_.add_argument("--config", required=True)
    build_parser_.add_argument("--url")
    build_parser_.add_argument("--param", action="append", default=[], type=_param)

    batch_parser = subparsers.add_parser("batch", help="generate links from a CSV")
    batch_parser.add_argument("--config", required=True)
    batch_parser.add_argument("--roster", required=True)
    batch_parser.add_argument("--out")

    audit_parser = subparsers.add_parser("audit", help="audit links from CSV or text")
    audit_parser.add_argument("--config", required=True)
    audit_parser.add_argument("--input", required=True)
    audit_parser.add_argument("--url-column")
    audit_parser.add_argument(
        "--format", choices=("text", "json", "csv"), default="text"
    )
    audit_parser.add_argument("--out")
    audit_parser.add_argument("--strict", action="store_true")

    qr_parser = subparsers.add_parser(
        "qr",
        help="export QR codes for campaign links (requires optional [qr] extra)",
    )
    qr_parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="absolute http(s) URL to encode (repeatable)",
    )
    qr_parser.add_argument(
        "--input",
        help="CSV or text file of links (CSV preferred after clk batch)",
    )
    qr_parser.add_argument("--url-column", help="CSV column holding the URL")
    qr_parser.add_argument(
        "--name-column",
        help="CSV column used for file names (default: handle/name/creator)",
    )
    qr_parser.add_argument(
        "--out-dir",
        default="qr-codes",
        help="directory for generated QR files (default: qr-codes)",
    )
    qr_parser.add_argument(
        "--format",
        choices=("svg", "png"),
        default="svg",
        help="output format (default: svg)",
    )
    qr_parser.add_argument(
        "--scale",
        type=int,
        default=8,
        help="module scale factor 1-40 (default: 8)",
    )
    qr_parser.add_argument(
        "--error",
        choices=("l", "m", "q", "h"),
        default="m",
        help="QR error correction level (default: m)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            path = Path(args.path)
            if path.exists() and not args.force:
                raise ValueError(f"{path} already exists; use --force to replace it")
            path.write_text(
                json.dumps(starter_convention(), indent=2) + "\n", encoding="utf-8"
            )
            print(f"Wrote {path}")
            return 0

        if args.command == "qr":
            jobs = []
            if args.url:
                jobs.extend(make_qr_jobs_from_urls(args.url))
            if args.input:
                input_path = Path(args.input)
                if input_path.suffix.lower() == ".csv":
                    jobs.extend(
                        make_qr_jobs_from_csv(
                            input_path,
                            url_column=args.url_column,
                            name_column=args.name_column,
                        )
                    )
                else:
                    urls = [
                        line.strip()
                        for line in input_path.read_text(encoding="utf-8").splitlines()
                    ]
                    jobs.extend(make_qr_jobs_from_urls(urls))
            if not jobs:
                raise ValueError("provide at least one --url or --input with links")
            summary = write_qr_codes(
                jobs,
                Path(args.out_dir),
                fmt=args.format,
                scale=args.scale,
                error=args.error,
            )
            print(
                f"Wrote {summary.written}/{summary.total} QR codes to {args.out_dir}; "
                f"{summary.failed} failed",
                file=sys.stderr,
            )
            return 1 if summary.failed else 0

        convention = load_convention(args.config)

        if args.command == "validate-config":
            print(f"Valid convention: {args.config}")
            return 0

        if args.command == "build":
            params = dict(args.param)
            print(build_url(args.url or convention.base_url, params, convention))
            return 0

        if args.command == "batch":
            rows, summary = batch_csv(args.roster, args.out, convention)
            if args.out is None:
                fieldnames: list[str] = []
                for row in rows:
                    for key in row:
                        if key not in fieldnames:
                            fieldnames.append(key)
                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(
                f"Generated {summary.ok}/{summary.total} links; "
                f"{summary.failed} failed",
                file=sys.stderr,
            )
            return 1 if summary.failed else 0

        if args.command == "audit":
            urls = _read_audit_urls(Path(args.input), args.url_column)
            result = audit_urls(urls, convention)
            rendered = {
                "text": to_text,
                "json": to_json,
                "csv": to_csv,
            }[args.format](result)
            if args.out:
                Path(args.out).write_text(rendered, encoding="utf-8")
            else:
                print(rendered)
            if result.errors or (args.strict and result.warnings):
                return 1
            return 0
    except QrDependencyError as exc:
        print(f"clk: {exc}", file=sys.stderr)
        return 2
    except (ConfigError, OSError, ValueError) as exc:
        print(f"clk: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
