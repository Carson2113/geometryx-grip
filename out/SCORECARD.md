# GRIP-1 Scorecard

Geometryx Relocation Intercomparison Protocol, reference run. Every number below was produced by `run_backtest.py` against public-domain federal files under the vintage lock in `PROTOCOL.md`. No licensed data was used.

## Horizon 3 years

- Run started: `2026-08-23T15:35:42Z`
- Target: `y_pop_wr` (within-division, within-origin demeaned population growth)
- Origins in panel: [2010, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2022]
- Panel rows: 2687; median metros per origin: 245
- Mandatory baseline: `pop_g1_wr`

### Headline

| Metric | Model | Baseline |
|---|---|---|
| Median Spearman rho | 0.754 | 0.746 |
| Median out-of-sample R2 | 0.517 | 0.516 |
| Median top-quartile hit rate | 90.1% | 93.5% |

Paired, per-origin differences (model minus baseline). Unpaired medians
can flatter a model that loses on almost every origin, so these govern.

| Paired gain | Value |
|---|---|
| Median Spearman gain | -0.0162 |
| Median out-of-sample R2 gain | 0.0007 |
| Median hit-rate gain | -0.0138 |

**Origins where the model beat the baseline: 1/8.**

> Verdict: **NOT CERTIFIED for forward-looking claims.** The multi-feature model does not reliably beat prior one-year population growth. Under GRIP rule 8 this model may ship as a descriptive index only. Publishing it as a forecast would be the failure AIMIP was built to catch.

### E2/E3 Rolling-origin skill

Each row is a strictly causal test: fit on origins before the test origin, predict the test origin, never the reverse.

| Test origin | Metros | Model rho | 90% interval | Baseline rho | Model hit | Baseline hit | Beat baseline |
|---|---|---|---|---|---|---|---|
| 2014 | 228 | 0.723 | [0.644, 0.792] | 0.768 | 87.7% | 95.2% | no |
| 2015 | 228 | 0.788 | [0.723, 0.842] | 0.793 | 91.2% | 91.9% | no |
| 2016 | 230 | 0.869 | [0.833, 0.897] | 0.873 | 93.1% | 95.2% | no |
| 2017 | 221 | 0.835 | [0.790, 0.878] | 0.850 | 98.2% | 98.4% | no |
| 2018 | 221 | 0.651 | [0.567, 0.718] | 0.680 | 92.9% | 95.2% | no |
| 2019 | 221 | 0.665 | [0.585, 0.727] | 0.688 | 83.9% | 87.1% | no |
| 2020 | 217 | 0.648 | [0.568, 0.719] | 0.664 | 83.6% | 82.0% | no |
| 2022 | 215 | 0.785 | [0.721, 0.838] | 0.723 | 88.9% | 88.5% | yes |

### Ensemble and intervals

Every origin is scored from a block-bootstrap ensemble over origin years (minimum 19 members against a protocol floor of 5). The graded prediction is the ensemble mean.

| Ensemble metric | Value |
|---|---|
| Conforms to the member floor | yes |
| Share of individual members beating the baseline | 18.2% |
| Median single-fit Spearman rho, for comparison | 0.753 |
| Median member spread as a share of forecast error | 0.096 |
| Median 90% predictive interval width | 0.01485 |
| Median realised coverage of that interval | 90.7% |

> The 90% predictive interval is **conforming**: realised coverage 90.7% against a nominal 90%. This interval may be attached to published figures. Note that it is *wider* than the member spread by roughly an order of magnitude — member spread alone captures which model might have been fitted, not how wrong that model is about a given metro, and publishing it as a forecast interval would be narrow and wrong.

| Test origin | Members | Members beating baseline | Member rho range | 90% PI coverage |
|---|---|---|---|---|
| 2014 | 19 | 0/19 | [0.701, 0.734] | n/a (first scored origin) |
| 2015 | 20 | 9/20 | [0.723, 0.817] | 90.8% |
| 2016 | 20 | 0/20 | [0.842, 0.871] | 92.2% |
| 2017 | 20 | 0/20 | [0.824, 0.845] | 96.4% |
| 2018 | 20 | 0/20 | [0.634, 0.656] | 79.6% |
| 2019 | 20 | 0/20 | [0.636, 0.674] | 80.1% |
| 2020 | 20 | 0/20 | [0.630, 0.661] | 82.0% |
| 2022 | 20 | 20/20 | [0.743, 0.789] | 90.7% |

