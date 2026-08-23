# E7: FEMA NRI expected annual loss as a premium proxy

**Status: DESCRIPTIVE -- NOT A GRADED FORECAST**

Generated 2026-08-23T16:50:05+00:00. Source file `nri_calibration_20260823T165005Z.json`.

The NRI release read here was published 2025-12-18 and FEMA serves one mutable layer, so it is not vintage-legal for any scorable origin. Independently, the first NRI release was 2020-10, so no archived vintage could reach origins before 2021 -- two of the thirteen graded h=3 origins and none at h=5. This is a measurement exercise about a feature, not a prediction.

## Why this was attempted

E6 found that the pre-registered negative sign on insurance cost is real on house prices when measured with actual Treasury FIO premiums (-0.005234 per standard deviation, t = -6.82), and that the graded shock `premium_shock_40pct` fails because it perturbs `hpi_vol`, a house-price volatility term standing in for insurance cost. FIO cannot repair that: published 2025-01-16, it is never simultaneously vintage-legal and scorable. E7 asks whether FEMA's National Risk Index can carry the same signal from a source that is free, federal and published annually.

The candidate feature is `eal_rate = EAL_VALB / BUILDVALUE`: modelled expected annual building loss per dollar of building exposure, summed over eighteen hazards. In actuarial terms it is a pure premium rate, and it is the closest free multi-peril analogue to a homeowners rate.

## The National Risk Index is no longer distributed as a file

Before any statistics: FEMA has removed the NRI bulk download infrastructure. Verified 2026-08-23, the historical download path 302s to the Resilience Analysis and Planning Tool page, the S3 bucket that served it returns `NoSuchBucket`, and the National Risk Index does not appear among the 49 datasets in the OpenFEMA catalogue. The surviving first-party distribution is FEMA's own ArcGIS Online organisation, which is what this adapter reads.

That endpoint serves **one mutable layer**, currently the December 2025 Release (`modified` 2025-12-18), 3,232 counties. FEMA overwrites it at each release, so no content hash can be pinned and no earlier vintage can be requested. `grip/sources/nri.py` records the row count, release label and retrieval date instead, and declares this as a deviation rather than hiding it.

## E7a: does the proxy track what people actually pay?

Regression of the FIO log median premium per policy on the log NRI loss rate, 380 metros. An elasticity of 1.0 would mean premium scales one-for-one with modelled loss.

| Specification | Pearson r | R² | Elasticity | t |
|---|---|---|---|---|
| Pooled | 0.363 | **0.132** | 0.262 | +6.50 |
| Within Census division | 0.389 | 0.151 | 0.277 | +6.27 |

The relationship is real and strongly significant, and it is weak. The free proxy explains **13.2%** of the cross-metro variation in what homeowners pay. The elasticity of **0.26** means a metro with twice the modelled loss rate pays roughly a fifth more, not twice as much — consistent with premium being dominated by rebuild cost, regulatory rate suppression, expense loading and non-modelled water damage, none of which NRI measures.

## E7b: does it reproduce the E6 outcome coefficients?

The E6 specification exactly — demeaned within Census division, momentum controlled, HC1 standard errors, predictors standardised so a coefficient is per standard deviation — with the loss rate substituted for the premium.

### House-price growth (`y_hpi`), n = 353

| Predictor | β per SD | t | Sign |
|---|---|---|---|
| `eal_rate_log` | -0.002928 | -2.801 | as pre-registered |
| `hpi_g5` | -0.002996 | -3.004 | n/a |

E6 measured this with real premiums at -0.005234 (t = -6.82).

Top against bottom loss-rate quartile, no controls: **3.753%** a year against **6.291%**, gap **-2.538 pp** (89 against 89 metros) — the pre-registered direction.

### Population growth (`y_pop`), n = 380

| Predictor | β per SD | t | Sign |
|---|---|---|---|
| `eal_rate_log` | +0.000652 | +2.047 | inverted |
| `pop_g3` | +0.004598 | +9.955 | n/a |

E6 measured this with real premiums at +0.000720 (t = +2.12).

Top against bottom loss-rate quartile, no controls: **0.893%** a year against **0.622%**, gap **+0.271 pp** (95 against 95 metros) — inverted.

## E7c: does it survive the premium it is meant to replace?

This is the decisive test. If the loss rate matters only through premium, it is a clean if noisy substitute. If it carries an independent coefficient, it is measuring something else and calling it a premium proxy would be wrong.

### House-price growth, both terms, n = 353

| Predictor | β per SD | t | Sign |
|---|---|---|---|
| `eal_rate_log` | -0.000793 | -0.832 | as pre-registered |
| `premium_log_2022` | -0.004922 | -6.235 | as pre-registered |
| `hpi_g5` | -0.002500 | -2.611 | n/a |

### Population growth, both terms, n = 380

| Predictor | β per SD | t | Sign |
|---|---|---|---|
| `eal_rate_log` | +0.000386 | +1.055 | inverted |
| `premium_log_2022` | +0.000676 | +1.692 | inverted |
| `pop_g3` | +0.004523 | +9.911 | n/a |

## Hazard composition and regional conditionality

Splitting building EAL into wildfire, flood and wind shares asks whether one peril carries the signal. Dropping the South Atlantic, East South Central and West South Central divisions is the objection E6 answered for the premium.

### House-price growth

