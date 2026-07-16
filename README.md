# creator-link-kit

Convention-as-code tooling for creator and influencer campaign links.
Define your UTM naming convention once, generate validated per-creator links
in bulk, then audit the links that actually shipped - before messy data ever
reaches your analytics.

* `youtube` vs `YouTube` vs `yt` in the same campaign → three separate rows in GA4
* one teammate's copy-pasted link with the wrong creator handle → silent mis-attribution
* 30 creators × 3 placements each → 90 links nobody wants to build by hand

`creator-link-kit` (CLI: `clk`) catches all of this offline, in seconds, with
zero dependencies and no data leaving your machine.

## What it does

| Command | Purpose |
| --- | --- |
| `clk init` | Write a starter convention file you can edit in two minutes |
| `clk build` | Build and validate a single campaign link |
| `clk batch` | Generate one validated link per row of a creator roster CSV |
| `clk audit` | Check shipped links (CSV or text export) against the convention |
| `clk validate-config` | Sanity-check the convention file itself |

Everything is driven by one small JSON (or YAML) convention file that lives in
your repo, so "how we tag links" stops being a wiki page nobody reads and
becomes something CI can enforce.

## Why not...

* **Google's Campaign URL Builder** - great for one link, but it can't store a
  convention, can't validate values against your allowlists, and can't do 90
  links at once.
* **A shared spreadsheet** - works until someone freestyles a value, duplicates
  a row, or copies the wrong creator's link. (See `RESEARCH.md` - this is the
  default pain of every team we found discussing UTM governance.)
* **Paid governance SaaS** (UTM.io, Improvado, …) - solves this and much more,
  for a subscription. This tool covers the 80% that agencies and small teams
  actually need, free and offline.
* **`utm-governance-linter`** (the closest OSS project) - audit-only.
  `creator-link-kit` also *generates* links (single and roster-scale batch)
  with per-creator templating, near-miss suggestions, and richer checks.

## Install

Requires Python 3.10+. No required dependencies.

```bash
pip install creator-link-kit          # once published to PyPI
pip install creator-link-kit[yaml]    # optional: YAML convention files
```

Or run from a clone:

```bash
git clone https://github.com/NeilFoxAgency/creator-link-kit
cd creator-link-kit
pip install -e .
```

## Quickstart

```bash
# 1. Write a starter convention and edit sources, mediums, campaign pattern, base_url
clk init creator-links.json

# 2. Generate a validated link for every creator in your roster
clk batch --config creator-links.json --roster roster.csv --out links.csv

# 3. Later, audit what actually shipped (export from your tracker, link-in-bio, GA4…)
clk audit --config creator-links.json --input live_links.csv
```

A roster row is just CSV:

```csv
handle,name,platform,landing_url
glowwithgreta,Greta Mohr,youtube,
thebudgetbeauty,Priya Nair,instagram,
labcoatlucie,Lucie Novak,youtube,https://shop.example.com/glowdrop?bundle=pro
```

`clk batch` turns it into per-creator links that all follow the same
convention - existing query params like `?bundle=pro` are preserved:

```csv
handle,name,platform,landing_url,generated_url,status,issues
glowwithgreta,Greta Mohr,youtube,,https://shop.example.com/glowdrop?utm_source=youtube&utm_medium=influencer&utm_campaign=glowdrop-launch&utm_content=glowwithgreta,ok,
```

And `clk audit` finds the real-world mess:

```text
  row 2: https://shop.example.com/glowdrop?utm_source=YouTube&utm_medium=...
    ERROR  CLK105 ERROR: [utm_source] 'YouTube' only differs from an allowed value
           by case; analytics tools treat these as different values (did you mean 'youtube'?)
  row 4: https://shop.example.com/glowdrop?utm_source=tiktok&utm_campaign=...
    ERROR  CLK102 ERROR: [utm_medium] required parameter is missing
  Duplicate links:
    ERROR  CLK005 ERROR: row 5 duplicates row 1: same destination and UTM values,
           so reporting splits between rows

  8 links checked: 3 clean, 3 error(s), 3 warning(s)
```

