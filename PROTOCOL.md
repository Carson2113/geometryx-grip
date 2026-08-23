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

### Ineligible sources

A source is **ineligible**, not merely deviating, when no origin exists at which
it is both legal under the vintage lock and scorable. Ineligibility is a property
of the source and the protocol together, and it must be recorded in code rather
than in a footnote, because the temptation to make an exception is strongest for
exactly the datasets that are most valuable.

The first such source is the Treasury Federal Insurance Office Property and
Casualty Market Intelligence collection, the only public-domain nationwide record
of what homeowners actually pay for insurance. It was published 2025-01-16, so the
earliest origin it can serve is 2025; the shorter graded horizon needs a realised
2028 outcome. It is therefore out of the panel until 2028 at the earliest.

That its content describes 2018-2022 changes nothing. **The lock is on publication
date, not on the period described.** A file published after the outcomes it
describes embeds revision, selection and hindsight no matter which years appear in
its rows, and admitting it because the content looks old enough is precisely the
backdating the protocol exists to prevent. See `grip/sources/fio.py`,
`VINTAGE_VERDICT`.

An ineligible source may still be used for an out-of-panel diagnostic under
section 8.

### The minimum-history rule

There is a second, less obvious way to be ineligible, and it is a property of the
protocol rather than of any dataset.

A feature may enter the graded panel at origin Y only if a vintage of it existed,
in a form fixed at the time, on or before 31 December Y. It follows that a feature
first published in year P can serve no origin earlier than P + 1. The graded
origins run 2010-2020 at h=5 and 2010-2022 at h=3. Therefore:

> **A feature first published after 2009 cannot be graded across the full panel.
> A feature first published in year P contributes at most (2022 - P) of the
> thirteen h=5 origins and (2020 - P) of the eleven h=3 origins, and none of
> either once P reaches 2022 or 2020 respectively.**

This is the price of refusing to backdate, and the protocol pays it deliberately.
But it has a consequence worth stating in advance rather than rediscovering once
per adapter: **almost every climate-risk product in existence is younger than this
backtest**, and is therefore structurally out-of-panel. FEMA's National Risk Index,
first released October 2020, could serve two h=3 origins and no h=5 origin even if
every historical vintage were perfectly archived. See `grip/sources/nri.py`,
`VINTAGE_VERDICT`, and the E7 diagnostic.

Two consequences bind future work:

1. A candidate feature must be checked for **first publication date before**
   anything is measured with it. A feature that cannot reach 2010 is a diagnostic,
   whatever its correlation.
2. A young source may not be admitted by shortening the panel to fit it. The
   origin set is fixed by section 6 and changing it to accommodate a feature is
   the same offence as changing a sign after a failed run.

### Amendment 1: the source-vintage taxonomy

**Added 23 August 2026, after NRI failed E7 and before the NFIP series were
measured.** The order matters and is checkable in the commit history: this
amendment is published in a commit that precedes the commit containing any NFIP
result.

The minimum-history rule above collapses two different hazards into one test, and
the collapse is too coarse. The hazards are:

- **Value hindsight.** The number itself embeds information from after the origin
  it would serve. A modelled expected annual loss published in 2025 encodes 2025
  hazard science; a period aggregate computed once over 2018-2022 encodes the whole
  period. There is no date at which such a number was true, so there is no origin
  it can honestly serve.
- **Availability.** The number was fixed and correct at a date on or before the
  origin, and is never restated, but it was not publicly obtainable until later.

Value hindsight is fatal and always will be. Availability is a defect in the
realism of the backtest, which is a different and lesser thing. Sources are
therefore classified:

| Class | Definition | Status |
|---|---|---|
| **A** | An as-of-origin vintage exists and is retrievable | Graded, no deviation |
| **B** | Each record carries its own event date, the value is a transaction fixed at that date, the publisher does not restate it, but first publication postdates the origin | Graded **only** with the availability deviation printed on the scorecard, and never as the sole basis of a certified claim |
| **C** | The value at any date is a retrospective construct — a model output, a period aggregate, or an index rebuilt with later methodology | Diagnostic only. Never graded |

Class B requires all four conditions, and the burden of proof is on the
submission. A dataset that revises its own history is Class C however
transactional it looks.

