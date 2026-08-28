# Changelog

## Unreleased

- Added **CLK120** detection for percent-encoded query delimiters immediately
  before a UTM key (`%26utm_` or `%3Futm_`). "Encode this URL" tools, JSON
  dumps, and spreadsheet formulas often encode `&`/`?`; `parse_qsl` then
  absorbs later UTM pairs into the previous value so GA4 never sees them.
  Encoded ampersands that are not followed by a UTM key are not flagged.

- Added **CLK118** detection for UTM parameters placed in the URL fragment
  (`#...`). Browsers and GA4 never send the fragment to the server, so these
  links attribute as direct/none despite looking tracked. Innocent SPA hashes
  without UTM keys are not flagged.
- Added free-form text URL extraction for `clk audit`: absolute HTTP(S) links can
  now be audited directly from pasted descriptions or notes, with duplicates
  retained for `CLK005` and unmatched sentence punctuation trimmed safely.
- Tightened convention parsing so unknown top-level, parameter-rule, and batch
  keys fail closed instead of being silently ignored; boolean values are also
  rejected where integer version and length fields are required.
- Reject ambiguous roster CSV shapes with blank or duplicate headers or surplus
  row values, while preserving the existing short-row fallback behavior.
- Added **CLK113** errors for whitespace-only UTM values and values with leading
  or trailing whitespace.
- Added **CLK112** errors for unresolved template placeholders such as
  `{{paid_social}}`, `${SOURCE}`, `%{campaign}%`, and `[[CREATOR]]`.
- Added **CLK117** detection for HTML-entity-corrupted query strings
  (`&`, `&#38;`, `&#x26;`). Links copied from CMS pages, email HTML, or
  Word often retain these entities; GA4 never splits the intended UTM pairs.
- Added **CLK114** audit detection for misspelled UTM parameter names
  (`utm_souce`, `utm-source`, `UTM_SOURCE`, and close variants). GA4 ignores
  unknown keys, so these typos previously produced silent attribution loss.
- Added a **by rule code** summary (per-code error and warning counts) to
  audit text, HTML, and JSON reports so large placement audits are easier
  to triage.
- Hardened URL authority validation so empty hosts, spaces, underscores,
  empty DNS labels, and other malformed hostnames are rejected (`CLK001`).
  Valid DNS names and IP literals continue to be accepted.
- Declared and CI-tested Python 3.13 support alongside 3.10–3.12.
- Added cross-link placement-ID consistency checks (`CLK116`) so the same
  `utm_content` value cannot label different campaigns or destinations within
  one audit set. The same placement on different platforms remains allowed
  when the campaign and destination match.
- Reject reserved and placeholder UTM values (`null`, `undefined`, `n/a`,
  `test`, `example`, `placeholder`, `tbd`, and related forms) with `CLK115`
  during build and audit so unfinished template or CMS defaults do not reach
  GA4 and similar tools.
- Reusable GitHub Action now writes a **by rule code** markdown table (error and
  warning counts per CLK code) to the Actions job summary so operators can
  triage dominant failure modes without downloading logs.

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
- Added a deterministic SHA-256 configuration fingerprint to generated link
  specifications without changing `schema_version`.
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
- Added a literal v0.1 compatibility fixture covering legacy handle-based
  `utm_content` generation without v0.2 ID or discount-code columns.

## 0.1.0 - 2026-07-16

- Added convention-as-code JSON configuration with optional YAML support.
- Added validated single-link generation with double-tag protection.
- Added roster CSV batch generation with row templates and isolated errors.
- Added CSV and text audits with rule codes, near-miss suggestions, and duplicate
  detection.
- Added text, JSON, and CSV reports plus CI-friendly exit codes.
- Added examples, tests, CI, security documentation, and an MIT license.