Try it on the included demo data:

```bash
clk batch --config examples/convention.json --roster examples/roster.csv
clk audit --config examples/convention.json --input examples/live_links.csv
```

## The convention file

```json
{
  "version": 1,
  "base_url": "https://shop.example.com/glowdrop",
  "owned_domains": ["example.com"],
  "casing": "lowercase",
  "max_value_length": 80,
  "required": ["utm_source", "utm_medium", "utm_campaign"],
  "parameters": {
    "utm_source":   { "allowed": ["youtube", "instagram", "tiktok", "newsletter"] },
    "utm_medium":   { "allowed": ["influencer", "social", "email", "cpc"] },
    "utm_campaign": { "pattern": "^[a-z0-9][a-z0-9-]{2,48}$" },
    "utm_content":  { "pattern": "^[a-z0-9][a-z0-9._-]{0,63}$" }
  },
  "defaults": { "utm_medium": "influencer" },
  "batch": {
    "param_map": {
      "utm_source": "{platform}",
      "utm_medium": "influencer",
      "utm_campaign": "glowdrop-launch",
      "utm_content": "{handle}"
    },
    "url_column": "landing_url"
  }
}
```

| Key | Meaning |
| --- | --- |
| `base_url` | Default destination when a roster row has no URL of its own |
| `owned_domains` | Your properties. Audit warns when a tagged link points anywhere else (typo, expired redirect, wrong property) |
| `casing` | `lowercase` (recommended) or `any` |
| `max_value_length` | Per-value character limit |
| `required` | Parameters every link must carry |
| `parameters` | Per-parameter rules: `allowed` (exact list) and/or `pattern` (regex) |
| `defaults` | Values pre-filled by `build`/`batch` (e.g. medium is always `influencer`) |
| `batch.param_map` | Templates per parameter; `{column}` pulls from the roster CSV |
| `batch.url_column` | Roster column holding a per-row landing URL (optional) |

YAML works too: name the file `*.yaml` and install the `[yaml]` extra.

## Rule codes

Errors break or fragment attribution. Warnings are worth a look but don't fail
an audit unless `--strict` is passed.

| Code | Severity | Caught problem |
| --- | --- | --- |
| CLK001 | error | URL can't be parsed |
| CLK002 | warning | plain `http` instead of `https` |
| CLK003 | warning | destination outside your `owned_domains` |
| CLK004 | warning | no UTM parameters at all (unattributed traffic) |
| CLK005 | error | duplicate link (same destination + UTM values as an earlier row) |
| CLK101 | warning | `utm_*` parameter with no governing rule |
| CLK102 | error | required parameter missing |
| CLK103 | error | parameter key repeated in the query string (double tagging) |
| CLK104 | error | value not in the allowlist (with closest-match suggestion) |
| CLK105 | error | value differs from an allowlisted value only by case |
| CLK106 | error | value fails its regex pattern |
| CLK107 | warning | uppercase value under a lowercase convention |
| CLK108 | error | value over the length limit |
| CLK109 | error | empty value |

## Exit codes (CI-friendly)

| Code | Meaning |
| --- | --- |
| 0 | success - audit found no errors (warnings allowed unless `--strict`) |
| 1 | validation failed - bad link, failing batch rows, or audit errors |
| 2 | operational error - missing file, invalid config, bad arguments |

Example: block merging a campaign tracker update that breaks the convention.

```yaml
- name: Audit shipped creator links
  run: |
    pip install creator-link-kit
    clk audit --config creator-links.json --input data/live_links.csv --strict
```

## Privacy

The tool is fully offline: no network calls, no analytics, no telemetry, no
link-shortener APIs. Your creator roster and campaign URLs never leave your
machine. See `SECURITY.md`.

## Roadmap

* QR code export for YouTube end screens and packaging inserts
* Optional HTML audit report for sharing with clients
* `utm_id` (GA4 campaign ID) governance helpers
* A GitHub Action wrapper for one-line CI audits

Ideas and use cases welcome - see `CONTRIBUTING.md`.

## License

MIT - see `LICENSE`.