**This amendment does not rescue either source already excluded.** FEMA's National
Risk Index expected annual loss is a model output whose 2025 release embeds 2025
science: Class C. The Treasury FIO workbook is a single aggregate computed over
2018-2022: Class C. Both remain diagnostics and the E6 and E7 verdicts stand
unchanged. The amendment was written because an NFIP paid flood claim is a
different kind of object from both — a dollar amount settled on a dated loss,
carried in a file that does not restate it — and the rule as originally written
could not express that difference.

The honest cost of Class B is stated plainly: a Class B feature makes the backtest
a weaker simulation of real-time forecasting, because a forecaster standing at the
origin could not have pulled the number. A cell certified with a Class B feature
carries that deviation on its face, permanently.

### Registered pre-registration: the NFIP series

Recorded **before** the regressions were run, for the same reason the shock signs
were recorded before `y_hpi` was ever graded.

The candidate features are (i) `nfip_rate_per_1k`, the NFIP premium per $1,000 of
building coverage, and (ii) `nfip_loss_pc_log`, log paid flood losses per resident
per year over a twenty-year trailing window.

| Prediction | Expected | Falsified if |
|---|---|---|
| Price sign on `y_hpi` | negative | positive at \|t\| >= 2 |
| Price sign on `y_pop` | negative | positive at \|t\| >= 2 |
| Fidelity to the FIO market premium | R-squared >= 0.25 to be called tracking | below 0.25 |
| **Flood is weaker than multi-peril on prices** | magnitude below the E7 NRI coefficient | flood exceeds multi-peril |

The fourth row is the interesting one, because it is a genuine out-of-sample
prediction derived from E7 rather than a restatement of prior belief. E7 found that
within the NRI hazard decomposition the wind share carried the entire price signal
(-0.00366, t = -2.66) while the wildfire and flood shares were insignificant. If
that decomposition is real, then a flood-only price and a flood-only loss history
must both be weak on house prices — weaker than NRI's all-hazard rate, which was
itself only 56% of the FIO premium coefficient. If instead the NFIP flood measures
come in *stronger* than the multi-peril measures, the E7 hazard decomposition is
wrong and this protocol will say so in the same release.

### Correction: the NFIP policy file has no pre-2009 history

The v1.4.0-grip1 release notes stated that the NFIP policy file offers "genuine
pre-2009 history" and named it the next adapter partly on that basis. **That was
wrong.** OpenFEMA reports the `NfipPolicies` v3 temporal coverage as beginning
2009-01-01, which was verifiable at the time the claim was made and was not
checked. The policy file therefore reaches no further back than the FHFA and PEP
series already in the panel, and offers no additional origins.

What does reach back is the **claims** file, whose earliest observed loss year is
1978. But a paid claim is a realised loss, not a price, so it cannot substitute for
a premium — it can only proxy the hazard that a premium is supposed to price. The
distinction is the whole content of E8.


The rule cuts the other way as a design constraint: the search for a feature is a
search among series with pre-2009 history, which is a much smaller and much more
boring set than the one the marketing literature discusses. That is the point.

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

GRIP-1 grades **two targets**, each with its own mandatory baseline: the prior
one-year change in the same quantity being forecast.

| Target | Quantity | Mandatory baseline |
|---|---|---|
| `y_pop_wr` | annualised metro population growth, Census PEP | `pop_g1_wr` |
| `y_hpi_wr` | annualised metro house-price growth, FHFA HPI | `hpi_g1_wr` |

Both are demeaned within (origin year, census division) per section 5. Each
baseline is one line of code and free; `pop_g1_wr` beat the five-pillar Geometryx
composite in 8 of 8 cells in prior testing.

The pairing is not optional. Grading a house-price forecast against a population
baseline is a straw man, and grading it against no baseline at all is how
essentially every vendor forecast in this market is sold. A scorecard that does
not report its baseline is invalid.

Targets are graded **independently and both are published**, including where
they disagree. `y_hpi` is the cheaper test of the section-8 shock suite, because
the mechanisms the shocks encode — affordability constraint, insurance-cost
capitalisation — act on prices in one step and on population only through a
subsequent migration response. A shock inversion that appears on both targets is
a property of the features, not of one outcome variable.

## 8. Evaluation criteria

Mirroring AIMIP's E1-E5:

| ID | Criterion | Method |
|---|---|---|
| **E1** | Descriptive fit | In-sample R² and rank correlation. Reported, never sold. |
| **E2** | Out-of-sample skill | Spearman rho and R² at each rolling origin, with bootstrap 90% intervals |
| **E3** | Skill above baseline | **Paired** per-origin difference versus the target's mandatory baseline |
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