### CLOCK_LEAK audit

AIMIP banned CO2 as an input because its steady rise "could become a proxy for a clock." This is the housing analogue: any feature whose cross-sectional mean drifts monotonically across origins is dating the sample rather than ranking metros.

| Feature | Drift rho across origins | p | Sign flips | Verdict |
|---|---|---|---|---|
| `pop_g1_wr` | 0.137 | 0.689 | 4 | PASS |
| `pop_g3_wr` | -0.318 | 0.340 | 4 | PASS |
| `pop_accel_wr` | -0.255 | 0.450 | 7 | PASS |
| `hpi_g1_wr` | -0.082 | 0.811 | 3 | PASS |
| `hpi_g5_wr` | 0.409 | 0.211 | 6 | PASS |
| `hpi_gap_wr` | 0.314 | 0.346 | 7 | PASS |
| `hpi_vol_wr` | -0.382 | 0.247 | 7 | PASS |
| `permits_pc_wr` | 0.282 | 0.401 | 4 | PASS |
| `permits_g3_wr` | -0.345 | 0.328 | 3 | PASS |

Features excluded by the audit: none.

### E4 Coefficient stability

A feature whose sign flips across origins is not a mechanism, it is a fit artifact.

| Feature | Mean coef | Min | Max | Share positive | Verdict |
|---|---|---|---|---|---|
| `pop_g1_wr` | 0.00250 | 0.00240 | 0.00260 | 100.0% | STABLE |
| `pop_g3_wr` | 0.00170 | 0.00110 | 0.00210 | 100.0% | STABLE |
| `pop_accel_wr` | 0.00100 | 0.00080 | 0.00120 | 100.0% | STABLE |
| `hpi_g1_wr` | 0.00070 | 0.00040 | 0.00130 | 100.0% | STABLE |
| `hpi_g5_wr` | -0.00130 | -0.00210 | 0.00000 | 0.0% | STABLE |
| `hpi_gap_wr` | 0.00030 | -0.00130 | 0.00090 | 75.0% | SIGN-UNSTABLE |
| `hpi_vol_wr` | 0.00030 | -0.00020 | 0.00060 | 62.5% | SIGN-UNSTABLE |
| `permits_pc_wr` | 0.00170 | 0.00150 | 0.00180 | 100.0% | STABLE |
| `permits_g3_wr` | -0.00020 | -0.00060 | -0.00010 | 0.0% | STABLE |

### E5 Shock plausibility

There is no ground truth for a rate or premium shock, so these are graded on pre-registered sign, exactly as AIMIP grades the +2K/+4K sea-surface experiments. Wrong sign bars a model from forward-looking claims regardless of its R2.

| Shock | Graded on | Relative response | Expected sign | Observed | Verdict |
|---|---|---|---|---|---|
| `rate_shock_200bp` | response_sign | 0.000420 | -1 | 1 | IMPLAUSIBLE |
| `premium_shock_40pct` | response_sign | 0.000542 | -1 | 1 | IMPLAUSIBLE |
| `momentum_reversal` | rank_stability | -0.000000 | -1 | 0 | PLAUSIBLE |

- **`rate_shock_200bp` failed.** A uniform or positive response means the model carries no rate sensitivity at all.
- **`premium_shock_40pct` failed.** Wrong sign means the climate/insurance pillar is acting as a proxy for Sun Belt growth rather than for risk -- the exact inversion already measured (+1.57% vs +0.51%).

### Declared deviations

- Census BPS publishes no revision-vintage archive; annual permit totals are the current revision, not the as-of-origin revision. Mitigated by using counts lagged at least one full year before the origin.
- FHFA does not archive per-release vintages of the metro HPI, so index values are the current revision rather than the as-of-origin revision. Mitigated by using only lagged growth rates and own-history trend deviations, never levels compared across metros.

### Vintage-lock checks

- `max_pep_vintage_matches_base_year`: PASS (0 violations)
- `delineation_not_from_future`: PASS (0 violations)

## Horizon 5 years

