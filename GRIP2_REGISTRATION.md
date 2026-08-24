# GRIP-2 — Blind Re-Registration

**Status: REGISTERED. This document is the anchor.** Tagged results-free as `v2.0.0-prereg` before
any GRIP-2 harness code exists. Every target, feature, gate, threshold and precondition below was
fixed at this tag. The grading run executes at the scheduled time in §7.3 and this file may not be
edited between the two — any edit voids the anchor and makes the result a numbered attempt under §8
rather than a grade.

**GRIP-1 is not amended, withdrawn or revised by this document.** `v1.0.0-grip1` stays published in
its failing state, with all four cells NOT CERTIFIED and both failing shocks registered exactly as
they were. GRIP-2 is a new protocol with new targets, new features and new gates. It is not a
retry of GRIP-1 with better numbers, and no GRIP-2 figure may be presented as an improvement on a
GRIP-1 figure — the samples, the targets and the feature sets all differ, so the comparison would
be meaningless.

---

## 1. Why a new protocol rather than an amendment

GRIP-1's specification budget (PROTOCOL.md §13) exists to stop exactly the move this document could
otherwise be. Any specification chosen with knowledge of a graded failure is capped at CANDIDATE and
cannot certify the cell it was chosen against. Attempt 1 (E9) was rejected. Attempt 2 (E10) was
SUPPORTED and remains CANDIDATE. Neither can re-grade anything, and no further attempt can either.
The only honest route to a certified cell is a protocol whose specification was fixed before its
outcomes were observed, graded on a sample that has not been used to select it.

GRIP-2 also inherits two findings that arrived after the first draft of this document and changed it
materially: an inference audit of our own harness (§5 G7), and a review of the predictability ceiling
which establishes that point accuracy at these horizons is capped low for everyone (§5 G8). Both are
recorded in `out/RETHINKING_THE_SCORECARD.md`. Neither was known when GRIP-1 was published.

Four things GRIP-1 established that GRIP-2 is built on, each with its honest limit attached:

1. **`hpi_gap` was never an affordability variable.** It correlates **+0.909** with the same metro's
   five-year price growth (`out/feature_audit.json`). It is momentum measured twice. Retired, not
   repaired.
2. **`hpi_vol` was never an insurance price.** It correlates **−0.947** with 2000s peak-to-trough
   crash depth at origin 2010, and E9 showed it carries almost no within-metro information about
   either target. Demoted.
3. **An income denominator works.** `hpi_income_gap` came out negative and significant in all four
   E10 WINDOW variants, inside the same window where the denominator-free gap is positive. This is
   the strongest single result GRIP-1 produced, and it is the one GRIP-2 leans on.
4. **A bust control is not optional.** `hpi_drawdown` is among the strongest predictors in every E10
   specification (|t| = 7.2 to 9.7). Its absence is most of why the graded shocks looked wrong.

And two limits GRIP-2 must not paper over:

- E10's P1 passed on sign and stability only. `hpi_gap` is **nowhere significantly negative**. The
  wrong sign was destroyed, not reversed, and GRIP-2 should not be written as though a mean-reversion
  coefficient has been demonstrated.
- E10's decomposition showed the sample extension was **overclaimed**: a bust control inside the
  existing window does comparable work. GRIP-2 therefore treats the control as the primary fix and
  the longer sample as secondary, which is the reverse of how attempt 2 was motivated.

## 2. The gate defect, and how GRIP-2 fixes it

GRIP-1 §14.1 disclosed that **its shock gate could not be passed by a correct model on a
single-episode sample.** Origins 2010–2020 observe one monotone recovery from one crash; asking a
model to assert that over-trend metros will slow down is, in that sample, asking it to predict the
opposite of what happened. A gate no correct model can pass is broken, not strict.

Three structural fixes, all declared here rather than discovered later.

**Fix 1 — an identification precondition, measured without touching outcomes.** A shock sign is
gradeable in a cell only if that cell's sample contains more than one regime. Operationally: pooling
all rows in the cell, at least **20%** must come from origins whose forward horizon contains a
national real price decline and at least **20%** from origins whose forward horizon does not. The
national reference series is the FHFA US index, and the test reads only the index, never a
coefficient or a residual. If the precondition fails, the shock returns **UNIDENTIFIED**, not
IMPLAUSIBLE. A protocol that reports "we cannot tell" is worth more than one that reports a
falsehood confidently.