### Certification is a conjunction

A submission is certified for forward-looking claims at a (target, horizon) cell
only if **all four** gates pass:

| Gate | Requirement |
|---|---|
| Skill | beats the mandatory baseline on a majority of scored origins, paired |
| Shock signs | every graded shock returns its pre-registered sign |
| Interval calibration | realised coverage of the nominal 90% interval lies in [0.85, 0.95] |
| Member robustness | more than half of individual ensemble members beat the baseline |

Certification is deliberately not a weighted score, because a score lets a large
R² buy off a wrong sign. The reference run demonstrates why the conjunction is
load-bearing rather than decorative: `y_hpi` at horizon 5 passes skill (4/7
origins), interval calibration (93.0%) and member robustness (52.5%), and is
barred solely by the shock gate. A model that appreciates the most over-trend and
the most hazard-exposed metros fastest ranks metros well for the wrong reason.

Expected signs may **never** be revised after a target is run. The signs in the
table above were registered in release `v1.0.0-grip1`, published before `y_hpi`
was ever graded, and are unchanged.

### Out-of-panel diagnostics

Some questions cannot be asked inside the panel and are still worth answering. A
**diagnostic** is a numbered, published analysis that uses data or a design the
graded panel may not use. Rules:

1. A diagnostic is never scored, never certified, and never enters a gate.
2. Its output must carry the status string `DESCRIPTIVE -- NOT A GRADED FORECAST`.
3. It must state, in its own output, why it is not a forecast.
4. It may not be cited as evidence of skill. It may only be cited as evidence
   about a **mechanism** or about the adequacy of a **feature**.
5. A diagnostic may not be used to revise a pre-registered expected sign. If a
   diagnostic contradicts a registered sign, the registered shock keeps failing
   on the record and a new, separately named shock is registered alongside it.

The first is **E6, the premium sign diagnostic** (`run_premium_diagnostic.py`,
`out/E6_PREMIUM_SIGN.md`). The graded `premium_shock_40pct` perturbs `hpi_vol`, a
house-price volatility term standing in for insurance cost, and returns the wrong
sign in all four cells. E6 substitutes real FIO premiums and finds that the
pre-registered negative sign holds strongly on house prices (−0.0052 per standard
deviation, t = −6.8, within division, with momentum controlled) and inverts on
population (+0.0007, t = +2.1). Premium *growth* is negatively signed on
population where premium *level* is positively signed, and dropping the three
Southern divisions turns the population coefficient negative.

The consequences for the protocol are:

- The graded price inversion is a **proxy failure**, not a mechanism failure. The
  named fix is to replace `hpi_vol` with a premium series, and E6 is the
  calibration target any vintage-legal premium proxy must reproduce.
- A single global expected sign per shock was an inadequate specification. Future
  shocks state expected signs **per target**, and where a mechanism is regionally
  conditional, per region.
- `premium_shock_40pct` is not revised. It remains registered as it was published
  in v1.0.0-grip1, and it remains failing.

The second is **E7, the NRI proxy calibration** (`run_nri_calibration.py`,
`out/E7_NRI_PROXY.md`), which tests the fix E6 named. FEMA's National Risk Index
expected annual loss per dollar of building exposure is the closest free
multi-peril analogue to a homeowners rate. Measured against actual FIO premiums it
explains 13.2% of the cross-metro variation in what people pay, with an elasticity
of 0.26 rather than 1.0. Substituted into the E6 specification it reproduces both
E6 signs — −0.0029 (t = −2.8) on house prices, +0.0007 (t = +2.0) on population —
at 56% of the E6 price magnitude. In a horse race against the premium its price
coefficient collapses to −0.0008 (t = −0.8) while the premium retains −0.0049
(t = −6.2).

The consequences are:

- **E6 is corroborated.** An independent federal source, built from hazard
  climatology rather than from insurer filings, reproduces both signs. E6 measured
  a mechanism, not an artefact of the FIO file.
- **NRI is not the replacement.** It is a noisy partial measurement of the same
  quantity and contributes nothing once the premium is present. It is admitted as a
  substitute of last resort only, and it is ineligible regardless under the
  minimum-history rule in section 4.