- Run started: `2026-08-23T15:34:05Z`
- Target: `y_pop_wr` (within-division, within-origin demeaned population growth)
- Origins in panel: [2010, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]
- Panel rows: 2438; median metros per origin: 245
- Mandatory baseline: `pop_g1_wr`

### Headline

| Metric | Model | Baseline |
|---|---|---|
| Median Spearman rho | 0.744 | 0.759 |
| Median out-of-sample R2 | 0.569 | 0.577 |
| Median top-quartile hit rate | 91.4% | 90.3% |

Paired, per-origin differences (model minus baseline). Unpaired medians
can flatter a model that loses on almost every origin, so these govern.

| Paired gain | Value |
|---|---|
| Median Spearman gain | -0.0100 |
| Median out-of-sample R2 gain | 0.0172 |
| Median hit-rate gain | 0.0106 |

**Origins where the model beat the baseline: 3/7.**

> Verdict: **NOT CERTIFIED for forward-looking claims.** The multi-feature model does not reliably beat prior one-year population growth. Under GRIP rule 8 this model may ship as a descriptive index only. Publishing it as a forecast would be the failure AIMIP was built to catch.

### E2/E3 Rolling-origin skill

Each row is a strictly causal test: fit on origins before the test origin, predict the test origin, never the reverse.

| Test origin | Metros | Model rho | 90% interval | Baseline rho | Model hit | Baseline hit | Beat baseline |
|---|---|---|---|---|---|---|---|
| 2014 | 228 | 0.734 | [0.647, 0.800] | 0.715 | 86.0% | 83.9% | yes |
| 2015 | 228 | 0.799 | [0.742, 0.850] | 0.790 | 94.7% | 95.2% | yes |
| 2016 | 230 | 0.770 | [0.723, 0.816] | 0.759 | 91.4% | 90.3% | yes |
| 2017 | 221 | 0.714 | [0.651, 0.773] | 0.737 | 91.1% | 88.7% | no |
| 2018 | 217 | 0.728 | [0.656, 0.792] | 0.780 | 89.1% | 93.4% | no |
| 2019 | 217 | 0.747 | [0.677, 0.807] | 0.774 | 92.7% | 93.4% | no |
| 2020 | 217 | 0.744 | [0.685, 0.799] | 0.754 | 92.7% | 88.5% | no |

### Ensemble and intervals

Every origin is scored from a block-bootstrap ensemble over origin years (minimum 19 members against a protocol floor of 5). The graded prediction is the ensemble mean.

| Ensemble metric | Value |
|---|---|
| Conforms to the member floor | yes |
| Share of individual members beating the baseline | 35.2% |
| Median single-fit Spearman rho, for comparison | 0.742 |
| Median member spread as a share of forecast error | 0.102 |
| Median 90% predictive interval width | 0.01547 |
| Median realised coverage of that interval | 89.2% |

> The 90% predictive interval is **conforming**: realised coverage 89.2% against a nominal 90%. This interval may be attached to published figures. Note that it is *wider* than the member spread by roughly an order of magnitude — member spread alone captures which model might have been fitted, not how wrong that model is about a given metro, and publishing it as a forecast interval would be narrow and wrong.

| Test origin | Members | Members beating baseline | Member rho range | 90% PI coverage |
|---|---|---|---|---|
| 2014 | 19 | 17/19 | [0.712, 0.762] | n/a (first scored origin) |
| 2015 | 20 | 13/20 | [0.754, 0.810] | 90.8% |
| 2016 | 20 | 19/20 | [0.753, 0.774] | 83.0% |
| 2017 | 20 | 0/20 | [0.700, 0.724] | 88.7% |
| 2018 | 20 | 0/20 | [0.703, 0.735] | 88.9% |
| 2019 | 20 | 0/20 | [0.723, 0.763] | 90.8% |
| 2020 | 20 | 0/20 | [0.716, 0.753] | 89.4% |

### CLOCK_LEAK audit

AIMIP banned CO2 as an input because its steady rise "could become a proxy for a clock." This is the housing analogue: any feature whose cross-sectional mean drifts monotonically across origins is dating the sample rather than ranking metros.