**Fix 2 — shocks are graded only on a specification containing the confound control.** Because an
`exposed_only` shock response is arithmetically the fitted coefficient on the perturbed feature
(established in E9), a shock sign is a partial correlation and inherits every omitted-variable
problem in the specification. `hpi_drawdown` is therefore **mandatory in every price specification**
and every price shock is graded on that specification. No shock may be graded on a specification
that omits a control this protocol declares mandatory.

**Fix 3 — one gate that does not rely on a ridge coefficient at all.** A penalised partial
correlation cannot deliver a causal sign, however many robustness columns surround it. G6 below
grades a genuine administrative natural experiment instead. It is Class B and it is reported
separately, so a failure there does not contaminate the Class A cells and a pass there cannot rescue
them.

## 3. Targets

| Target | Definition | Status | Origins available |
|---|---|---|---|
| `y_hpi` | annualised FHFA metro index growth, base B to B+h | **graded** | 1995 onward |
| `y_inflow` | cumulative **gross** in-migrating returns, years B+1..B+h, over base-year returns | **graded** | 1996 onward |
| `y_outflow` | cumulative **gross** out-migrating returns, same scaling | **graded** | 1996 onward |
| `y_flow_pair` | directed origin→destination flow, metro pair, B+1..B+h | **graded (§3a)** | 1996 onward |
| `y_netdom` | net domestic migration over base population | **derived, reported, not gated** | 2002 onward |
| `y_pop` | annualised total population growth (the GRIP-1 target) | **reported, not gated** | 2002 onward |

**`y_pop` is demoted deliberately.** E9 found that removing metro identity destroys 83% of the
population fit versus 6% for prices. The most likely explanation is natural increase: births minus
deaths is close to deterministic five years out and is largely a function of age structure, so
grading total population growth awards most of its credit for demographic momentum nobody forecasts,
while the migration signal the product actually sells is a minority of the variance. Climate risk and
insurance cost also have no plausible channel to births. `y_pop` stays on the scorecard for
continuity with GRIP-1 and because dropping a target after it embarrassed us would be the wrong
precedent, but it carries no gate.

