# What GRIP-1 Is Missing

**Date:** 23 August 2026
**Status:** diagnosis and proposed attempt 2. No result in this memo has been graded, and the
central prediction has deliberately *not* been run — see "The one thing I refused to do."

---

## Summary

Four graded cells, nothing certified, and two of three pre-registered shocks returning the wrong
sign in every cell. E9 removed the last comfortable explanation by showing the wrong signs survive
a metro fixed effect in 38 of 38 leave-one-origin-out refits. The natural reading is that the
theory is wrong. That reading is premature, and this memo argues it is wrong for a reason that has
nothing to do with the model.

Two measurements, both computed from predictors and price history only:

| Measurement | Value |
|---|---|
| `corr(hpi_gap, hpi_g5)` pooled | **+0.909** |
| `corr(hpi_gap, hpi_g5)` range across all ten origins | **+0.762 to +0.966** |
| `corr(hpi_vol, 2000s peak-to-trough crash depth)` at origin 2010 | **−0.947** |
| same, origins 2010 through 2018 | **−0.790 to −0.947** |
| same, origins 2019 and 2020 | **−0.499, −0.521** |
| `corr(hpi_vol, 2000–2006 boom)` pooled | **+0.623** |

Reproduce with `run_feature_audit.py`; raw output in `out/feature_audit.json`.

`hpi_gap` is labelled an affordability headwind. It is defined as deviation from a metro's own
fifteen-year log-price trend, and it correlates **+0.91** with that metro's own five-year price
growth. It is not a valuation measure with a momentum problem. It is momentum, measured twice.

`hpi_vol` is labelled a stand-in for insurance cost. It correlates **−0.95** with how far a metro
fell from its 2000s peak. It is not a risk measure. It is a register of which metros blew up in
2008 — Phoenix, Las Vegas, the Florida and Inland Empire markets — and those are the metros that
rebounded hardest over the grading window. The correlation decays to −0.50 by origin 2020 as the
crash leaves the fifteen-year window, which is itself confirmation that this is a window artifact
rather than a property of the feature.

So both failing shocks reduce to one fact: **the graded panel is a single episode.** Origins 2010
through 2020, with five-year outcomes, observe one monotone recovery from one crash. Within that
window, high momentum and deep prior collapse both predict strong subsequent growth, because
recovery is what the window contains. `rate_shock_200bp` asks the model to say that metros priced
furthest above trend will grow more slowly. In this sample that is a request to predict the
opposite of what happened, and no estimator can grant it. E9's rejection was correct and its
conclusion was too narrow: the problem is not the estimator, and it is not really the features
either. It is that the features and the sample window are collinear with each other.

This has an uncomfortable corollary that should be published: **the shock gate as written cannot be
passed by a correct model on this sample.** A gate that no correct model can pass is broken, not
strict. That is a defect in GRIP-1, disclosed by GRIP-1, and it belongs in the protocol.

---

## What is missing, in order of leverage

### 1. Regimes, not rows. Fifteen additional origins are already in our cache.

The FHFA metro index in `cache/` runs **1975 to 2025 across 410 metros** — we have been grading
against the last decade of a fifty-year file. Feasibility at a fifteen-year trend window and an
eight-year minimum:

| Candidate origins | Count | Median metros with h=5 outcome |
|---|---|---|
| 2010–2021 (current window) | 12 | 410 |
| 1995–2009 (addable) | **15** | **406** |

Adding 1995–2009 more than doubles the origins, and it adds the one thing the current window
structurally lacks: origins that sit *before* a bust rather than after one. Origins 2002 through
2006 have outcomes running into 2007–2011, when over-trend metros did in fact revert, violently.
That is the only sample in which the registered mean-reversion sign can be identified at all.

Cost for the house-price target: zero new data.

