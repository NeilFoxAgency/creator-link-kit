# Research: why this tool exists

Date of research: 2026-07-17
Method: web search across Reddit, GitHub repositories, marketing-ops
publications, and analytics documentation. Paraphrases are our own; quotes are
short and attributed.

## The problem

Teams running creator/influencer campaigns need **unique, consistently tagged
links per creator** to attribute traffic and sales. In practice, tagging is
done by hand across spreadsheets and chat threads, and inconsistencies
(`YouTube` vs `youtube` vs `yt`) silently fragment analytics data. Existing
free tools build one link at a time and enforce nothing; governance features
are locked inside paid SaaS.

## Evidence from public discussions

Multiple substantial threads with many distinct participants describe the same
recurring need. (Thread titles, vote/comment counts, and short snippets as
surfaced by Reddit search on 2026-07-17; full thread pages blocked automated
access, so paraphrases rely on the visible snippets.)

1. **r/GoogleAnalytics - "How do you deal with inconsistent UTM naming in
   GA4?"** (68 comments)
   <https://www.reddit.com/r/GoogleAnalytics/comments/1sjp3xg/how_do_you_deal_with_inconsistent_utm_naming_in/>
   Top snippet: "Scalable companies all implement a UTM governance process
   (via a template or spreadsheet) where the values are locked." - i.e. the
   accepted answer is *governance*, today typically a fragile spreadsheet.

2. **r/PPC - "How do you keep UTMs consistent when running multiple
   campaigns?"** (44 comments)
   <https://www.reddit.com/r/PPC/comments/1sjp2b7/how_do_you_keep_utms_consistent_when_running/>
   Top snippet: "What actually works is having one UTM naming system and not
   letting platforms or team members freestyle it."

3. **r/analytics - "UTM naming patterns that hold up after 12+ months in
   production. What broke and what didn't."** (15 comments)
   <https://www.reddit.com/r/analytics/> (thread surfaced in the same search)
   Practitioners comparing long-term naming conventions and their failure
   modes - evidence the problem persists even for mature teams.

4. **r/GoogleAnalytics - "Need advice on scalable UTM structure for Paid
   Social (Meta, LinkedIn & TikTok Ads) + GA4"** (19 comments)
   <https://www.reddit.com/r/GoogleAnalytics/comments/1t72yyf/need_advice_on_scalable_utm_structure_for_paid/>
   Snippet: "worth standardizing naming conventions early because once
   multiple people start touching campaigns the reporting debt piles up fast."

Independent practitioner publications describing the same pain:

5. Attrk, *UTM Parameters Explained: A Creator's Guide* (2026) - naming
   inconsistency fragments sources; creators/agencies pay a "spreadsheet tax"
   of 5–10 minutes per link; inconsistent UTMs are "worse than no UTMs."
   <https://attrk.com/en/blog/utm-parameters-creators-guide>

6. Improvado, *UTM tracking best practices* - "Inconsistent Capitalization and
   Separators … GA4 treats each variation as a separate value"; recommends
   "automated validation" to "prevent rogue UTMs."
   <https://improvado.io/blog/advanced-utm-tracking-best-practices>

7. Second Stage, *Steam Tracking Fundamentals* - "The most common mistake
   teams make is inconsistent naming… your reports fragment"; recommends
   generating links with tooling instead of by hand.
   <https://secondstage.io/academy/steam-marketing/steam-tracking-fundamentals>

8. InfluenceFlow, *UTM Tracking for Influencer Links* (2026) - per-influencer
   links are the standard; "Managing UTM parameters across dozens of
   influencers and campaigns manually is exhausting"; batch generation is
   offered only inside their hosted platform.
   <https://influenceflow.io/resources/utm-tracking-for-influencer-links-the-complete-2026-guide/>

9. Plain English, *The Revenue-First Influencer Campaign Stack* (2026) -
   common mistakes that "ruin the stack": inconsistent naming, shared codes,
   no leakage monitoring; recommends one code/link convention per creator.
   <https://plainenglish.io/marketing/the-revenue-first-influencer-campaign-stack-utm-codes-post-purchase-survey>

## Existing solutions scanned (2026-07-17, GitHub search)

| Project | What it does | Gap for this use case |
| --- | --- | --- |
| Google Campaign URL Builder (web) | Builds one UTM link at a time | No convention storage, no validation, no bulk, no audit |
| `abhi-agnihotri/utm-governance-linter` (0★, single commit, 2026-04) | CLI that lints a CSV of URLs against a YAML taxonomy | Audit-only: no link generation, no roster templating, no near-miss suggestions |
| `sdras/devex-utm-builder`, `kkoutoup/UTM-Link-Builder`, `bhuvanbalasubramanian/utmbuilder` (≤10★) | Single-page web form builders | One link at a time; no governance or audit |
| `reatlat/wp-campaign-url-builder` (17★) | WordPress plugin builder | WP-only, no batch/audit |
| UTM.io / Improvado / InfluenceFlow (SaaS) | Hosted governance, batch generation, approvals | Paid, hosted, requires accounts/data sharing; overkill for small teams |

**Differentiator:** `creator-link-kit` covers the full loop - define the
convention as code, *generate* validated per-creator links at roster scale,
then *audit* what shipped - offline, dependency-free, CI-friendly, and free.
No existing free tool combines generation + governance + audit.

## Intended users

* Agencies running YouTube/creator partnerships for consumer brands
  (per-creator links across campaigns and placements)
* In-house marketers at small brands working with multiple creators
* Creators managing their own brand deals across platforms
* Marketing-ops folks who want convention enforcement in CI

## Non-goals confirmed by research

* No link shortener (platform trust issues; out of scope)
* No scraping or personal-data collection (not needed for the job)
* No hosted dashboard (that's the SaaS territory we're deliberately avoiding)