**Grading gross flows rather than net migration is the substantive change in this protocol, and it is
forced by evidence rather than chosen for convenience.** The Census Bureau's own evaluation of its
1995–2025 state projections, at exactly our five-year horizon, reports a total-population MAPE of
**2.64%** and a net domestic migration MAPE of **193.3%** (Series A) and **174.2%** (Series B),
described in that paper's own words as "the worst component in the projection." Utah was projected at
**+112,548** against an estimated **−5,247** — the wrong sign, at 2,245% absolute error
([Census POP-twps0067](https://www.census.gov/library/working-papers/2002/demo/POP-twps0067.html)).
Earlier Census validation of **gross** interstate flows achieved roughly **8–12%** error at one to two
years ([Census RR90-07](https://www.census.gov/content/dam/Census/library/working-papers/1990/adrm/rr90-07.pdf)).

A net flow is a small difference between two large gross flows, so it inherits the noise of both and
the signal of neither. Registering it as the graded target would have guaranteed failure and taught us
nothing about the model. **`y_netdom` is therefore derived and reported, never gated.** Any GRIP-2
attempt that proposes promoting it back to a graded target must first demonstrate that the gross cells
passed.

**Source.** Gross flows come from IRS SOI county-to-county migration, verified hands-on rather than
assumed: **33 annual transitions, 1990–1991 through 2022–2023**, national county inflow and outflow
files with the exact nine-column header
`y2_statefips,y2_countyfips,y1_statefips,y1_countyfips,y1_state,y1_countyname,n1,n2,agi`, 130,101 rows
in 2011–2012 and 90,048 in 2022–2023, carrying returns (`n1`), individuals (`n2`) and aggregate AGI
([IRS SOI](https://www.irs.gov/statistics/soi-tax-stats-migration-data)). Aggregation to CBSA uses the
vintage-appropriate Census county crosswalk.

Four disclosed problems, registered now rather than discovered later:

- **IRS is Class B and can never be Class A.** It counts tax filers, not people; non-filers are absent
  entirely; and `n2` is documented as exemptions in the older guide and as individuals in the newer
  one, so the two eras are not the same quantity. Returns (`n1`) is the graded measure for that reason.
- **Suppression is material and is registered as a known bound, not a nuisance.** Named county edges
  carry **78.67%** of county domestic migration returns in 2011–2012 and **73.23%** in 2022–2023; the
  balance cannot be placed on a named edge. The current county threshold is **20 returns**
  ([2022–23 guide](https://www.irs.gov/pub/irs-soi/2223inpublicmigdoc.pdf)). Every graded flow cell
  must publish its realised named-edge coverage share, and a cell below **70%** coverage returns
  UNINFORMATIVE.
- **Two documented series breaks**, at 2011–2012 and 2022–2023. Spans crossing a break are graded but
  **reported separately as a mandatory robustness split**, and a cell whose verdict flips across the
  split is recorded UNSTABLE rather than certified. This is the same discipline the decennial reset
  required, applied to a different seam.
- **Independent validation is required, not optional.** Every graded flow cell must report its rank
  correlation against Census ACS county-to-county flows, which are uncertainty-aware and not
  disclosure-suppressed but come as twelve **overlapping five-year** releases, 2005–2009 through
  2016–2020, and are therefore a benchmark rather than an annual panel
  ([Census](https://www.census.gov/topics/population/migration/guidance/county-to-county-migration-flows.html)).
  If two independent federal measures disagree materially, the target definition is the suspect and
  GRIP-2 pauses rather than grading against a measure it cannot corroborate.

Horizons: h = 5 primary, h = 3 secondary and reported, as in GRIP-1.

## 3a. The pair-level cell

The metro panel has 410 units and, in the deepest version we have built, 27 origins and **6
non-overlapping five-year blocks**. §5's inference audit shows the binding constraint is independent
time periods, not rows. Adding features to a 410×27 panel cannot fix that, and no feature engineering
will.

The directed pair panel is the one structural way to buy identifying variation without buying data:
up to roughly **168,000 ordered metro pairs** per year from files already in hand. With **origin × year
and destination × year fixed effects**, identification comes from pair-level variation, which survives
the national cycle that dominates the metro panel.

Registered in advance:

- **Estimator:** censored/hurdle Poisson pseudo-maximum-likelihood on flow counts, with an explicit
  zero/suppressed state. Counts are not logs and must not be modelled as logs.
- **Mandatory baselines, both of which must be beaten for the cell to count:** (a) **persistence** —
  last observed pair flow; (b) a **gravity model** in origin mass, destination mass and distance. A
  method that cannot beat persistence is not a method. Published held-out county-flow work reports
  OD-flow R² of **0.81** for boosted trees against **0.59** for extended radiation, but those are
  **next-year** figures and are registered here as context, not as a target
  ([Robinson & Dilkina](https://arxiv.org/pdf/1711.05462)).
- **Standard errors clustered two-way on origin metro and destination metro**, with the pair count and
  both cluster counts published.
- **Suppressed edges are a modelled state, not a dropped row.** Dropping them would condition on the
  outcome, because suppression is a function of flow size.

This cell is **Class B** for as long as IRS is its only source.

## 4. Features

Every price specification must contain the mandatory controls. Retired features may not be
reintroduced by any GRIP-2 attempt.

| Feature | Role | Definition |
|---|---|---|
| `hpi_g1` | free | one-year lagged index growth |
| `hpi_g5` | free | five-year annualised lagged index growth |
| `hpi_drawdown` | **mandatory control** | deepest peak-to-trough log decline in the 15-year window to B; ≤ 0 |
| `hpi_income_gap` | **focal** | deviation of log(index ÷ per-capita personal income) from its own 15-year trend |
| `permits_pc`, `permits_g3` | free | as GRIP-1; permits lagged to B−1 |
| `pop_g1`, `pop_g3`, `pop_accel` | free | as GRIP-1 |
| `inflow_rate_g1`, `inflow_rate_g3` | free | lagged **gross** in-migration rate, one- and three-year |
| `outflow_rate_g1`, `outflow_rate_g3` | free | lagged **gross** out-migration rate, one- and three-year |
| `flow_entropy` | free, Class B | Shannon entropy of the metro's inbound edge-weight distribution at B |
| `flow_concentration` | free, Class B | share of inbound flow from the top five origin metros at B |
| `flow_reciprocity` | free, Class B | correlation of inbound and outbound volume across partner metros at B |
| `agi_per_return_in` | free, Class B | mean AGI per in-migrating return at B, from IRS `agi` ÷ `n1` |
| `nfip_loss_pc_log` | **focal, Class B** | log realised NFIP paid losses per capita through B |
| ~~`hpi_gap`~~ | **RETIRED** | momentum measured twice (+0.909 with `hpi_g5`); no content once `hpi_drawdown` is present |
| ~~`hpi_vol`~~ | **RETIRED as a risk proxy** | a 2000s crash-severity register (−0.947); may not be described as insurance cost again |

`hpi_income_gap` uses BEA CAINC1 per-capita personal income, county 1969–2024, aggregated to CBSA as
total personal income over total population ([CAINC1.zip](https://apps.bea.gov/regional/zip/CAINC1.zip)).
Because the feature is a deviation from the metro's own trend, the arbitrary constant in an
index-over-dollars ratio drops out. BEA merges some Virginia independent cities into combination codes
matching no county FIPS, so a metro is used only at ≥80% county match, with the realised rate
reported.

`nfip_loss_pc_log` is promoted from E8, where realised paid losses beat the modelled NRI rate head to
head and survived a premium control (→ `y_hpi` −0.00188, t = −2.129). It is **Class B**, graded with
deviation, never Class A.

## 5. Gates and accept rules

All eight gates are declared here in full. A cell is CERTIFIED only if every applicable gate passes.
**G6 is declared here but deferred to GRIP-2.2 per §13 item 5 and is not run in this release**; it is
specified in full anyway so that it cannot be reshaped later in light of what run one returns.

- **G1 — Skill.** The model must beat the mandatory naive baseline (prior one-year change in the same
  quantity) on the declared primary metric in at least **5 of 7** origins. Reported per origin.
  **Switching the skill metric to R² is prohibited**, as it was in GRIP-1, and this prohibition is
  not waivable by any attempt.
- **G2 — Member robustness.** At least **60%** of ensemble members must agree with the ensemble-mean
  direction. Minimum five members.
- **G3 — Clock audit.** No feature may pass a CLOCK_LEAK check by carrying a cross-sectional
  reference distribution from the future. Unchanged from GRIP-1, which is the one part of the harness
  that has already caught its author.
- **G4 — Vintage audit.** No predictor may derive from a file published after 31 December of the
  origin year. Delineation vintage ≤ origin year. Unchanged.
- **G5 — Shock signs, subject to the §2 preconditions.** Three shocks, re-specified against the new
  features and given new names so they can never be confused with the GRIP-1 shocks:

  | Shock | Perturbs | Registered sign on `y_hpi` | Registered sign on `y_inflow` |
  |---|---|---|---|
  | `income_gap_shock_1sd` | `hpi_income_gap`, +1 SD, exposed quintile | **negative** | **negative** |
  | `flood_loss_shock_1sd` | `nfip_loss_pc_log`, +1 SD, exposed quintile | **negative** | **negative** |
  | `permit_shock_1sd` | `permits_pc`, +1 SD, exposed quintile | **negative** | **positive** |

  Graded only on the specification containing `hpi_drawdown`, and only in cells passing the
  regime-diversity precondition. Otherwise UNIDENTIFIED.
- **G6 — Natural experiment, Class B, reported separately. DEFERRED to GRIP-2.2, specified now.**
  NFIP Risk Rating 2.0 repriced flood
  insurance by formula rather than by market forces: Phase I, new policies, effective
  **1 October 2021**; Phase II, all remaining policies renewing on or after **1 April 2022**
  ([FEMA](https://www.fema.gov/flood-insurance/risk-rating)). FEMA publishes ZIP-level premium-change
  breakdowns per state ([profiles](https://www.fema.gov/flood-insurance/risk-rating/profiles)).
  Registered design: difference-in-differences on premium-change intensity, treatment measured as the
  ZIP share of policies facing an increase, outcome being subsequent ZIP price growth, aggregated to
  metro for comparability with the graded cells. **Registered sign: negative.** Known limits, stated
  in advance — it is a one-time snapshot comparison rather than a premium time series, ZIPs with
  fewer than five policyholders are suppressed, and treatment intensity correlates with flood
  exposure, so the design identifies the effect of *repricing* and not of risk itself. A G6 failure
  does not contaminate the Class A cells and a G6 pass cannot rescue them.
- **G7 — Inference audit.** This gate exists because GRIP-1 failed it silently. `grip/fe.py` clusters
  standard errors on metro, which correctly allows a metro's residuals to be correlated across
  overlapping origins but **assumes metros are independent of one another within the same year**.
  Demeaning by origin × division removes the common mean, not the common factor. Recomputing identical
  coefficients under alternative assumptions on the deepest panel we have built (`run_se_audit.py`)
  moves `hpi_g1` at h=5 from **t = +20.858** under metro clustering to **+2.886** under
  non-overlapping-block clustering, a factor of **7.2**; `hpi_g5` from −13.031 to −3.710;
  `hpi_drawdown` from −9.077 to −2.869.

  Binding for every graded coefficient in GRIP-2:

  1. Report **four** t-statistics — metro, period, non-overlapping block, and two-way
     (Cameron-Gelbach-Miller) — never one.
  2. **Grade on the most conservative scheme that has an adequate cluster count**, where adequate is
     **≥ 10 clusters**. Below that the estimator is not conservative, it is degenerate: on the GRIP-1
     graded window, block clustering with two blocks returned t = 161.105 and t = 57.346, which are
     artifacts and not precision.
  3. **Publish the number of non-overlapping blocks in every cell**, on the scorecard, beside the
     verdict.
  4. If no scheme allowing within-period cross-metro correlation has ≥ 10 clusters, the cell's
     inference is **UNIDENTIFIED**. On present evidence this is the honest status of most of the
     GRIP-1 graded window, which has **2 blocks at h = 5**.

- **G8 — Calibration, ranking, and honest abstention.** Point accuracy is capped low at these horizons
  by evidence outside our control: reviewed five-year out-of-sample R² ceilings are roughly
  **0.00–0.20** for metro house prices and **0.00–0.15** for net migration, against a best measured
  metro price result of median **43% R² at twelve months**
  ([Rady/UCSD](https://rady.ucsd.edu/_files/faculty-research/timmermann/HSI.pdf)) that does not carry
  to five years, and a genuine three-year MSA test with RMSE of **10.1 to 37.6 percentage points**
  ([Lincoln Institute](https://www.lincolninst.edu/app/uploads/legacy-files/pubfiles/2142_1468_Follain_WP12JF1.pdf)).
  A scoreboard that grades only accuracy therefore grades a quantity nobody can win, which is
  uninformative rather than rigorous.

  GRIP-2 additionally grades what is achievable:

  1. **Interval coverage.** A declared 80% interval must contain the realised outcome in **75–85%** of
     cases. Both under- and over-coverage fail; an interval wide enough to always contain the truth is
     not a forecast.
  2. **Rank correlation.** Spearman ρ between predicted and realised cross-metro ordering, reported per
     origin, and required to beat the persistence baseline in **5 of 7** origins.
  3. **A scored indeterminate class.** An entrant may decline to forecast a metro-horizon cell.
     Abstention is **not free and not penalised as an error**: declared coverage is published alongside
     accuracy on the covered subset, and an entrant covering 40% of metros well is reported as exactly
     that, never as beating an entrant covering all of them. Abstaining on more than **50%** of a cell
     returns UNINFORMATIVE for that cell.
  4. **Sharpness must be reported with coverage.** Mean interval width is published in every cell, so
     coverage cannot be bought with width.

**Accept rule.** In this release CERTIFIED requires **G1, G2, G3, G4, G5, G7 and G8** all passing,
applied per cell to the gates applicable to it, and the power precondition in §6 met. G6 is deferred
per §13 and no cell's verdict depends on it in either direction.
A cell with any gate UNIDENTIFIED is recorded **NOT CERTIFIED (UNIDENTIFIED)** — distinct from
NOT CERTIFIED (FAILED), because conflating "we cannot test this" with "this is false" is the error
GRIP-1's gate made.

The distinction is not academic. E10's P3 was reported as a failure on `hpi_vol` at t = +3.202 under
metro clustering. Under period clustering the same coefficient is **t = +1.938** — not distinguishable
from zero. Under G7 that result is UNIDENTIFIED, not IMPLAUSIBLE, and the earlier report of it as a
failure overstated what the data could support. Conversely `hpi_income_gap` at h = 5 survives every
scheme and is **strongest** under block clustering at **t = −4.186**, which is why it is the one focal
feature carried into this protocol. At h = 3 it is marginal (two-way **−1.900**) and is not claimed.

## 6. Power preconditions, fixed in advance

- `y_hpi`: ≥ **20** origins, median ≥ **150** metros per origin.
- `y_inflow` and `y_outflow`: ≥ **15** origins, median ≥ **150** metros per origin.
- `y_flow_pair`: ≥ **15** origins, median ≥ **20,000** named directed pairs per origin, and named-edge
  coverage ≥ **70%** of total flow volume per §3.
- Every cell: ≥ **60** usable rows after demeaning, ≥ **5** metros per demeaning group.
- **Every cell: ≥ 10 clusters under the scheme it is graded on, per G7.** This is a power
  precondition, not a robustness nicety, and it is the one most likely to bite — it disqualifies the
  GRIP-1 graded window as currently constructed.
- Regime diversity per §2 Fix 1.

Failing a precondition returns UNINFORMATIVE for that cell. It does not return a failure, and it may
not be worked around by pooling horizons or widening a window after the fact.

## 7. Blindness protocol — the part GRIP-1 got weakest

GRIP-1's anchors were honest but thin: the E9 results commit came **4.5 minutes** after its
results-free tag and E10's came **under 8 minutes**. Both were disclosed as weak anchors, which is
better than hiding them and still not good enough. A gap that short proves only that the author did
not edit the file in between, not that the specification was chosen blind.

Binding for GRIP-2:

1. **This document is tagged results-free** before any GRIP-2 harness code exists, as
   `v2.0.0-prereg`.
2. **A mandatory minimum of 24 hours** elapses between that tag and the grading run. No exceptions,
   and the realised interval is published on the scorecard.
3. **The grading run is executed by a scheduled job, not interactively.** The author does not run it,
   watch it, or have the opportunity to stop it and adjust. The schedule is published in the anchor
   tag, and the run writes its output directly to a release.
   **Scheduled grading run: 26 August 2026, 13:00 UTC** (09:00 America/New_York), executed by a
   scheduled job created at tag time. The realised interval between the tag and the run is
   **approximately 61 hours**, against a 24-hour minimum, and the realised figure is published on
   the scorecard to the second.
4. **Third-party timestamping.** The tag page is submitted to the Internet Archive, and the
   specification hash is posted publicly in a repository issue and archived independently. GitHub's
   own commit timestamps are controlled by the party being audited and are therefore not sufficient
   on their own.
5. **One run.** The harness executes once against the graded sample. Fixing a crash is permitted and
   the diff is published; changing a specification, a feature, a gate or a threshold after the run is
   not, and any such change makes the result a numbered attempt under §8 rather than a grade.

## 8. Specification budget for GRIP-2

- Total post-hoc attempts permitted: **two**. Both are capped at CANDIDATE and neither can certify
  the cell it was chosen against, exactly as under GRIP-1 §13.
- Every attempt requires its own results-free registration with the full 24-hour anchor gap and its
  own accept rule, power precondition and reject clause fixed in advance.
- An attempt whose accept criterion is a sign flip **must require statistical significance**, not
  sign plus stability alone. This rule exists because E10's P1 passed at t = −0.653 under a criterion
  I wrote myself, and it is the single clearest drafting lesson GRIP-1 produced.
- An attempt may not reintroduce a retired feature, weaken a mandatory control, relax a declared
  threshold, or switch the G1 metric.
- Retired features stay retired across attempts.

## 9. Data classes and sources

Amendment 1 classes carry over: **A** graded, **B** graded with disclosed deviation, **C** diagnostic
forever.

| Source | Class | Note |
|---|---|---|
| [FHFA metro HPI](https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv) | A, standing deviation | no per-release vintage archive; growth rates and own-trend deviations only |
| [Census PEP county estimates](https://www.census.gov/programs-surveys/popest.html) | A | per-vintage archived, which is why vintage locking is real |
| [Census Building Permits](https://www.census.gov/construction/bps/) | A, standing deviation | no vintage archive; lagged to B−1 |
| [Census metro delineations](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html) | A | delineation vintage ≤ origin year |
| [BEA CAINC1](https://apps.bea.gov/regional/zip/CAINC1.zip) | **B** | revises history, no vintage archive |
| [IRS SOI county flows](https://www.irs.gov/statistics/soi-tax-stats-migration-data) | **B** | graded flow targets and network features; filers not people, 20-return threshold, breaks at 2011–12 and 2022–23 |
| [Census ACS county flows](https://www.census.gov/topics/population/migration/guidance/county-to-county-migration-flows.html) | **B** | validation benchmark only; overlapping 5-year releases, carries 90% MOE |
| NFIP claims (OpenFEMA) | **B** | realised paid losses; beat NRI head to head in E8 |
| [FEMA Risk Rating 2.0](https://www.fema.gov/flood-insurance/risk-rating/profiles) | **B** | G6 only; snapshot, small-ZIP suppression |
| FEMA NRI, Treasury FIO | **C** | diagnostic forever, per Amendment 1 |

## 10. Declared out of scope

Named here so that adding one later is visibly a change of scope rather than a quiet extension.

- **ZIP, county and tract cells.** FHFA's [five-digit ZIP index from 1984](https://www.fhfa.gov/hpi/download/annual/hpi_at_zip5.xlsx)
  is where flood and wildfire risk actually varies, and averaging to metros destroys that variation.
  It is also explicitly developmental, annual only, and thin in low-transaction ZIPs. It belongs in
  GRIP-2.1 with its own registration, not smuggled into this one.
- **Pre-2000 migration components.** The harness's Census county-estimate vintages begin at 2001 and
  the verified continuous `DOMESTICMIG` series begins with component year 2000, so the derived
  `y_netdom` starts in 2002 and no attempt may claim otherwise. Whether the 1990s county files separate
  domestic from international migration at all is **not verified** — the relevant layout file is
  inaccessible to our fetcher — so extending back is a research task with an unknown answer, not a
  known impossibility. Note that the IRS flow series does reach back to 1990–1991, so the graded gross
  cells are not bound by this limit; only the derived net series is.
- **Graph neural networks and learned pair embeddings.** Registered as out of scope for the first
  GRIP-2 run, deliberately. They may only be introduced in a later numbered release, and only after
  they have beaten persistence, gravity, and the incumbent ridge on rolling 3- and 5-year holdouts.
  Adding an unexplainable estimator before the explainable baselines are settled would make a failure
  uninterpretable.
- **Pre-2003 metro geography.** Units were MSAs and PMSAs before 2003, a genuine discontinuity rather
  than a missing file. `y_hpi` origins before 2003 rely on FHFA's own current-definition history,
  which is anachronistic by FHFA's construction, and this is disclosed on every affected cell.
- **HUD-USPS address vacancy data.** Access is [restricted to governmental entities and registered
  non-profits](https://www.huduser.gov/portal/datasets/usps.html). We do not qualify. Not used.
- **Zillow and Redfin research files.** Free to download but
  [licensed with attribution](https://www.zillowgroup.com/developers/api/public-data/real-estate-metrics/)
  rather than public domain, and Zillow restates history monthly. Excluded from graded use.
- **Any licensed dataset.** Unchanged standing constraint.

## 11. What would falsify GRIP-2's premises

Stated now so it cannot be renegotiated later.

- If `hpi_income_gap` fails to carry a negative sign on a blind sample it did not help select, then
  the affordability mechanism is not present at these horizons and Geometryx should stop encoding it
  and say so publicly. E10 is not evidence against this outcome; E10 chose that feature.
- If gross inflow and outflow prove no more forecastable than `y_pop` once natural increase is
  removed, then the between-metro fit that E9 exposed is not an artifact of the target, and the honest
  conclusion is that metro migration is close to unforecastable at five years with public data. That
  conclusion would be published as prominently as any pass.
- If the pair-level cell fails to beat **persistence**, the flow turn is wrong and the added complexity
  is not paid for. Beating gravity but not persistence counts as a failure, not a partial success.
- If IRS and ACS flows disagree materially, the target definition is wrong and GRIP-2 pauses rather
  than grading against a measure it cannot corroborate.
- If no graded cell can reach **10 clusters** under a scheme allowing within-period cross-metro
  correlation, then GRIP-2 cannot certify anything at all with this data, and the correct output is a
  protocol that says so rather than a certificate issued on inference we know to be too generous.
- If G6 shows no price response to an administratively imposed flood-insurance repricing, then the
  insurance-cost channel is weaker than the entire product thesis assumes, and that is the most
  commercially important negative result available to us.

## 12. Deviations disclosed in advance

1. FHFA and BEA both revise history without archiving per-release vintages, so features at early
   origins come from files published in 2026. Mitigated by using growth rates and own-trend
   deviations, never cross-metro levels. This is the largest standing weakness in the whole protocol
   and it is not solvable with free data.
2. FHFA expresses its full history under current CBSA definitions, so early-year metro geography is
   anachronistic by FHFA's own construction.
3. The derived `y_netdom` stitches two vintages across each decennial reset, and the graded IRS flow
   series has documented breaks at 2011–2012 and 2022–2023; both are reported as mandatory robustness
   splits per §3.
4. G6 identifies the effect of repricing rather than of risk, and its treatment intensity is
   correlated with exposure.
5. IRS flows measure tax filers rather than people and omit non-filers entirely, and between 21% and
   27% of flow volume cannot be placed on a named county edge. Every flow cell publishes its realised
   coverage share.
6. GRIP-1's published graded cells were reported with metro-clustered inference only. That is
   disclosed in §5 G7 and on the public scorecard. The published verdicts are not withdrawn — they were
   all NOT CERTIFIED, and more conservative inference cannot turn a non-certification into a
   certification — but the confidence attached to individual coefficients in those cells was overstated.
7. No licensed or access-restricted data is used anywhere in GRIP-2.

*This product uses FHFA Data but is neither endorsed nor certified by FHFA. Census population
estimates, building permits and metro delineations, BEA regional accounts, FEMA and IRS statistics
are US Government works in the public domain.*

Protocol modelled on [AIMIP](https://allenai.org/blog/aimip) ([code](https://github.com/ai2cm/AIMIP)).

---

## 13. Decisions resolved at tag time

These were the open items in the draft. All five are settled here, before any harness code exists,
and none may be revisited before the run.

1. **Scheduled run time: 26 August 2026, 13:00 UTC.** Fixed in §7.3. Roughly 61 hours after this tag,
   not the 24-hour minimum, because the harness has to be written between the two and a longer gap is
   the more credible anchor.
2. **G1's 5-of-7 and G2's 60% stand unchanged.** They are carried from GRIP-1 rather than derived, and
   that is a real weakness — but it is the lesser one. Both thresholds were fixed before GRIP-1's
   outcomes were known, and adjusting them now, with knowledge of exactly which cells missed which
   threshold, is the precise offence this protocol exists to prevent. An arbitrary threshold chosen
   blind is worth more than a defensible one chosen after seeing the answer. They may be re-derived
   in GRIP-3 from a power calculation, before anything is run against them.
3. **The pair-level cell ships in run one.** §3a is graded in this release, not deferred to GRIP-2.1.
   The consequence is accepted explicitly: it needs a new data pipeline over 33 IRS transitions, a
   censored PPML estimator, two-way clustering on both endpoints, and gravity plus persistence
   baselines — all built inside the 61-hour window, and all of it registered blind. If it cannot be
   built in time, the cell returns **UNINFORMATIVE (NOT BUILT)** and that is published as such. It is
   not permitted to slip quietly out of the release, and the graded metro cells do not wait for it.
4. **`y_pop` stays, ungated, with the 83% between-metro finding printed beside it.** Removing a target
   that failed reads as concealment however it is explained. It appears on the scorecard as reported,
   never as graded, with the reason for its ungraded status stated in the same cell.
5. **G6 is deferred to GRIP-2.2 with its own registration.** With §3a in run one, bundling a
   quasi-experimental design on a suppressed snapshot would put the graded cells behind the most
   speculative component. G6 is Class B throughout, so it can neither contaminate nor rescue any
   graded cell, which makes it the cheapest thing to defer and the only one that costs no rigour to
   move. **The accept rule is therefore G1–G5, G7 and G8 in this release**, applied per cell to the
   gates applicable to it. G6 is not weakened, dropped or quietly abandoned; it is unrun.

## 14. What this tag commits us to publishing

Registered now so that a bad outcome cannot be reframed as a partial one.

- Every graded cell's verdict, including UNIDENTIFIED and UNINFORMATIVE cells, with its
  non-overlapping block count and cluster count beside it per G7.
- The realised tag-to-run interval to the second.
- Coverage, mean interval width and per-origin rank correlation for every cell per G8, whether or not
  the accuracy gate passes.
- The realised named-edge coverage share of the IRS flow data per §3, and an UNINFORMATIVE verdict on
  any flow cell falling below the 70% floor.
- If nothing certifies, that result, at the top of the scorecard, in the same position a pass would
  occupy.
