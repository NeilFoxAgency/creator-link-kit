# Changelog

## Unreleased

- Added optional HTML audit report (`clk audit --format html`) for offline client sharing with escaped dynamic content.
- Added optional per-creator **discount code** generation during `clk batch`:
  template expansion from roster columns, regex validation, case-insensitive
  uniqueness, and a dedicated output column. Starter convention and examples
  include a `{handle}15` pattern so agencies can mint unique codes alongside
  governed UTM links offline.

## 0.1.0 - 2026-07-16

- Added convention-as-code JSON configuration with optional YAML support.
- Added validated single-link generation with double-tag protection.
- Added roster CSV batch generation with row templates and isolated errors.
- Added CSV and text audits with rule codes, near-miss suggestions, and duplicate detection.
- Added text, JSON, and CSV reports plus CI-friendly exit codes.
- Added examples, tests, CI, security documentation, and an MIT license.
