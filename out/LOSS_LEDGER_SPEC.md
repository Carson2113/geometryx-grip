# Realised Loss Ledger — Specification v0.1

**Status:** draft spec, not built. **Author:** Geometryx. **Date:** 24 August 2026.
**One-line:** a descriptive ZIP- and metro-level record of climate losses that *actually happened*, built only from dated federal transaction records.

---

## 1. Why this and not a hazard score

GRIP's E8 module measured realised NFIP flood loss against FEMA's modelled expected annual loss on the same cross-section. Realised loss won.

| Test (3-yr house price growth, momentum-controlled) | Result |
|---|---|
| Realised flood loss per capita + modelled NRI expected annual loss, together | realised **t = −2.918**; modelled NRI **t = −0.896 (insignificant)** |
| Realised loss, controlling for actual Treasury FIO homeowners premium | **t = −2.129**, premium **t = −5.379**, both correctly signed |
| Realised loss, 7 robustness cuts (drop top 5% / top 10% of loss burden; drop the 12 highest-loss metros by name; 10-yr and 30-yr windows; claim *frequency* instead of dollars) | correctly signed and significant in **all 7**; weakest **t = −2.017** |
| Modelled NRI expected annual loss vs. population growth | **t = +3.341, wrong sign** — people move *toward* higher modelled risk |

The mechanism is why this holds: a paid NFIP claim is a dollar amount settled on a dated loss and never restated. NRI's expected annual loss is a 2025 model output, so its value at any past date is a retrospective construct. Competitors display the modelled score. This ledger displays what was paid.

**Limits that must travel with every use.** Effect is on prices, not migration (realised loss vs. population: t = −0.53). Magnitude is modest, ~0.4pp of 3-yr HPI per standard deviation. The signal is conditional on momentum — in a raw quartile sort high-loss metros grew slightly *faster* (4.88% vs 4.57%). And neither NFIP series proxies a homeowners premium (r² 0.10 and 0.18 against FIO, below the 0.25 pre-registered floor; flood price is *negatively* correlated with homeowners premium at −0.32). This ledger describes loss history. It does not estimate what anyone will pay.

## 2. Sources — all US Government works, public domain

| Source | Endpoint / path | Grain | Coverage |
|---|---|---|---|
| NFIP redacted claims | `https://www.fema.gov/api/open/v3/NfipClaims` | property, `countyCode` + ZIP, `dateOfLoss` | 2.72M records, loss years from 1978 |
| Disaster declarations | `https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries` | county-level `designatedArea`, incident dates | 1953– |
| NOAA Storm Events | `https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/` | county FIPS, event, damage estimate | 77 yearly files, 1950–2026 |

**Verified 24 Aug 2026:** v3 `NfipClaims` returns `dateOfLoss`, `countyCode`, `ratedFloodZone`, `amountPaidOnBuildingClaim`. **Live risk:** the v2 `FimaNfipClaims` endpoint is **deprecated effective 2026-10-15** — build on v3 only. Storm Events filenames embed a *changing* creation date (`StormEvents_details-ftp_v1.0_d{YYYY}_c{YYYYMMDD}.csv.gz`), so the directory must be listed at runtime; never hard-code a filename.

Excluded: HUD-USPS vacancy (registration-restricted), Zillow/Redfin (licensed). NOAA damage estimates are NWS field estimates, not settled transactions — carry them as context only, never as the loss measure.

## 3. Fields

Per ZIP and per CBSA, as of a stated snapshot date:

- `paid_claims_n` — count of paid flood claims, 10/20/30-yr windows
- `paid_loss_total`, `paid_loss_per_capita` — building + contents, nominal and CPI-deflated
- `claim_frequency_per_10k` — the dollar-free variant that survived robustness
- `largest_single_event_loss` and its date
- `years_since_last_paid_claim`
- `disaster_declarations_n`, `most_recent_declaration` (type, date)
- `flood_zone_mix` — share of claims by `ratedFloodZone`
- `coverage_flag` — suppressed, sparse (<10 claims), or reportable

## 4. Build steps

1. Page v3 `NfipClaims` with `$select` limited to the fields above; store raw JSONL by loss year.
2. Map `countyCode` → CBSA using the existing GRIP delineation registry (`grip/sources/cbsa.py`), honouring the vintage rule: never assign a newer delineation to an older origin.
3. Aggregate to ZIP and CBSA. Deflate with a public CPI series. Suppress any cell under 10 claims.
4. Join declarations and Storm Events counts by county FIPS, then roll up.
5. Emit one Parquet per grain plus a manifest recording source URLs, retrieval timestamps, row counts, and a SHA-256 per file.

## 5. The vintage snapshot — do this first

OpenFEMA serves only the *current* file with no archived vintages. That single fact is why E8's features are Class B and ungradeable: no as-of-origin snapshot can be demonstrated.

Fix it going forward. A monthly job that stores a hashed copy of the claims extract and the declarations file, with its retrieval date, creates a versioned history of a federal series that is published only as "current." In twelve months that is an asset nobody else holds, and the Class B problem dissolves for every origin after the archive starts. Cost is a scheduled task plus object storage. **Start this before building anything else — the clock only runs once it is on.**

## 6. Product use and copy rules

Intended surface: the insurance conversation. "This ZIP has *N* paid flood claims over 20 years, median payout $*X*, largest single event $*Y* in *YEAR*, last federally declared flood incident *YEAR*." Factual, checkable, and it makes an introduction more valuable without touching the composite score.

**Permitted:** past tense, counted, sourced, with the snapshot date and window shown. **Forbidden:** any forward-looking phrasing — "will", "predicts", "expected", "risk score", "future" — and any use in a migration or Rising/Stable/Declining label. This layer is deliberately descriptive so that it carries no durability claim to defend. If HPI figures are ever shown alongside it, the FHFA disclaimer applies: *This product uses FHFA Data but is neither endorsed nor certified by FHFA.*

## 7. Acceptance tests

- Total paid claims and total paid dollars reconcile to an independent recount within 0.1%.
- No cell with fewer than 10 claims is exposed.
- County→CBSA mapping loses under 1% of claim dollars to unmapped counties; unmapped residual is reported, not silently dropped.
- Manifest hashes reproduce on a re-run against the same snapshot.
- A grep of rendered copy finds zero forward-looking terms.

## 8. Out of scope

Any physical weather or climate projection model. Any use of this layer as a migration predictor — the population result does not support it. Any premium estimate derived from NFIP figures. Re-fitting the five-pillar composite.

## 9. Effort and sequencing

Snapshot job: ~1 hour, do it this week. Ledger build: 2–3 days, **after** the counsel memo lands, since that determines what may be said about it. The counsel brief and `metro_select` instrumentation keep priority for the week of 24 August.

---

*Evidence: `out/nfip_calibration_20260823T205336Z.json` (E8, pre-registered at commit `6ca77bbf`, release `v1.5.0-prereg`). E8 is a descriptive measurement exercise, not a graded forecast.*
