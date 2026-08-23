# E9 — Metro fixed effects and the E5 re-run

Run 2026-08-23T21:18:13Z. Source `fe_diagnostic_20260823T211817Z.json`.

**Registered PROTOCOL.md section 13 as specification attempt 1 of the post-E5 budget, and released results-free as `v1.6.0-prereg` before this script was executed once.**

**Pre-registered verdict: the confound hypothesis is supported in 0/4 cells.** The attempt rejects, by the rule fixed in advance.

## What was asked

Two of three pre-registered shocks fail in all four graded cells, and both
failures route through exactly two coefficients: `hpi_vol_wr`, perturbed by
`premium_shock_40pct`, and `hpi_gap_wr`, perturbed by `rate_shock_200bp`.
Those two are also the only SIGN-UNSTABLE entries in E4. E8 had found the
Treasury FIO premium's positive population coefficient losing significance
once NFIP flood price entered the same regression, which suggested the
premium had been standing in for persistent warm-state characteristics. E9
asks whether the same confound drives these two features: is the wrong sign a
between-metro artefact, or a real within-metro relationship?

Because an `exposed_only` shock response is arithmetically the fitted
coefficient on the perturbed standardised feature, re-running E5 under a new
specification is identically re-estimating those two coefficients. The suite
in `grip/shocks.py` was executed unmodified.

## Results

### Population, h=5

Within-metro share of variance: `hpi_vol` 0.335, `hpi_gap` 0.865. Both clear the 0.10 power precondition, so both signs are readable.

| Spec | n | origins | R² | `hpi_vol` | t | LOO share + | `hpi_gap` | t | LOO share + | rate / premium shock |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 baseline | 2,011 | 9 | 0.5840 | `+0.000557` | +2.86 | 1.000 | `+0.001116` | +3.16 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S0 on S2's rows (control) | 1,549 | 7 | 0.6091 | `+0.000742` | +2.77 | 1.000 | `+0.001347` | +3.58 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S1 within metro | 2,011 | 9 | 0.1012 | `-0.000124` | -0.75 | 0.111 | `+0.000750` | +1.36 | 1.000 | IMPLAUSIBLE / PLAUSIBLE |
| S2 expanding, forecast-legal | 1,549 | 7 | 0.2704 | `-0.000864` | -2.03 | 0.000 | `-0.001961` | -2.12 | 0.000 | PLAUSIBLE / PLAUSIBLE |

### Population, h=3

Within-metro share of variance: `hpi_vol` 0.379, `hpi_gap` 0.886. Both clear the 0.10 power precondition, so both signs are readable.

| Spec | n | origins | R² | `hpi_vol` | t | LOO share + | `hpi_gap` | t | LOO share + | rate / premium shock |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 baseline | 2,234 | 10 | 0.5609 | `+0.000542` | +2.31 | 1.000 | `+0.000420` | +1.71 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S0 on S2's rows (control) | 1,772 | 8 | 0.5653 | `+0.000743` | +2.77 | 1.000 | `+0.000806` | +2.56 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S1 within metro | 2,234 | 10 | 0.0960 | `+0.000231` | +1.23 | 1.000 | `+0.000857` | +1.62 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S2 expanding, forecast-legal | 1,772 | 8 | 0.2518 | `-0.000666` | -1.71 | 0.000 | `-0.002256` | -2.76 | 0.000 | PLAUSIBLE / PLAUSIBLE |

### House price, h=5

Within-metro share of variance: `hpi_vol` 0.335, `hpi_gap` 0.863. Both clear the 0.10 power precondition, so both signs are readable.

| Spec | n | origins | R² | `hpi_vol` | t | LOO share + | `hpi_gap` | t | LOO share + | rate / premium shock |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 baseline | 2,022 | 9 | 0.4655 | `+0.002916` | +3.90 | 1.000 | `+0.005942` | +4.42 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S0 on S2's rows (control) | 1,560 | 7 | 0.4693 | `+0.002188` | +2.70 | 1.000 | `+0.006360` | +4.82 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S1 within metro | 2,022 | 9 | 0.4373 | `-0.000767` | -1.65 | 0.111 | `+0.002712` | +1.38 | 1.000 | IMPLAUSIBLE / PLAUSIBLE |
| S2 expanding, forecast-legal | 1,560 | 7 | 0.3647 | `+0.001196` | +1.63 | 1.000 | `+0.004017` | +2.02 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |

### House price, h=3

Within-metro share of variance: `hpi_vol` 0.380, `hpi_gap` 0.887. Both clear the 0.10 power precondition, so both signs are readable.

| Spec | n | origins | R² | `hpi_vol` | t | LOO share + | `hpi_gap` | t | LOO share + | rate / premium shock |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 baseline | 2,241 | 10 | 0.4649 | `+0.004256` | +5.01 | 1.000 | `+0.005320` | +4.58 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S0 on S2's rows (control) | 1,779 | 8 | 0.4584 | `+0.003480` | +3.64 | 1.000 | `+0.005678` | +4.93 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S1 within metro | 2,241 | 10 | 0.3799 | `+0.001088` | +1.75 | 0.900 | `+0.008087` | +4.54 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |
| S2 expanding, forecast-legal | 1,779 | 8 | 0.3309 | `+0.002215` | +3.22 | 1.000 | `+0.002675` | +1.80 | 1.000 | IMPLAUSIBLE / IMPLAUSIBLE |

