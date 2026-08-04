# creator-link-kit

Convention-as-code tooling for creator and influencer campaign links.

Define a UTM naming convention once, generate validated links for each creator
placement, emit a machine-readable provenance record, and audit the links that
actually shipped before attribution data reaches analytics.

`creator-link-kit` is deliberately a deterministic, offline library and CLI. It
does not shorten links, collect clicks, connect to commerce platforms, or store
conversion data. A private attribution service can consume its provider-neutral
models and link specifications, then call a managed link provider without
putting credentials or client data in this public package.

## What v0.2 adds

- governed `utm_id` campaign identifiers and cross-link consistency checks
- stable `placement_id` values as the recommended `utm_content`
- standard `brand_id`, `campaign_id`, `creator_id`, and `placement_id` roster
  columns
- batch-level duplicate `placement_id` rejection
- production mode, where an unapproved destination domain is a hard error
- JSON link specifications with destinations, IDs, config version, a
  deterministic configuration fingerprint, and audit results
- provider-neutral request, response, and adapter protocol models
- optional placement-specific discount-code generation with pattern and
  case-insensitive uniqueness checks
- optional offline SVG/PNG QR export, named by `placement_id` when available
- malformed-port and embedded-credential URL rejection
- spreadsheet-safe CSV exports for untrusted roster and audit values
- escaped, self-contained HTML audit reports
- a reusable GitHub Action for one-line CI audits
- explicit public-package data boundaries for secrets and client information

## Why placement IDs matter

A creator can publish more than one sponsored video. The creator handle alone
therefore cannot identify a specific placement.

Use one immutable `placement_id` for every sponsored asset:

```text
brand_id       = brd-glowdrop
campaign_id    = cmp-glowdrop-launch
creator_id     = crt-glowwithgreta
placement_id   = plc-glowdrop-greta-video-01
```

Three videos from one creator should have one `creator_id` and three different
`placement_id` values. The starter convention maps `campaign_id` to `utm_id`
and `placement_id` to `utm_content`.

## Commands

| Command | Purpose |
| --- | --- |
| `clk init` | Write a production-oriented starter convention |
| `clk build` | Build one validated link or JSON link specification |
| `clk batch` | Generate one governed link and specification per roster row |
| `clk audit` | Check shipped links against the convention |
| `clk qr` | Export SVG or PNG QR codes using the optional `[qr]` extra |
| `clk validate-config` | Validate the convention file itself |

## Install

Requires Python 3.10 or newer. The core package has no runtime dependencies.

```bash
pip install creator-link-kit
pip install creator-link-kit[yaml]  # optional YAML convention files
pip install creator-link-kit[qr]    # optional offline QR export
```

Or run from a clone:

```bash
git clone https://github.com/NeilFoxAgency/creator-link-kit
cd creator-link-kit
pip install -e .
```

## Quickstart

Create and edit a convention:

```bash
clk init creator-links.json
```

The generated file uses `mode: production`. Replace the example `base_url` and
`owned_domains` before generating real links. In production mode, the base URL
and every per-row destination must use an approved domain.

Create a roster:

```csv
brand_id,campaign_id,creator_id,placement_id,handle,name,platform,landing_url
brd-glowdrop,cmp-glowdrop-launch,crt-greta,plc-greta-video-01,glowwithgreta,Greta Mohr,youtube,
brd-glowdrop,cmp-glowdrop-launch,crt-greta,plc-greta-video-02,glowwithgreta,Greta Mohr,youtube,https://shop.example.com/product?bundle=pro
brd-glowdrop,cmp-glowdrop-launch,crt-priya,plc-priya-video-01,thebudgetbeauty,Priya Nair,youtube,
```

Generate a CSV plus one JSON link specification per line:

```bash
clk batch \
  --config creator-links.json \
  --roster roster.csv \
  --out links.csv \
  --spec-out link-specs.jsonl
```

Optional QR export remains offline and uses placement IDs for filenames when
that column is present:

```bash
pip install 'creator-link-kit[qr]'
clk qr --input links.csv --out-dir qr-codes --format svg
```

The output CSV preserves the roster columns and adds:

- `generated_url`
- `discount_code` when `batch.discount_code_template` is configured
- `link_spec`
- `status`
- `issues`

