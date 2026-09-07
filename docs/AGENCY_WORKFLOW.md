# Agency link preparation and delivery workflow

The public kit builds and audits destinations. It does **not** host redirects,
count clicks, create operational campaign records, or prove sales.

## Installation and first run

From a checkout of this repository, use Python 3.10 or newer:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m creator_link_kit.agency examples/agency-intake.json --output plan.json
```

The example is synthetic. Do not execute its requests against live operations.
The output path must not already exist. Validation failures return exit code 2
without writing a partial plan. Source files and generated campaign artifacts
must stay outside public Git repositories.

## Input contract

Use one authoritative campaign ID and a current `supabase_snapshot_version`.
Each placement has its own stable ID and a creator ID. The same creator may have
multiple placements. IDs are preserved, not lowercased or sanitized. Duplicate
and case-colliding placement IDs fail the entire batch.

`approved_domains` is a list of **exact ASCII DNS hosts**. Listing `example.com`
does not approve `shop.example.com` in this agency wrapper. Comparison ignores
case and one trailing dot. No wildcards, IP destinations, credentials, fragments,
non-default ports, HTTP, existing UTMs, common paid-ad click identifiers, hidden
characters, or common private query fields are accepted. A syntactically allowed
host is not evidence that the brand approved it. Confirm the actual landing page.

Canonical tags are `youtube`, `creator_sponsorship`, campaign ID for both
`utm_campaign` and `utm_id`, and placement ID for `utm_content`. Optional
`discount_code` and `slug` must be supplied approved values. No redeemable code
is generated from a creator name or placement ID.

## What the output means

Every row includes an audited link specification, deterministic configuration
fingerprint, and the exact arguments for the connected `create_campaign_link`
action. The plan has a deterministic SHA-256 fingerprint and status
`prepared_not_provisioned`. The destination passed to the service is the original,
untagged URL; the specification provides the expected tagged destination.

The plan fingerprint is not a digital signature or an approval. The intake's
snapshot version is operator-supplied evidence and is not authenticated offline.

## Operations Agent execution

1. Re-fetch the campaign and placements from the approved operational connector.
   Confirm source version, all four IDs, destination/domain/code approval, and the
   current shadow/live operating mode. Refresh the plan when the snapshot changed.
2. Execute each prepared request only with current write authorization. Do not
   create campaign/placement records in the attribution service to make a test pass.
3. Read back `list_campaign_links`. Verify every placement, creator, destination,
   expected UTM value, code and active delivery URL. An idempotent response with a
   different specification is a conflict, not success. Preserve completed link
   receipts if another placement fails; do not blindly replay an altered batch.
4. Check the delivery URL with HEAD and redirects disabled first. Confirm the
   exact Location and HTTPS destination, no auth challenge and no open redirect.
   Do not put UTMs on the short URL. A controlled GET test can create telemetry;
   isolate and label such tests rather than counting them as campaign results.
5. Give creators the verified delivery URL and approved code. At publication,
   check the actual video description, disclosure, destination and code. Store
   the video URL and evidence in the operational placement record.
6. Read campaign traffic for an explicit half-open UTC window (`since <= t < until`).
   Collect separately sourced cumulative platform snapshots and authoritative
   reconciled conversion evidence. Use the private service's `python -m reporting`
   for draft placement/creator/campaign reports. Missing evidence is not zero.

Delivery/QA, approximately day 7, and approximately day 30 are observation points,
not a reason to sum cumulative snapshots. Clicks do not establish sales. Codes
can spread beyond a video, and last-click attribution does not establish lift.