| Predictor | β per SD | t | Sign |
|---|---|---|---|
| `wfir_share` | -0.000594 | -0.810 | n/a |
| `flood_share` | -0.000178 | -0.145 | n/a |
| `wind_share` | -0.003660 | -2.661 | n/a |
| `hpi_g5` | -0.002114 | -2.121 | n/a |
| `eal_rate_log` (ex-South, n = 207) | -0.000218 | -0.207 | as pre-registered |

### Population growth

| Predictor | β per SD | t | Sign |
|---|---|---|---|
| `wfir_share` | -0.000202 | -0.712 | n/a |
| `flood_share` | -0.001303 | -2.483 | n/a |
| `wind_share` | +0.000422 | +0.782 | n/a |
| `pop_g3` | +0.004402 | +10.162 | n/a |
| `eal_rate_log` (ex-South, n = 224) | -0.000177 | -0.489 | as pre-registered |

## Verdict

| Test | Result |
|---|---|
| Tracks actual premium (R² ≥ 0.25) | **no** |
| Reproduces the E6 price sign at \|t\| ≥ 2 | **yes** |
| Magnitude relative to E6 | 0.56× |
| Eligible as a graded predictor | **no** |
| Recommended as the premium replacement | **no** |

### What this settles

**NRI is directionally right and quantitatively insufficient.** It reproduces both E6 signs — negative on house prices, inverted on population — which is real corroboration that E6 measured a mechanism and not an artefact of the FIO file. But it recovers only 56% of the E6 price coefficient, and in the horse race its price coefficient collapses to insignificance while the premium keeps essentially all of its own. NRI is a noisy partial measurement of the same quantity, adding nothing once the premium is present. It is a substitute of last resort, not a replacement.

**Wind, not wildfire, carries the price signal.** In the hazard-share decomposition the wind share is the only significant term on prices. Wildfire is insignificant on both targets, which is worth stating plainly because wildfire dominates the public narrative about insurance withdrawal.

**The regional conditionality is the same as E6's.** Outside the three Southern divisions both coefficients fall to approximately zero. Whatever this mechanism is, it is a Sun Belt phenomenon, and a single national coefficient is the wrong specification for it.

### The structural finding, which is the important one

NRI fails the vintage lock twice, and the second failure is not FEMA's fault. The retrievable release is a 2025 publication, so it is illegal before origin 2026 and unscorable at h=3 until 2029 — the FIO trap exactly. But even a perfectly archived set of vintages would not help. The first NRI release was October 2020, so the earliest origin any vintage can serve is 2021. The graded origins run 2010-2020 at h=5 and 2010-2022 at h=3. An archived NRI would contribute **two origins out of thirteen at h=3, and none at h=5.**

Generalise that and it is a property of the protocol rather than of any dataset: **a vintage lock over a thirteen-origin backtest cannot admit a feature born in 2020, however good the feature is.** Anything to be graded across the full panel had to exist, in a form fixed at the time, in or before 2009. Every young climate-risk product — and almost all of them are young — is structurally out-of-panel and stays diagnostic until the panel itself moves forward. This is the cost of refusing to backdate, and it is worth paying, but it has to be stated rather than discovered repeatedly.

So the premium proxy has to be found among series with pre-2009 history. The candidate that survives that filter is the NFIP redacted policy file in OpenFEMA (`NfipPolicies` v3, 74.3 million records), which carries `totalInsurancePremiumOfThePolicy`, `fullRiskPremium` and `policyEffectiveDate` and therefore supports an actual average premium per county-year with genuine pre-2009 history. Its weakness is the mirror image of NRI's: it is a real price rather than a model, but it is flood-only and federally rated rather than multi-peril and market-rated. That is the next adapter.

## Declared deviations

- Mutable source. FEMA overwrites one ArcGIS layer per release, so no content hash can be pinned and no earlier vintage can be requested. Row count, release label and retrieval timestamp are recorded instead.
- EAL is a modelled climatology, not a realisation. It is built from decades of historical hazard frequency and severity, so it is close to time-invariant and cannot express a change in risk pricing between two adjacent origins.
- Building exposure denominator. EAL_VALB is measured against BUILDVALUE, FEMA's estimate of replacement cost, which is not the insured value and not the FIO policy base. The ratio is therefore a rate on a different denominator than a premium per policy.
- County to metro aggregation is exposure-weighted, so a metro's rate is dominated by its highest-value county. This is the correct weighting for a loss cost but it discards within-metro dispersion.
- EAL omits the two perils that drive most homeowners rate filings in the hardest markets: it has no fire-following-wind term, and its flood components are riverine and coastal inundation, not the non-modelled water damage that dominates claim frequency.

## Sources

- FEMA National Risk Index Counties, ArcGIS item `39485e8035d446a5bff03259508ae355`, December 2025 Release — https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0
- National Risk Index methodology — https://www.fema.gov/flood-maps/products-tools/national-risk-index
- Treasury FIO, Analyses of U.S. Homeowners Insurance Markets 2018-2022 — https://home.treasury.gov/news/press-releases/jy2791
- FHFA House Price Index, metro annual — https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv
- Census Population Estimates Program — https://www2.census.gov/programs-surveys/popest/datasets/
- OpenFEMA NFIP Redacted Policies v3 — https://www.fema.gov/openfema-data-page/nfip-redacted-policies-v3
- ICPSR/DataLumos deposit of a 2025 NRI release — https://doi.org/10.3886/E218382V1

This product uses FHFA Data but is neither endorsed nor certified by FHFA.