The v0.2 starter generates the discount code from `placement_id`, keeping link
and code attribution at the same video-level grain. A duplicate non-empty
`placement_id` causes every row carrying that duplicate to fail. Reusing a
`creator_id` is expected and allowed. Discount-code uniqueness is checked
case-insensitively across otherwise valid rows.

## Build one link

The ID arguments can supply `utm_id` and `utm_content` automatically when those
parameters are governed by the convention:

```bash
clk build \
  --config creator-links.json \
  --param utm_source=youtube \
  --param utm_campaign=cmp-glowdrop-launch \
  --brand-id brd-glowdrop \
  --campaign-id cmp-glowdrop-launch \
  --creator-id crt-greta \
  --placement-id plc-greta-video-01
```

Use JSON output when another tool or agent needs a durable specification:

```bash
clk build \
  --config creator-links.json \
  --param utm_source=youtube \
  --param utm_campaign=cmp-glowdrop-launch \
  --brand-id brd-glowdrop \
  --campaign-id cmp-glowdrop-launch \
  --creator-id crt-greta \
  --placement-id plc-greta-video-01 \
  --format json
```

The result has a stable, provider-neutral shape:

```json
{
  "schema_version": 1,
  "config_version": 1,
  "config_fingerprint": "14f12541e5132116a6dc06cf0788fa92bed06fccc5ac9815cdde4f698e51b80f",
  "original_destination": "https://shop.example.com/product",
  "generated_destination": "https://shop.example.com/product?utm_medium=influencer&utm_source=youtube&utm_campaign=cmp-glowdrop-launch&utm_id=cmp-glowdrop-launch&utm_content=plc-greta-video-01",
  "ids": {
    "brand_id": "brd-glowdrop",
    "campaign_id": "cmp-glowdrop-launch",
    "creator_id": "crt-greta",
    "placement_id": "plc-greta-video-01"
  },
  "audit": {
    "valid": true,
    "errors": 0,
    "warnings": 0,
    "issues": []
  }
}
```

The exact query-parameter order is not part of the specification contract.
Consumers should parse the URL rather than compare its raw string ordering.

`config_fingerprint` is a deterministic SHA-256 digest of the normalized
convention, including its rules, defaults, domain policy, batch mappings, and
mode. It identifies which policy produced a specification but is not a
signature, authentication token, or substitute for storing the convention
itself. `schema_version` remains `1`; the fingerprint is an additive field.

## Convention file

The starter convention is equivalent to:

```json
{
  "version": 1,
  "base_url": "https://shop.example.com/product",
  "owned_domains": ["example.com"],
  "mode": "production",
  "casing": "lowercase",
  "max_value_length": 100,
  "required": [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_id",
    "utm_content"
  ],
  "parameters": {
    "utm_source": {
      "allowed": ["youtube", "instagram", "tiktok", "newsletter"]
    },
    "utm_medium": {
      "allowed": ["influencer", "social", "email", "cpc"]
    },
    "utm_campaign": {
      "pattern": "^[a-z0-9][a-z0-9-]{2,48}$"
    },
    "utm_id": {
      "pattern": "^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,99}$"
    },
    "utm_content": {
      "pattern": "^[a-z0-9][a-z0-9._-]{0,63}$"
    }
  },
  "defaults": {
    "utm_medium": "influencer"
  },
  "batch": {
    "param_map": {
      "utm_source": "{platform}",
      "utm_medium": "influencer",
      "utm_campaign": "{campaign_id}",
      "utm_id": "{campaign_id}",
      "utm_content": "{placement_id}"
    },
    "url_column": "landing_url",
    "id_columns": {
      "brand_id": "brand_id",
      "campaign_id": "campaign_id",
      "creator_id": "creator_id",
      "placement_id": "placement_id"
    },
    "discount_code_template": "{placement_id}",
    "discount_code_pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$",
    "discount_code_column": "discount_code"
  }
}
```

| Key | Meaning |
| --- | --- |
| `base_url` | Default destination when a row has no per-placement URL |
| `owned_domains` | Approved destination roots; subdomains are accepted |
| `mode` | `production` makes external destinations errors; `development` warns |
| `casing` | `lowercase` or `any` |
| `max_value_length` | Maximum length of each governed UTM value |
| `required` | Parameters every generated or audited link must contain |
| `parameters` | Per-parameter allowlists and regular-expression rules |
| `defaults` | Values filled before validation |
| `batch.param_map` | Templates that read values from each roster row |
| `batch.url_column` | Optional per-row destination column |
| `batch.id_columns` | Mapping from standard ID names to roster columns |
| `batch.discount_code_template` | Optional roster template for placement codes |
| `batch.discount_code_pattern` | Optional regex for generated discount codes |
| `batch.discount_code_column` | Output column name; defaults to `discount_code` |

