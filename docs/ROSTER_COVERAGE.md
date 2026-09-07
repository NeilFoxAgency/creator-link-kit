# Roster coverage checks

`clk audit --roster roster.csv` compares shipped links against the planned
placement IDs in a campaign roster.

| Code | Severity | Meaning |
| --- | --- | --- |
| `CLK201` | error | A roster `placement_id` never appears as `utm_content` in the audited links |
| `CLK202` | warning | A shipped `utm_content` value is not on the roster |

Matching is case-insensitive when the convention uses `casing: lowercase`.
Blank roster placement cells are ignored. Duplicate roster IDs are collapsed
to the first occurrence.

This is an optional check. Audits without `--roster` keep the previous
behavior. Extra live or test links are warnings so operators can confirm them
with `--strict` when desired.

Example:

```bash
clk audit \
  --config creator-links.json \
  --input live_descriptions.txt \
  --roster roster.csv
```

The roster is read locally. No network calls are made and no creator contact
data is required beyond the identifier columns already used by `clk batch`.
