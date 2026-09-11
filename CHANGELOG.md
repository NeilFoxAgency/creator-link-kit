# Changelog

## Unreleased

- Added **CLK119** detection for percent-encoded UTM separators (`%26utm_...`).
  Excel, Slack, and CMS exports often encode `&` as `%26`, which glues later
  UTM pairs into one query value. `parse_qsl` and GA4 split only on a raw `&`.
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
  (`&amp;`, `&#38;`, `&#x26;`). Links copied from CMS pages, email HTML, or
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
  analytics.
- Added `clk agency-prepare` for governed multi-placement planning, audited
  connector handoff, and checksum-verified campaign artifacts.