Blockers for the population target, both surmountable:
- PEP vintages in `grip/sources/pep.py` start at 2001. Census does publish the **original 1990s
  county series based on the 1990 Census and explicitly not revised to Census 2000**
  ([1990s county estimates](https://www.census.gov/data/tables/time-series/demo/popest/1990s-county.html)),
  which is vintage-legal under our rule. The later
  [1990–2000 intercensal files](https://www.census.gov/data/datasets/time-series/demo/popest/intercensal-1990-2000-state-and-county-characteristics.html)
  are smoothed against the 2000 Census and must not be used for backtesting.
- CBSA delineations in `grip/sources/cbsa.py` start at 2009. Before 2003 the units were MSAs and
  PMSAs, a genuine discontinuity rather than a missing file. Handle it by grading on FHFA's own
  metro codes with a boundary-comparability filter, the way `boundary_comparable` already works.

### 2. Give the valuation gap a denominator. BEA income, 1969–2024, free.

Deviation from a metro's own price trend is definitionally momentum, which is why the correlation
is +0.91. Affordability requires something to be affordable *relative to*. BEA's CAINC1 county
file carries personal income, population and per-capita personal income for **1969 through 2024**
as a no-registration bulk download ([apps.bea.gov/regional/zip/CAINC1.zip](https://apps.bea.gov/regional/zip/CAINC1.zip)),
which aggregates to our CBSAs with the crosswalk we already build. A price-to-income gap is not
mechanically momentum, because the denominator moves on its own. Metro-level series need a free
BEA API key ([signup](https://apps.bea.gov/API/signup/)); the county bulk file avoids that
entirely and is the better fit since we aggregate counties anyway.

This is the single feature change most likely to let the registered negative sign appear honestly.

### 3. Stop forecasting population. Forecast net domestic migration.

E9's largest number was that removing metro identity destroys 83% of the population fit against 6%
for prices. The most likely explanation is natural increase: births minus deaths is close to
deterministic five years out and is a persistent metro trait, because it is mostly age structure.
Grading total population growth therefore awards most of its credit for demographic momentum we
never forecast, while the migration signal we actually sell is a minority of the variance — and
climate risk and insurance cost have no plausible channel to births.

The components are already inside the file we download. County-level
`BIRTHS`, `DEATHS`, `NATURALCHG`, `INTERNATIONALMIG`, `DOMESTICMIG` and `NETMIG` are confirmed in
the `co-est` ALLDATA series from **2000 onward** ([CO-EST2024 layout](https://www2.census.gov/programs-surveys/popest/technical-documentation/file-layouts/2020-2024/CO-EST2024-ALLDATA.pdf),
verified present in [co-est2009-alldata.csv](https://www2.census.gov/programs-surveys/popest/datasets/2000-2009/counties/totals/co-est2009-alldata.csv)).
The 1980s components file carries births and deaths with only a combined residual, so the clean
domestic/international split does not extend before 2000 — the migration target is available for
roughly twenty origins, not thirty.

Forecast the domestic net migration rate. It is the actual product question, it is the component a
climate or insurance mechanism could move, and it is free.

### 4. Go down to ZIP, because that is where the mechanism lives.

Flood and wildfire risk, and insurance pricing, operate at parcel and ZIP scale. Houston as a
single row is a mixture of floodplain and not. Averaging to 231 metros destroys precisely the
variation the mechanism runs through, and we then conclude the mechanism is absent. Verified free
and unregistered:

- **FHFA five-digit ZIP annual HPI from 1984** — [hpi_at_zip5.xlsx](https://www.fhfa.gov/hpi/download/annual/hpi_at_zip5.xlsx)
- FHFA county annual from 1986 — [hpi_at_county.xlsx](https://www.fhfa.gov/hpi/download/annual/hpi_at_county.xlsx)
- FHFA census tract annual — [hpi_at_tract.csv](https://www.fhfa.gov/hpi/download/annual/hpi_at_tract.csv)
- NFIP claims and policies already carry ZIP; NRI is tract and county

These are developmental, not seasonally adjusted, thin in low-transaction ZIPs, and often missing
before the mid-1980s — treat as Class B under Amendment 1, not Class A. The prize is a cross
section perhaps a hundred times larger, in the same ZIP-first shape as the insurance product, and
E9 already built the fixed-effects machinery needed to identify within-metro effects cleanly.

### 5. Replace perturbation shocks with a real natural experiment.

E9 established that an `exposed_only` shock response is arithmetically the fitted coefficient on
the perturbed feature. A ridge coefficient in a thirty-feature model is a partial correlation, so
the gate demands a causal sign from a machine that cannot produce one. The fix is an actual
experiment, and one exists.

**NFIP Risk Rating 2.0** repriced flood insurance by formula rather than by market forces, with
confirmed dates: new business **1 October 2021**, renewals **1 April 2022**, full implementation
**1 April 2023** ([FEMA Risk Rating 2.0](https://www.fema.gov/flood-insurance/risk-rating)). FEMA
publishes **ZIP-code-level premium-change breakdowns** for every state
([state profiles](https://www.fema.gov/flood-insurance/risk-rating/profiles); e.g.
[Georgia ZIP breakdown](https://www.fema.gov/sites/default/files/documents/fema_risk-rating-zip-breakdown-georgia_2025.xlsx),
[methodology narrative](https://www.fema.gov/sites/default/files/documents/fema_zip-level-narrative_04-2025.pdf)).
That is administratively imposed, cross-sectionally varying treatment intensity — about as close to
an instrument as this field offers. Difference-in-differences on premium-change intensity, outcome
being subsequent ZIP price and migration. Caveat: it is a one-time snapshot comparison, not a
premium time series, and ZIPs with fewer than five policyholders are suppressed.

Supporting event studies, both free:
[OpenFEMA disaster declarations](https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2)
(county FIPS reliable from 1964) and the
[NOAA Storm Events bulk files](https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/)
(county, event-level, with damage estimates, from 1950 — though pre-1996 coverage is thinner).

### 6. Get migration ground truth: IRS SOI county-to-county flows.

Origin–destination flows for filing-year pairs from **1990–1991 through 2021–2022**, free
([IRS SOI migration data](https://www.irs.gov/statistics/soi-tax-stats-migration-data)). A gravity
model gives an expected flow; the residual is revealed preference, and it is a far better dependent
variable than a population level. Cells under ten returns are suppressed, and the series counts
filers rather than people.

### 7. Two sources to refuse, on our own rules

- **HUD-USPS address vacancy data.** I wanted this as the high-frequency migration indicator. HUD
  states that under its USPS agreement it can release the data only to governmental entities and
  registered non-profits ([HUD USPS datasets](https://www.huduser.gov/portal/datasets/usps.html)).
  We do not qualify. Do not use it.
- **Zillow ZHVI and Redfin market tracker.** Both are free to download without registration —
  Zillow metro ZHVI monthly from January 2000, Redfin metro from January 2012 — but they are
  licensed-with-attribution corporate data, not public-domain federal data
  ([Zillow Group public data terms](https://www.zillowgroup.com/developers/api/public-data/real-estate-metrics/)).
  Our standing rule is public-domain federal only. They cannot be graded Class A, and Zillow
  restates history each month, so any use requires archiving vintages at download time.

---

## The one thing I refused to do

I did not check whether extending the panel to 1995–2009 flips the sign of `hpi_gap`. That is
exactly the prediction PROTOCOL.md section 13 requires us to register before running, and looking
first would destroy the only thing that makes the answer worth anything. Everything measured above
is a property of the predictors, not of any relationship to an outcome.

## Proposed attempt 2, to be released results-free before it runs

Attempt 1 was rejected with the clause that attempt 2 must not be another estimator. This is not.
It is a data-scope and feature-definition change, and it is falsifiable.

- **P1.** With origins 1995–2009 added, the coefficient on `hpi_gap` for the house-price target
  turns negative in the pooled panel.
- **P2.** Replacing `hpi_gap` with a price-to-income gap built on BEA CAINC1 turns the coefficient
  negative even inside the current 2010–2020 window.
- **P3.** The coefficient on `hpi_vol` loses significance once 2000s crash depth is included as an
  explicit control, confirming it was proxying for the bust rather than for risk.
- **P4, power precondition.** Minimum metros per origin and minimum origins per cell declared in
  advance; failing it returns UNINFORMATIVE rather than a rejection.
- **Accept rule.** Stated in full before the run, as in attempt 1.
- **Published regardless of outcome:** the admission that the shock gate cannot be passed by a
  correct model on a single-episode sample, and what that means for the four standing NOT CERTIFIED
  verdicts.

If P1 and P2 both fail on a sample that contains two busts and a real affordability denominator,
the mean-reversion mechanism is dead and Geometryx should say so publicly and stop encoding it.
That is a result worth having either way, which is the point of the whole exercise.

---

*Data-availability claims in this memo were verified by direct fetch on 23 August 2026; see
`free_data_verification.md` for per-source verdicts and gotchas. This product uses FHFA Data but is
neither endorsed nor certified by FHFA.*