- **The peril that carries the price signal is wind**, not wildfire; the wildfire
  share is insignificant on both targets.
- The search for a graded premium proxy is constrained to series with pre-2009
  history. The next candidate on the register was the OpenFEMA NFIP policy file,
  which was described in the v1.4.0-grip1 notes as having long history. **It does
  not** -- see the correction in section 4 -- and E8 below tests what the NFIP
  actually offers.

The third is **E8, the NFIP flood calibration** (`run_nfip_calibration.py`,
`out/E8_NFIP_FLOOD.md`), and it is the first diagnostic whose predictions were
published, with no results, in a separate earlier release: commit
`6ca77bbf0bcb13bbbf49a9301a3e364379bfb384`, 2026-08-23T20:45:59Z, release
`v1.5.0-prereg`. Two features were tested, and they are different objects: a
regulated price (`nfip_rate_per_1k`, premium per $1,000 of building coverage,
from a stratified sample of 780,695 policies effective in 2022) and a realised
loss (`nfip_loss_pc_log`, paid flood claims per resident per year over a
twenty-year window, from a full pull of all 2,724,656 claims).

The results are:

- **Neither series proxies the homeowners premium.** Both fail the pre-registered
  fidelity floor of R² ≥ 0.25 (0.101 and 0.179). The flood price fails it
  *inverted*: elasticity −0.304 (t = −5.66) against the FIO premium. Metros with
  expensive flood cover have cheap homeowners cover, because NFIP rates price
  floodplain position while homeowners rates price wind and hail, and the two
  peril maps barely overlap. **That line of enquiry is closed**: no flood price
  will ever substitute for a homeowners price.
- **Realised loss beats modelled loss.** On house prices the loss burden gives
  −0.00391 (t = −4.30), 75% of the E6 premium magnitude, and unlike E7's NRI rate
  it **survives** the premium control at −0.00188 (t = −2.13). Head to head
  against the NRI all-hazard rate it wins outright, −0.00309 (t = −2.92) against
  −0.00110 (t = −0.90). A dollar actually paid after a flood measures the hazard
  better than a model's estimate of what that dollar should have been.
- **The population sign inversion partly resolves.** E6 and E7 both found
  population growth moving *with* insurance cost. The flood price is the first
  feature to recover the pre-registered negative sign, −0.00161 (t = −4.82), and
  with both in the same regression it holds at −0.00147 (t = −4.44) while the FIO
  premium's positive coefficient loses significance (t = +1.47). The hypothesis
  this suggests — that the positive coefficient is the homeowners premium standing
  in for warm Sun Belt states rather than people moving toward risk — is a
  hypothesis generated by a diagnostic. It does **not** license changing
  `premium_shock_40pct`, which remains registered as published in v1.0.0-grip1 and
  remains failing.
