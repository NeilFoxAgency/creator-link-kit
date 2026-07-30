# Security

## Offline guarantee

Creator Link Kit makes no network requests, includes no telemetry, and does not
send campaign URLs or creator roster data anywhere. YAML parsing is optional;
the default JSON workflow has no runtime dependencies.

## Public repository data boundary

This repository is public and must contain only code, documentation, synthetic
examples, naming conventions, and non-secret test fixtures.

Never commit:

- API keys, OAuth credentials, passwords, webhook secrets, or private keys
- `.env` files or provider configuration containing credentials
- merchant exports, order records, refunds, conversion events, or payment data
- customer names, email addresses, postal addresses, or other personal data
- private client reports, analytics exports, or confidential commercial terms
- active merchant discount codes or unpublished campaign QR assets

The link-specification serializer uses an explicit identifier whitelist:
`brand_id`, `campaign_id`, `creator_id`, and `placement_id`. It does not copy
unrelated roster columns into JSON specifications.

Batch CSV output still preserves the input roster columns for compatibility.
Operators are responsible for keeping sensitive source rosters, generated
links, discount-code exports, JSONL specifications, and QR assets outside the
repository. Use a private working directory and a private service for live
campaign data.

## Spreadsheet-safe CSV exports

Roster fields and audited URLs can contain untrusted text. When Creator Link Kit
writes CSV output, string cells beginning with spreadsheet formula trigger
characters (`=`, `+`, `-`, `@`, tab, carriage return, or newline) are prefixed
with an apostrophe. Excel, Google Sheets, and LibreOffice then display the value
as text instead of evaluating it as a formula. In-memory rows and JSON, text, or
HTML reports are not modified.

## URL authority checks

Link building and auditing reject URLs with malformed ports or embedded
username/password credentials. Production mode separately rejects destinations
outside the configured owned domains.

## Provider integrations

Do not add Dub, Short.io, commerce-platform, analytics-platform, or other hosted
provider credentials and network clients to this public package. Implement the
`LinkProvider` protocol in a separate private service with secrets management,
access controls, webhook verification, and audit logging.

## Reporting a vulnerability

Open a private GitHub security advisory. Do not post credentials, live campaign
URLs, client data, or reproduction data containing personal information in a
public issue.