| Feature | Drift rho across origins | p | Sign flips | Verdict |
|---|---|---|---|---|
| `pop_g1_wr` | 0.407 | 0.243 | 3 | PASS |
| `pop_accel_wr` | -0.079 | 0.829 | 6 | PASS |
| `hpi_g1_wr` | -0.273 | 0.446 | 4 | PASS |
| `hpi_g5_wr` | 0.079 | 0.829 | 5 | PASS |
| `hpi_gap_wr` | 0.085 | 0.815 | 7 | PASS |
| `hpi_vol_wr` | -0.273 | 0.446 | 7 | PASS |
| `permits_pc_wr` | 0.358 | 0.310 | 3 | PASS |
| `permits_g3_wr` | -0.383 | 0.308 | 3 | PASS |
| `pop_g3_wr` | -0.661 | 0.038 | 3 | WARN |

Features excluded by the audit: none.

### E4 Coefficient stability

A feature whose sign flips across origins is not a mechanism, it is a fit artifact.

| Feature | Mean coef | Min | Max | Share positive | Verdict |
|---|---|---|---|---|---|
| `pop_g1_wr` | 0.00230 | 0.00220 | 0.00240 | 100.0% | STABLE |
| `pop_g3_wr` | 0.00150 | 0.00090 | 0.00190 | 100.0% | STABLE |
| `pop_accel_wr` | 0.00110 | 0.00100 | 0.00120 | 100.0% | STABLE |
| `hpi_g1_wr` | 0.00020 | 0.00000 | 0.00060 | 71.4% | SIGN-UNSTABLE |
| `hpi_g5_wr` | -0.00210 | -0.00280 | -0.00140 | 0.0% | STABLE |
| `hpi_gap_wr` | 0.00110 | 0.00010 | 0.00170 | 100.0% | STABLE |
| `hpi_vol_wr` | 0.00050 | 0.00020 | 0.00080 | 100.0% | STABLE |
| `permits_pc_wr` | 0.00190 | 0.00170 | 0.00200 | 100.0% | STABLE |
| `permits_g3_wr` | -0.00050 | -0.00090 | -0.00030 | 0.0% | STABLE |

### E5 Shock plausibility

There is no ground truth for a rate or premium shock, so these are graded on pre-registered sign, exactly as AIMIP grades the +2K/+4K sea-surface experiments. Wrong sign bars a model from forward-looking claims regardless of its R2.

| Shock | Graded on | Relative response | Expected sign | Observed | Verdict |
|---|---|---|---|---|---|
| `rate_shock_200bp` | response_sign | 0.001116 | -1 | 1 | IMPLAUSIBLE |
| `premium_shock_40pct` | response_sign | 0.000557 | -1 | 1 | IMPLAUSIBLE |
| `momentum_reversal` | rank_stability | -0.000000 | -1 | 0 | PLAUSIBLE |

- **`rate_shock_200bp` failed.** A uniform or positive response means the model carries no rate sensitivity at all.
- **`premium_shock_40pct` failed.** Wrong sign means the climate/insurance pillar is acting as a proxy for Sun Belt growth rather than for risk -- the exact inversion already measured (+1.57% vs +0.51%).

### Declared deviations

- Census BPS publishes no revision-vintage archive; annual permit totals are the current revision, not the as-of-origin revision. Mitigated by using counts lagged at least one full year before the origin.
- FHFA does not archive per-release vintages of the metro HPI, so index values are the current revision rather than the as-of-origin revision. Mitigated by using only lagged growth rates and own-history trend deviations, never levels compared across metros.

### Vintage-lock checks

- `max_pep_vintage_matches_base_year`: PASS (0 violations)
- `delineation_not_from_future`: PASS (0 violations)

## Attribution

- This product uses FHFA Data but is neither endorsed nor certified by FHFA.
- Building permits: U.S. Census Bureau Building Permits Survey (public domain).
- Population estimates: U.S. Census Bureau Population Estimates Program (public domain).
- Metro delineations: OMB/U.S. Census Bureau delineation files (public domain).

Sources: [FHFA House Price Index](https://www.fhfa.gov/data/hpi), [Census Population Estimates](https://www.census.gov/programs-surveys/popest.html), [Census Building Permits Survey](https://www.census.gov/construction/bps/), [OMB/Census metro delineation files](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html). Protocol modelled on [AIMIP](https://allenai.org/blog/aimip) ([code](https://github.com/ai2cm/AIMIP), [PCMDI hub](https://github.com/PCMDI/AI-MIP)).