- **The pre-registered falsification test came out CONDITIONAL.** E7 attributed
  the whole price signal to the wind share and found flood insignificant. The
  flood loss burden exceeds E7's all-hazard coefficient on the full cross-section,
  which falsifies that. But the falsification does not survive trimming the top
  loss decile (0.00171, below E7's 0.00293), so E7 is not refuted outright. What
  E7 got wrong was measuring flood with a modelled share of a modelled construct
  instead of with paid claims. The sign is right and significant at every one of
  the seven cuts tested; only the magnitude claim is fragile.

Two consequences bind future work:

1. **Prefer realised transactions to modelled constructs, even when the model is
   free and the transactions are awkward.** Every modelled feature tried so far —
   NRI expected annual loss, the FIO period aggregate — is Class C and collapses
   against a price. The one measured feature that does not collapse is a paid
   claim. Adapters should be ranked by how close the record is to a settled
   transaction, not by convenience.
2. **Class B eligibility has to be earned by waiting.** Both NFIP series are
   Class B under Amendment 1, so they are gradeable in principle with the
   availability deviation declared. They are not gradeable in this run, because
   OpenFEMA serves one current file and no archived vintages. The route to grading
   is to begin archiving monthly snapshots now and wait. That is a real cost,
   stated rather than evaded, and it is not a reason to bend the vintage lock.

**E9 (registered, results pending at time of writing).** Section 13 registers a
post-hoc specification attempt against the E5 shock-sign failure: metro fixed
effects, with the accept/reject rule and the power precondition fixed in advance.

## 9. Ensembles, not point estimates

AIMIP requires a minimum 5-member ensemble, described as "enough to estimate
dispersiveness" — not enough to isolate the forced response. GRIP adopts the
same floor. A submission reporting a single number per metro is rejected. Every
published Geometryx figure derived from a GRIP-graded model must carry an
interval.

The reference implementation builds members by **block bootstrap over origin
years**. The resampling unit is the whole origin, not the metro: metros within an
origin share a national cycle and a single delineation vintage, so resampling
metros would treat correlated rows as independent and understate the spread.
Each member is a model that could legitimately have been fitted from the same
history, which is the analogue of AIMIP's initial-condition members.

**Two intervals that must not be conflated.** Member spread answers *which model
might I have fitted*. It does not answer *how wrong is this model about this
metro*. In the reference run the spread across members is roughly a tenth of the
realised forecast error (`parameter_spread_to_error_ratio` median 0.10 at h=5).
Publishing member spread as if it were a forecast interval would be worse than
publishing no interval at all, because it would be narrow and wrong rather than
simply absent.

A GRIP predictive interval is therefore the ensemble mean widened by the
empirical residual distribution from **strictly earlier scored origins only**,
and it is not reportable until its realised coverage is published beside it. A
nominal 90% interval whose measured coverage is not in [0.85, 0.95] is
non-conforming and may not be attached to a public figure.

**Verdict robustness.** Because a verdict computed only from the ensemble mean
can rest on the averaging rather than on the method,
`members_beating_baseline` is reported per origin and
`member_share_beating_baseline` across all origins. A model whose mean beats the
baseline while most of its members do not has not demonstrated skill.

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

## 13. Specification budget and post-hoc specification attempts

Everything above governs what data may enter a forecast. This section governs
something the vintage lock does not touch and that quietly destroys more
published research than leakage does: **how many specifications an author is
allowed to try after seeing a result, and what those attempts may then claim.**

GRIP-1 published four NOT CERTIFIED cells in `v1.0.0-grip1`, with the binding
constraint on all four being the shock gate. The obvious next move — try a
different estimator and see whether the signs come right — is exactly the move
that, repeated silently, converts any dataset into a confirmation of whatever the
author expected. The protocol therefore makes the attempts countable.

**The rule.** Every specification change proposed *after* a graded result is
known is a numbered attempt against that result. Each attempt must, before it is
run, declare: the specification, the prediction, the accept/reject rule, and the
power precondition under which the test would be uninformative. Each attempt is
released results-free and then released again with results, whatever they are. An
attempt that is run and not published does not exist, and the numbering makes an
unpublished attempt visible as a gap.

**What an attempt may claim.** Nothing, in the cell it was chosen against. A
specification selected in the knowledge of a failure cannot certify that failure
away, because the selection itself used the outcome. The most a successful
attempt earns is the status of CANDIDATE: it must then be re-registered blind and
re-graded on a fresh run before any certification claim attaches. This is the same
reasoning that bars `premium_shock_40pct` from being revised on the strength of E6
through E8, applied to estimators instead of features.

### Attempt 1 — E9, metro fixed effects and the E5 re-run

**Why this specification.** Two of three pre-registered shocks fail in all four
cells, and both failures route through exactly two coefficients: `hpi_vol_wr`
(perturbed by `premium_shock_40pct`) and `hpi_gap_wr` (perturbed by
`rate_shock_200bp`). Those two are also the only SIGN-UNSTABLE entries in E4. E8
then found that the positive population coefficient on the Treasury FIO premium
loses significance once NFIP flood price sits in the same regression, which is
consistent with the premium having stood in for persistent warm-state
characteristics rather than for a risk price. If that confound also drives
`hpi_vol` and `hpi_gap`, removing persistent between-metro differences should
reveal a negative within-metro relationship. Metro fixed effects test that and
nothing else.

**Three structural facts fix the design, and each removes an option.**

1. For a `scope="exposed_only"` shock, `run_shock` computes
   `delta[exposed].mean() − delta[~exposed].mean()` from a linear model in which
   the perturbation lands only on exposed rows. That difference *is* the fitted
   coefficient on the perturbed standardised feature. "Re-running E5" is
   therefore identically "re-estimating those two coefficients", and the suite is
   executed unmodified so this is a code path rather than an assertion.
2. **A metro effect cannot be estimated within one origin.** Each metro
   contributes one row per origin, so the within-metro transformation is
   identically zero in any single cross-section. E4's per-origin stability
   statistic has no fixed-effects analogue. Leave-one-origin-out replaces it, and
   is applied to *every* specification including the baseline, so the published
   E4 numbers (`share_positive` 0.429 and 0.857 at h = 5) are **not** comparable
   to E9's and are not compared to them.
3. **A metro effect on the target is not computable at forecast time.** Demeaning
   an outcome by its own metro mean requires that metro's mean outcome, which
   contains the outcome being forecast. Any specification that demeans the target
   within metro is permanently a diagnostic and can never be graded, however good
   its coefficients look. This is a fact about forecasting, not a choice, and it
   is the reason the attempt is split into S1 and S2 below.

**Specifications.** Metro nests inside division, so a metro effect absorbs the
division effect and S1/S2 do not demean by division again. The `origin_year` term
is kept everywhere, because dropping it leaves the national cycle in the residual
and that residual is itself a clock — the failure that made the first run of this
harness flag every price feature as CLOCK_LEAK.

| Spec | Features | Target | Status |
| --- | --- | --- | --- |
| S0 | `(origin_year, division)` demeaned | same | the registered baseline, as graded in v1.0.0-grip1 |
| S1 | two-way `(origin_year, cbsa_code)` within | two-way within | **diagnostic only, never gradeable** (fact 3) |
| S2 | origin demeaned, then expanding within-metro over origins ≤ Y | S0's target | forecast-legal; gradeable only after re-registration |
| S0_on_S2_sample | S0 transform | S0's target | control, on exactly S2's rows |

The control is not decoration. S2 discards each metro's first three origins, so
any coefficient movement between S0 and S2 could be the specification or could be
the smaller sample. Without running S0 on S2's rows the comparison would be
uninterpretable, and reporting S2 against full-sample S0 alone would be a
mistake dressed as a finding.

S2 exists because it is the only version that could ever ship. Its features ask
"is this metro's volatility high relative to its own history", which a forecaster
standing at the origin can answer, while its target keeps the cross-sectional
meaning the product is actually sold on. S1 answers whether the confound is real;
S2 answers whether anything can be done about it in a live forecast.

**Sample rule.** A metro must appear in at least 4 origins to contribute
within-metro variation. A metro observed once is absorbed exactly by its own
fixed effect and contributes a row of zeros.

**Predictions, registered before execution.**

- **P1** — In S1 the pooled coefficients on `hpi_vol_wr` and `hpi_gap_wr` both
  turn **negative**, matching the pre-registered shock signs.
- **P2** — In S1 the leave-one-origin-out `share_positive` for both focal
  features falls below 0.5, i.e. reliably negative rather than merely stable.
  Stability alone is not success: a coefficient stably positive on a shock whose
  registered sign is negative is stably wrong.
- **P3** — In S2 the E5 verdicts for `rate_shock_200bp` and
  `premium_shock_40pct` both flip to PLAUSIBLE.
- **P4**, a precondition rather than an outcome — any feature whose
  within-metro share of variance is below **0.10** is declared UNINFORMATIVE and
  its fixed-effects sign is not read as evidence in either direction. A metro
  effect can absorb nearly all of a slow-moving feature's variance, and reading
  the sign of what remains is reading noise.

**Accept rule.** The confound hypothesis is SUPPORTED only if P1 and P2 both hold
for **both** focal features and the P4 precondition passes for both. Anything
partial is reported as NOT SUPPORTED. Inference on the focal coefficients uses OLS
with standard errors clustered on metro, because a five-year forward outcome
measured at consecutive origins overlaps by four years and unclustered
t-statistics would be inflated several-fold.

**If it rejects.** Then the inversion is within-metro as well, the estimator is
not the problem, and the features are. That routes the fix to measured
transactions such as the NFIP realised losses from E8, not to a further
regression — and attempt 2 should not be another estimator.

**What this attempt cannot do.** It cannot certify. The four NOT CERTIFIED
verdicts in `v1.0.0-grip1` stand whatever E9 returns. If P3 holds, S2 becomes a
CANDIDATE requiring a fresh full backtest under a fresh blind pre-registration
before any shock claim attaches to it.


---

**Attribution.** This product uses FHFA Data but is neither endorsed nor
certified by FHFA. Population estimates, building permits and metro delineations
are US Census Bureau products in the public domain.