The four recognized identifier names are fixed intentionally:
`brand_id`, `campaign_id`, `creator_id`, and `placement_id`. This whitelist keeps
arbitrary roster data out of link specifications.

YAML also works when the optional dependency is installed.

## Production and development modes

In `development` mode, a destination outside `owned_domains` produces `CLK003`
as a warning. This retains the behavior of v0.1 configurations that do not have
a `mode` key.

In `production` mode:

- at least one owned domain is required
- `base_url` must use an owned domain
- any generated or audited external destination produces `CLK003` as an error
- link generation refuses to emit the invalid URL

Domain checks accept the listed domain and its subdomains. For example,
`example.com` approves both `example.com` and `shop.example.com`, but not
`example.net`.

## Discount codes

Discount-code generation is optional and entirely offline. The starter uses:

```json
{
  "discount_code_template": "{placement_id}",
  "discount_code_pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$",
  "discount_code_column": "discount_code"
}
```

Templates use the same `{column}` syntax as `batch.param_map`. Empty values,
missing columns, pattern failures, and duplicate codes mark only the affected
row as an error. Code uniqueness is case-insensitive, so `VIDEO15` and
`video15` collide.

Using `placement_id` in the starter is deliberate: one creator can publish
multiple sponsored videos, and a creator-wide code cannot distinguish those
placements. The generated CSV can be used by a private service or merchant
integration to create the codes in the brand's commerce platform. This package
does not make that network call.

## QR code export

Install the optional dependency and export from a batch CSV or explicit URLs:

```bash
pip install 'creator-link-kit[qr]'
clk qr --input links.csv --out-dir qr-codes --format svg
clk qr --url 'https://shop.example.com/product?...' --out-dir qr-codes
```

SVG is the default; PNG is also supported. Filenames prefer `placement_id`,
then creator-oriented columns, and are sanitized against path traversal and
case-insensitive collisions. These are output labels only; a handle or
`utm_content` value from a legacy file is never treated as a stable placement
identity. URL validation rejects non-HTTP(S), malformed-port, and credentialed
URLs. QR generation stays offline.

## Provider-neutral integration

The public package exposes models but no network client:

```python
from creator_link_kit import (
    LinkIdentifiers,
    LinkProvisionRequest,
    build_link_specification,
    load_convention,
)

convention = load_convention("creator-links.json")
ids = LinkIdentifiers(
    brand_id="brd-glowdrop",
    campaign_id="cmp-glowdrop-launch",
    creator_id="crt-greta",
    placement_id="plc-greta-video-01",
)
specification = build_link_specification(
    "https://shop.example.com/product",
    {
        "utm_source": "youtube",
        "utm_campaign": "cmp-glowdrop-launch",
    },
    convention,
    identifiers=ids,
)
request = LinkProvisionRequest.from_specification(
    specification,
    slug="greta-video-01",
    tags=("youtube", "cmp-glowdrop-launch"),
)
```

A private service can implement the `LinkProvider` protocol and translate
`LinkProvisionRequest` into Dub, Short.io, or another provider's API. Provider
credentials, webhook secrets, merchant integrations, orders, conversions, and
customer records remain outside this repository.

See `docs/PRIVATE_SERVICE_INTEGRATION.md` for the intended boundary.

## Audit shipped links

```bash
clk audit \
  --config creator-links.json \
  --input live_links.csv \
  --format json \
  --out audit.json
```

For CSV input, the CLI automatically looks for common URL columns including
`generated_url`, `url`, `link`, `landing_url`, and `destination_url`. Use
`--url-column` to override detection.

Warnings do not fail the command unless `--strict` is supplied. Errors always
produce exit code 1. Across an audit set, `CLK110` rejects one `utm_campaign`
paired with multiple `utm_id` values, and `CLK111` rejects one `utm_id` reused
for multiple campaign names.

Audit output supports `text`, `json`, `csv`, and `html`. HTML reports are
self-contained, escape all dynamic content, and can be shared offline:

```bash
clk audit \
  --config creator-links.json \
  --input live_links.csv \
  --format html \
  --out audit.html
```

