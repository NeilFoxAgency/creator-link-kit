# Changelog

## 0.2.0 - 2026-07-30

- Added governed `utm_id` support to the starter convention and cross-link
  campaign-name/ID consistency checks (`CLK110` and `CLK111`).
- Switched the recommended `utm_content` template from creator handle to stable
  `placement_id`.
- Added standard brand, campaign, creator, and placement identifier mappings.
- Added batch-level duplicate placement ID validation while allowing multiple
  placements for the same creator.
- Added production mode with hard failures for unapproved destination domains.
- Added machine-readable JSON link specifications and JSONL batch export.
- Added provider-neutral link provisioning models and a `LinkProvider` protocol.
- Added optional placement-specific discount-code generation with template
  expansion, regex validation, and case-insensitive uniqueness checks.
- Added optional offline SVG/PNG QR export, preferring `placement_id` for stable
  filenames when it is available.
- Added escaped, self-contained HTML audit reports for offline client sharing.
- Added a reusable GitHub Action for convention audits in other repositories.
- Rejected malformed-port and embedded-credential campaign URLs.
- Neutralized spreadsheet-formula prefixes in generated and audit CSV exports.
- Documented and hardened the public-repository boundary for secrets, commerce
  data, orders, customers, and private analytics.

## 0.1.0 - 2026-07-16

- Added convention-as-code JSON configuration with optional YAML support.
- Added validated single-link generation with double-tag protection.
- Added roster CSV batch generation with row templates and isolated errors.
- Added CSV and text audits with rule codes, near-miss suggestions, and duplicate
  detection.
- Added text, JSON, and CSV reports plus CI-friendly exit codes.
- Added examples, tests, CI, security documentation, and an MIT license.
