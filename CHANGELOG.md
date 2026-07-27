# Changelog

## Unreleased

- Added a reusable composite GitHub Action (`action.yml`) for one-line CI audits
  of shipped creator links against a convention file.
- Documented Action inputs and usage in the README; marked the related roadmap
  item complete.
- Added `.github/workflows/example-audit.yml` as a copy-paste starting point for
  downstream projects.

## 0.1.0 - 2026-07-16

- Added convention-as-code JSON configuration with optional YAML support.
- Added validated single-link generation with double-tag protection.
- Added roster CSV batch generation with row templates and isolated errors.
- Added CSV and text audits with rule codes, near-miss suggestions, and duplicate detection.
- Added text, JSON, and CSV reports plus CI-friendly exit codes.
- Added examples, tests, CI, security documentation, and an MIT license.