t-statistics are OLS with standard errors clustered on metro. Clustering is
not optional here: a five-year forward outcome measured at consecutive origins
overlaps by four years, so within-metro residuals are autocorrelated by
construction. `LOO share +` is the fraction of leave-one-origin-out refits in
which the coefficient is positive; the pre-registered shock sign is negative,
so 0.000 is reliably right and 1.000 is reliably wrong.

## What this settles

**1. The valuation-gap inversion is real, not a confound.** Under the pure
within-metro transformation `hpi_gap` stays positive in all four cells and in
every single leave-one-origin-out refit — 38 of 38 refits positive, reaching t = +4.54. Removing every persistent difference
between metros does not touch it. When a metro is priced further above its own
long-run trend than it usually is, its subsequent growth is *higher*. That is
momentum, it is in the data, and no estimator will remove it. `hpi_gap` is a
momentum term wearing an affordability label, and `rate_shock_200bp` has been
testing mean reversion against a feature that measures its opposite.

**2. The volatility channel is ambiguous rather than vindicated.** `hpi_vol`
does turn negative under S1 in both h=5 cells, but at t = -0.75 and t = -1.65
it is insignificant in both, and it stays positive in both h=3 cells. That is
not evidence of a confound. It is a feature with little to say.

**3. Population growth is almost entirely a between-metro phenomenon.**
Removing metro identity collapses the population fit from 0.584 to 0.101, destroying 83% of it, while the house-price fit
falls only from 0.466 to 0.437, losing 6%. Which
metro you are is nearly the whole population story; prices genuinely have
within-metro dynamics. That asymmetry is a fact about the product, not about
this regression: a population ranking is carried by persistent metro
characteristics, so the honest way to improve it is better cross-sectional
features, not cleverer time-series handling.

**4. The control earned its place, and it cuts the right way.** Restricting to
S2's rows moves `hpi_gap` further positive in 4 of 4 cells, and in
both population cells — the only ones where S2 flips a sign — it moves *both*
focal coefficients further positive: `hpi_gap` at population h=5 goes from
`+0.001116` to `+0.001347`.
So the sample restriction works *against* the negative result, and the
specification, not the smaller sample, is what produces it. Reporting S2
against full-sample S0 alone would have been a mistake dressed as a finding.

The one place the sample effect runs the other way is `hpi_vol` in the two
house-price cells (hpi_h5, hpi_h3), where it becomes less positive on
S2's rows while still staying positive. That does not rescue anything — S2
leaves both house-price shocks IMPLAUSIBLE regardless — but stating it is the
difference between a control and a decoration.

## The part that must not be oversold

In both population cells S2 flips both shocks to PLAUSIBLE, with
`LOO share +` of 0.000 — reliably negative across every refit. P3, as
registered, held there. It would be easy to present that as the shock gate
repaired. It is not, for a reason that has nothing to do with statistics.

S2 redefines the feature. Under S2 `hpi_gap_wr` no longer measures how far a
metro sits above its own long-run trend; it measures how far its gap sits
above its own *recent average* gap, which is a second difference. The shock's
exposed set is defined by a quantile of the perturbed feature, so the exposed
set changes meaning with it: it stops selecting the most overvalued metros and
starts selecting metros whose overvaluation is unusually high for them.
`rate_shock_200bp` as registered asks about metros "already priced furthest
above their own long-run trend". S2 does not answer that question, so S2 has
not passed that shock — it has passed a different one that happens to share a
name. The t-statistics are marginal too (as weak as -1.71, insignificant at 5%)
on 7 to 8 heavily overlapping origins.

Under the section 13 rule S2 is therefore recorded as a **CANDIDATE for the
population target only**, and it carries an extra condition beyond the
standard one: a fresh blind re-registration must re-specify the shock's
exposure against the S2 feature definition. Re-registering the existing shock
text against a redefined feature would be a label error, not a test.

## Consequences

Attempt 1 is spent, and its own reject clause applies: the inversion is
within-metro as well, so the estimator is not the problem and the features
are. **Attempt 2 must not be another estimator.** The route is the one E8
opened — measured transactions rather than constructed proxies. `hpi_vol` was
never an insurance price and is now shown to carry almost no within-metro
information about either target; NFIP realised paid losses already beat the
modelled NRI rate head to head. Replacing the proxy is the remaining move.

Nothing here changes any certification. The four NOT CERTIFIED verdicts in
`v1.0.0-grip1` stand, `premium_shock_40pct` and `rate_shock_200bp` remain
registered as published and remain failing, and E9 was barred from certifying
before it was run.

## Deviation disclosed

One code change landed after the `v1.6.0-prereg` anchor. The cached panels
already carried `*_wr` columns from the graded run, which collided on merge
and raised a `KeyError` on first execution; stale `*_wr` columns are now
dropped at load so every specification is built from raw features only. It is
a mechanical fix, visible in the diff, and it changed no specification, no
prediction and no rule.

## Sources

- Protocol and pre-registration: <https://github.com/Carson2113/geometryx-grip/blob/main/PROTOCOL.md> section 13
- Results-free anchor: <https://github.com/Carson2113/geometryx-grip/releases/tag/v1.6.0-prereg>
- FHFA house price index: <https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv>. This product uses FHFA Data but is neither endorsed nor certified by FHFA.
- Census Population Estimates Program, public domain: <https://www2.census.gov/programs-surveys/popest/datasets/>
- Census Building Permits Survey, public domain: <https://www.census.gov/construction/bps/>
