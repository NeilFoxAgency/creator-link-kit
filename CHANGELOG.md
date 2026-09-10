# Changelog

## Unreleased

- Added **CLK119** detection for percent-encoded UTM separators (`%26utm_source=...`). Spreadsheet, Slack, and CMS exports often encode `&` as `%26`, which glues later UTM pairs into the previous value; `parse_qsl` and GA4 split only on a raw `&`. Innocent `%26` inside a non-UTM value is not flagged.
- Added **CLK118** detection for UTM parameters placed in the URL fragment
  (`#...`). Browsers and GA4 never send the fragment to the server, so these
  links attribute as direct/none despite looking tracked. Innocent SPA hashes
  without UTM keys are not flagged.
