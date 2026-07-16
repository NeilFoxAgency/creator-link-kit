# Security

## Offline guarantee

Creator Link Kit makes no network requests, includes no telemetry, and does not
send campaign URLs or creator roster data anywhere. YAML parsing is optional;
the default JSON workflow has no runtime dependencies.

## Spreadsheet-safe CSV exports

Roster fields and audited URLs can contain untrusted text. When Creator Link Kit
writes CSV output, string cells beginning with spreadsheet formula trigger
characters (`=`, `+`, `-`, `@`, tab, carriage return, or newline) are prefixed
with an apostrophe. Excel, Google Sheets, and LibreOffice then display the value
as text instead of evaluating it as a formula. In-memory rows and JSON or text
reports are not modified.

## Reporting a vulnerability

Please open a private GitHub security advisory for this repository. Do not post
sensitive campaign data in a public issue.
