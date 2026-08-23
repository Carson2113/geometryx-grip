# GRIP-1: Geometryx Relocation Intercomparison Protocol, version 1

**Status:** draft for public release. **Date:** August 2026. **Maintainer:** Geometryx.

GRIP is a public, reproducible protocol for grading forecasts of US metro
population and house-price movement, built entirely on public-domain federal
data. It is modelled directly on [AIMIP](https://allenai.org/blog/aimip), the
AI Model Intercomparison Project, which grades machine-learning climate
emulators against a fixed experimental design rather than against each authors'
own chosen benchmark ([AIMIP code](https://github.com/ai2cm/AIMIP),
[PCMDI hub](https://github.com/PCMDI/AI-MIP)).

The premise is deliberate. AIMIP's leverage does not come from owning the best
model; it comes from being the venue where models are graded in public, with
protocol deviations named. That position is available in relocation and
climate-insurance forecasting and nobody holds it. It also costs nothing to
occupy, which matters when the alternative moat, proprietary data, is priced
between $25,000 and six figures a year.

---

## 1. Scope and claims

GRIP grades two target families at the metro (CBSA) level:

| Target | Definition | Status |
|---|---|---|
| `y_pop` | Annualised population growth, base year to base+H | primary |
| `y_hpi` | Annualised FHFA HPI growth, base year to base+H | secondary |

Horizons H are 3 and 5 years. Both targets are graded **after within-region,
within-origin demeaning** (section 5), so a submission is scored on *relative*
movement among peer metros, never on the national cycle.

A model that passes GRIP is licensed to make **relative, ranked, ensemble**
claims about metro movement. It is not licensed to claim absolute forecasts of
price levels, migration counts, or insurance losses.

## 2. Input eligibility

Only sources that are public domain or explicitly resale-permissive may be used.
The reference implementation uses:

- [Census Population Estimates Program](https://www.census.gov/programs-surveys/popest.html), per vintage
- [Census Building Permits Survey](https://www.census.gov/construction/bps/), metro annual
- [FHFA House Price Index](https://www.fhfa.gov/data/hpi), metro quarterly
- [OMB/Census metro delineation files](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html)

**Banned inputs.** Any series whose terms of use restrict commercial
redistribution or model training. This specifically excludes FRED, whose June
2024 terms prohibit training any machine-learning model on its content, and
Redfin, which prohibits commercial use. Where a banned series is needed, it must
be re-sourced from the originating agency, not laundered through an aggregator.

**Banned features: clocks.** AIMIP excludes atmospheric CO2 as a model input
because its steady rise "could become a proxy for a clock" — a model can score
well by inferring *when* it is rather than *what is happening*. GRIP enforces the
housing analogue in `grip/leakage.py`. Any candidate feature whose
cross-sectional mean drifts monotonically across origin years (Spearman rho
against origin year, p < 0.05, with few sign flips) is flagged CLOCK_LEAK and
excluded from the fitted model. This is checked and published on every run, not
assumed.

This rule has teeth. In the first run of this harness, before within-origin
demeaning was applied, **all four price-derived features failed the clock
audit** — the 2010-2020 recovery was monotone enough to act as a date stamp. The
fix was to remove the era, not to remove the test.

## 3. Geography: boundary comparability

A metro that gained a county between two origin years is not the same object.
Comparing it across origins mixes a boundary revision into a growth signal.

GRIP therefore restricts every multi-origin comparison to CBSAs whose **exact
county set is identical across all delineation vintages in play**. Under the
2009 through 2020 vintages this yields **247 boundary-comparable metros**, of
which 217-245 survive the data-availability filters at any given origin.

Each origin year is assigned the most recent delineation published on or before
December 31 of that year. Census serves delineation files back to 2009, which
sets the earliest usable origin.

## 4. The vintage lock

This is the core of the protocol and the part most forecast evaluations get
wrong.

For origin year Y, **every predictor must be derivable from files published on or
before December 31 of Y.** Implementation:

- Information base year **B = Y − 1**.
- Population uses the PEP **vintage stack** — every vintage with reference year
  ≤ B, newest published value winning for each year. Vintage V is released in Q1
  of V+1, so V = Y − 1 is the newest legally available. There is no V2010 file
  (census year), which the stack absorbs; origin 2011 is consequently dropped
  from the 5-year panel rather than silently backfilled.
- Cross-decade lookback is permitted, because a forecaster standing in 2022
  genuinely held both the 2020s vintage and the frozen 2010s files.
- Targets are measured from B forward using the **latest** revision. This is
  legitimate for the same reason AIMIP grades against reanalysis: the forecaster
  is not asked to predict the revision, only the outcome.

Two vintage-lock assertions run on every panel and appear on the scorecard:
`max_pep_vintage_matches_base_year` and `delineation_not_from_future`.

**Frozen-percentile ban.** No feature may be expressed as a percentile computed
over a distribution that includes data after the origin. This is the single
error that most inflates a backtest, and it is the reason a prior Geometryx
point-in-time test saw only 62 of 199 metros clear a quality floor at origin 2010
versus 160 at origin 2015 — the floor was a 2026 percentile applied to 2010.
Where a "distance from normal" feature is wanted, compute it from the metro's own
history, as `hpi_gap` does.

### Declared deviations

AIMIP publishes deviations rather than hiding them; one entrant's checkpoint
contained 1.5 years of holdout and this was stated openly. GRIP requires the
same. Current deviations:

1. **FHFA HPI has no per-release vintage archive.** Index values are the current
   revision. Mitigated by using only lagged growth rates and own-history trend
   deviations, never cross-metro levels.
2. **Census BPS has no revision-vintage archive.** Mitigated by lagging permit
   counts a full year behind the base year (`permit_base = B − 1`).

## 5. Prescribed forcing: within-region, within-origin demeaning

AMIP-style experiments prescribe sea-surface temperature — the boundary
condition the model is not asked to predict — and grade only the atmospheric
response to it. GRIP prescribes the two things a metro model cannot forecast and
should not be credited for:

- the **era** (mortgage rates, the national cycle, the pandemic), and
- the **region** (Census division level effects).

Every feature and every target is demeaned within `(origin_year, division)`
cells with a minimum of 5 metros. The demeaned variable carries the `_wr` suffix
and is the only thing scored.

This is not a cosmetic choice. Prior Geometryx work measured that **79.8% of
metro growth variance is within Census divisions and 20.2% between**, and that
division dummies alone explained more variance (R² +0.152) than a five-pillar
composite score (R² +0.112). A model graded on undemeaned growth is largely being
graded on having correctly guessed the map.

## 6. Rolling origins

Two origin years is not a backtest. GRIP requires an **expanding-window,
strictly causal** evaluation: for each test origin, fit only on origins strictly
earlier, predict the test origin, never the reverse. Minimum 3 training origins.

The reference run scores **7 origins at H=5** (test origins 2014-2020) and
**8 origins at H=3** (2014-2022).

## 7. The mandatory baseline

Every submission is scored against **prior one-year within-region population
growth** (`pop_g1_wr`). Nothing else. It is one line of code, it is free, and in
prior Geometryx testing it beat the five-pillar composite in 8 of 8 cells.

A scorecard that does not report the baseline is invalid. Reporting a model's R²
without it is the single most common way a housing forecast is oversold.

## 8. Evaluation criteria

Mirroring AIMIP's E1-E5:

| ID | Criterion | Method |
|---|---|---|
| **E1** | Descriptive fit | In-sample R² and rank correlation. Reported, never sold. |
| **E2** | Out-of-sample skill | Spearman rho and R² at each rolling origin, with bootstrap 90% intervals |
| **E3** | Skill above baseline | **Paired** per-origin difference versus `pop_g1_wr` |
| **E4** | Coefficient stability | Sign and magnitude of each fitted coefficient across origins |
| **E5** | Shock plausibility | Pre-registered response signs under counterfactual shocks |

**E3 must be paired.** Comparing unpaired medians is not sufficient and can
invert the answer. In the reference run at H=3, the model's median Spearman
(0.753) exceeds the baseline's (0.746) while the baseline wins **7 of 8
origins**; the paired median gain is **−0.0162**. Only the paired statistic is
reported as the verdict.

### E5: the shock suite

AIMIP cannot observe a +4 K world, so it grades whether the *sign and structure*
of a model's response are physically plausible under prescribed perturbation.
Three entrants — ACE2.1, cBottle1.3 and MD-1.5 v0.9 — failed by implausibly
predicting cooling over land while their historical means looked fine.

Geometryx has the identical failure class already on record: the high
climate-risk quartile grew **faster** than the low-risk quartile (+1.10% vs
+0.78%), and the worst insurance-nonrenewal decile grew fastest (+1.57% vs
+0.51%). Under GRIP those become published diagnostics with pre-registered
expected signs.

Signs are declared **before** the shock is run. Current suite:

| Shock | Perturbation | Scope | Expected |
|---|---|---|---|
| `rate_shock_200bp` | valuation gap +1 sd on the most over-trend quartile | exposed only | relative decline |
| `premium_shock_40pct` | insurance-cost proxy +1 sd on high-hazard quartile | exposed only | relative decline |
| `momentum_reversal` | prior momentum −1 sd everywhere | uniform | rank compression, not reordering |

Two mechanics matter. Shocks must land **only on exposed metros**, because a
uniform additive shock to a linear model produces an identical response
everywhere and a differential of exactly zero — a null result that looks like a
failure. And uniform shocks must be graded on **rank stability** rather than on
response sign, for the same reason.

**A wrong sign bars a model from forward-looking claims regardless of its R².**

## 9. Ensembles, not point estimates

AIMIP requires a minimum 5-member ensemble, described as "enough to estimate
dispersiveness" — not enough to isolate the forced response. GRIP adopts the
same floor. A submission reporting a single number per metro is rejected. Every
published Geometryx figure derived from a GRIP-graded model must carry an
interval.

## 10. Submission format

A submission is a directory containing:

```
submission.json     model name, version, contact, declared deviations
predictions.csv     origin_year, cbsa_code, member, y_pred
sources.md          every input with URL, licence, retrieval date
```

`predictions.csv` must contain ≥5 members per (origin, metro). Any origin year
present in the file is graded; omitting hard origins is itself reported.

## 11. Reproducibility

The reference implementation caches every retrieved file and records a
`sha256` manifest at `cache/_manifest.json`. Requests are rate-limited to 2 per
second. A scorecard JSON is written per run with a UTC timestamp and is
immutable; `out/latest.json` points at the newest.

## 12. Why this is a moat and not a paper

You cannot backdate a public, timestamped forecast. Every quarter GRIP runs and
publishes, the record lengthens, and that record is not purchasable at any price.
A competitor with a $135,000 parcel licence still has no 2026 scorecard in 2029.

---

**Attribution.** This product uses FHFA Data but is neither endorsed nor
certified by FHFA. Population estimates, building permits and metro delineations
are US Census Bureau products in the public domain.
