# Changelog

## Unreleased

- Added optional `clk qr` command to export SVG or PNG QR codes for campaign
  links (YouTube end screens, packaging inserts, events). Install with
  `pip install 'creator-link-kit[qr]'` (segno). Core package remains
  dependency-free; generation is fully offline.

## 0.1.0 - 2026-07-16

- Added convention-as-code JSON configuration with optional YAML support.
- Added validated single-link generation with double-tag protection.
- Added roster CSV batch generation with row templates and isolated errors.
- Added CSV and text audits with rule codes, near-miss suggestions, and duplicate detection.
- Added text, JSON, and CSV reports plus CI-friendly exit codes.
- Added examples, tests, CI, security documentation, and an MIT license.
