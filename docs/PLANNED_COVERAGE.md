# Planned vs shipped link coverage (CLK206–CLK210)

Creator campaigns generate a governed CSV with `clk batch`, then later collect
the URLs that actually appeared in YouTube descriptions, briefs, or a live
export. Syntax audit alone cannot tell you whether every planned placement
shipped, or whether the live URL drifted off the generated destination.

## Usage

```bash
clk audit \
  --config creator-links.json \
  --input live_links.csv \
  --planned links.csv
```

`--planned` is optional. Audits without it behave exactly as before.

`--planned` accepts the same shapes as `--input`: a CSV with a URL column
(`generated_url`, `url`, `link`, `landing_url`, `destination_url`) or a text
file of absolute HTTP(S) URLs. Override the planned CSV column with
`--planned-url-column`.

## Rules

| Code | Severity | Meaning |
| --- | --- | --- |
| `CLK206` | error | A planned placement (`utm_content`) is missing from the shipped set, or a planned URL could not be parsed for comparison. |
| `CLK207` | error | The same placement shipped a different landing destination (scheme + host + path + non-UTM query). |
| `CLK208` | warning | The same placement shipped different `utm_source`, `utm_medium`, `utm_campaign`, or `utm_id` values. |
| `CLK209` | warning | A shipped `utm_content` was not in the planned set (extra test or leftover link). |
| `CLK210` | error | The planned file repeats the same `utm_content`. |

Matching follows the convention `casing` setting. Under `lowercase`,
`plc-Greta` and `plc-greta` are the same placement.

## What this does not do

- It does not prove a viewer clicked the link.
- It does not call GA4, YouTube, or a store API.
- It does not rewrite shipped URLs.
- It is not a substitute for CLK116 (one `utm_content` pointing at two
  destinations *inside* a single file). CLK207 compares planned vs shipped.

## Privacy

Comparison is offline. Use synthetic fixtures in this repository. Do not commit
live campaign CSVs.
