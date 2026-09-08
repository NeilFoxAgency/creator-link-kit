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

See the rule-code table for CLK119: percent-encoded UTM separators (`%26`)
that glue later UTM pairs into an earlier value so GA4 never splits them.

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
git clone https://github.com/NeilFoxAgency/creator-link-kit
cd creator-link-kit
pip install -e .
```

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
| `CLK112` | error | Value contains an unresolved template placeholder or macro |
| `CLK113` | error | Value is whitespace-only or has leading/trailing whitespace |
| `CLK114` | error | Query key looks like a misspelled UTM parameter name |
| `CLK115` | error | Value is a reserved or placeholder string (`null`, `n/a`, `test`, …) |
| `CLK116` | error | One `utm_content` is paired with multiple campaigns or destinations |
| `CLK117` | error | Query string still contains HTML entities (`&amp;`, `&#38;`, …) so UTM pairs are not split |
| `CLK118` | error | UTM parameters appear in the URL fragment (`#...`); browsers and GA4 never send them |
| `CLK119` | error | A later UTM pair is glued into an earlier value via `%26` / embedded `&utm_`; GA4 never splits it |

The full usage guide, convention schema, GitHub Action inputs, security
boundary, and v0.2 migration notes live on `main`. This branch only adds CLK119
to the published rule table; merge after `links.py` lands.

## License

MIT. See `LICENSE`.