CSV exports neutralize cells that begin with spreadsheet formula trigger
characters. In-memory rows and JSON, text, and HTML output are not modified.

## GitHub Action

A reusable composite action is included so another repository can enforce the
same convention without hand-writing installation and CLI steps:

```yaml
- uses: actions/checkout@v4

- name: Audit shipped creator links
  uses: NeilFoxAgency/creator-link-kit@main
  with:
    config: creator-links.json
    input: data/live_links.csv
    format: html
    strict: "true"
    # url-column: generated_url
```

| Input | Required | Default | Purpose |
| --- | --- | --- | --- |
| `config` | yes | - | Convention file path |
| `input` | yes | - | CSV or text file containing links |
| `url-column` | no | auto | CSV column containing the URL |
| `format` | no | `text` | `text`, `json`, `csv`, or `html` |
| `strict` | no | `false` | Treat warnings as failures |
| `python-version` | no | `3.12` | Python runtime for the action |
| `version` | no | local or latest | Package version to install |

The action uses the same exit codes as the CLI. The included example workflow
is at `.github/workflows/example-audit.yml`.

## Rule codes

| Code | Severity | Caught problem |
| --- | --- | --- |
| `CLK001` | error | URL cannot be parsed or is not absolute HTTP(S) |
| `CLK002` | warning | URL uses HTTP instead of HTTPS |
| `CLK003` | mode-dependent | Destination is outside `owned_domains` |
| `CLK004` | warning | URL has no UTM parameters |
| `CLK005` | error | Duplicate destination and UTM values in an audit |
| `CLK101` | warning | UTM parameter has no governing rule |
| `CLK102` | error | Required parameter is missing |
| `CLK103` | error | Parameter appears more than once |
| `CLK104` | error | Value is not in its allowlist |
| `CLK105` | error | Value differs from an allowed value only by case |
| `CLK106` | error | Value does not match its required pattern |
| `CLK107` | warning | Value is uppercase under a lowercase convention |
| `CLK108` | error | Value exceeds the configured length |
| `CLK109` | error | Value is empty |
| `CLK110` | error | One `utm_campaign` is paired with multiple `utm_id` values |
| `CLK111` | error | One `utm_id` is paired with multiple campaign names |
| `CLK114` | error | Query key looks like a misspelled UTM parameter name |

Batch duplicate-placement failures are reported in the row's `issues` field
before URL generation and do not receive a `CLK` code because they concern the
roster, not a URL.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Validation, audit, or batch-row failures |
| `2` | Configuration, file, argument, or operational error |

## Migration from v0.1

Existing version-1 convention files remain valid.

- A missing `mode` defaults to `development`, preserving the earlier external
  domain warning behavior.
- A missing `batch.id_columns` remains valid.
- Legacy batch files without v0.2 ID columns or discount-code configuration
  still load, build links, and emit specifications.
- Arbitrary governed `utm_*` parameters still work.
- To adopt the v0.2 agency convention, add `utm_id`, map `utm_content` to a
  stable placement ID, add the standard ID columns, and switch to production
  mode after confirming `owned_domains`.
- Existing configurations may keep `utm_id` optional. The v0.2 starter requires
  it so every generated placement carries a stable campaign identifier.
- Discount-code and QR features remain optional. The starter's code template is
  placement-specific; remove `discount_code_template` to disable code output.

The package release is `0.2.0`; the convention schema remains version `1`
because these additions are backward-compatible optional fields.

## Security and data boundary

This repository may contain code, synthetic examples, naming conventions, and
non-secret campaign identifiers. It must not contain:

- API keys, OAuth tokens, passwords, webhook secrets, or private keys
- merchant exports, orders, refunds, conversion events, or payment data
- customer names, emails, addresses, or other personal data
- private brand analytics or client reports
- live merchant discount codes or unpublished QR assets

Link specifications copy only the four approved identifier fields. They do not
copy arbitrary roster columns. A legacy creator handle in `utm_content` is not
promoted to `placement_id`. CSV files written by the CLI also neutralize
spreadsheet-formula prefixes. URLs with malformed ports or embedded credentials
are rejected during build and audit. See `SECURITY.md` and
`docs/PRIVATE_SERVICE_INTEGRATION.md` for the full policy.

## Privacy

The package makes no network requests and includes no analytics or telemetry.
All generation and auditing happens locally.

## License

MIT. See `LICENSE`.
