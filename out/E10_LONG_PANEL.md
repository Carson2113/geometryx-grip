# E10 — The Long Panel (attempt 2)

**Registered results-free** at `v1.7.0-prereg`, commit `89b98a19931368b98f0ab906aab6db8719bf544f`,
before the estimation script existed. Predictions, accept rule and reject clause: PROTOCOL.md §14.

**Verdict: SUPPORTED** — P4 passed, P1 and P2 both hold, no sign split between the primary and
secondary WINDOW variants.

**Status: CANDIDATE.** §13 caps any specification chosen with knowledge of a graded failure. This
does **not** re-grade `v1.0.0-grip1`, does not revise `rate_shock_200bp` or `premium_shock_40pct`,
and certifies nothing. The four NOT CERTIFIED verdicts stand.

Read §4 before quoting the headline. The verdict is real, but P1 passed weakly and P3 failed, and
the post-hoc decomposition shows the mechanism is not the one the memo advertised.

---

## 1. Cells

Target `y_hpi` throughout. Feature and target formulas copied verbatim from `grip/panel.py`;
estimation path untouched (same `RidgeCV(alphas=np.logspace(-3, 3, 25))`, same
`(origin_year, division)` demeaning, same metro-clustered OLS, same leave-one-origin-out refits).

| Cell | Origins | Metros | Rows | Median metros/origin |
|---|---|---|---|---|
| LONG h=5 | 27 (1995–2021) | 410 | 10,717 | 409 |
| LONG h=3 | 29 (1995–2023) | 410 | 11,536 | 409 |
| WINDOW h=5 | 12 (2010–2021) | 348 | 4,078 | 344 |
| WINDOW h=3 | 14 (2010–2023) | 361 | 4,781 | 344 |

BEA county match rate was **1.000 at the median in every WINDOW origin**, so the Virginia
combination-code concern registered in §14.10 did not bite. WINDOW covers 348 rather than 410
metros because it additionally requires a CBSA delineation crosswalk.

Zero new data was needed for LONG. The FHFA file already in cache spans 1975–2025.

## 2. LONG h=5 — 27 origins, no population or permit features

| Feature | Ridge coef | t (clustered) | 5% sig | LOO share positive | Refits |
|---|---|---|---|---|---|
| `hpi_g1` | +0.009287 | +20.858 | yes | 1.000 | 27 |
| `hpi_g5` | −0.009816 | −13.031 | yes | 0.000 | 27 |
| **`hpi_gap`** | **−0.000621** | **−0.653** | no | **0.000** | 27 |
| **`hpi_vol`** | **−0.001418** | **−2.682** | yes | **0.000** | 27 |
| `hpi_drawdown` | −0.004711 | −9.077 | yes | 0.000 | 27 |

Both focal features carry their registered negative sign, and neither flips in any of 27
leave-one-origin-out refits. `hpi_vol` is significant; `hpi_gap` is not.

The two momentum terms separate cleanly and this is the substantive finding of the cell: one-year
growth predicts **more** subsequent growth (t = +20.9) while five-year growth predicts **less**
(t = −13.0). Medium-horizon mean reversion is present in US metro house prices and is very strongly
identified. It simply does not load on `hpi_gap`. We had the mechanism roughly right and the
variable wrong.

`hpi_drawdown` is large and negative in every cell (t = −7.2 to −9.7): a deeper peak-to-trough
decline inside the prior fifteen years predicts stronger subsequent growth. That is the rebound
effect the feature audit said was contaminating the graded window, now measured directly.

## 3. WINDOW h=5 — the income denominator, inside the failing window

| Feature | Ridge coef | t (clustered) | 5% sig | LOO share positive |
|---|---|---|---|---|
| `hpi_g1` | +0.008442 | +15.319 | yes | 1.000 |
| `hpi_g5` | −0.004591 | −4.732 | yes | 0.000 |
| `hpi_gap` | +0.002238 | +1.519 | no | 1.000 |
| `hpi_vol` | +0.002056 | +3.202 | yes | 1.000 |
| `hpi_drawdown` | −0.004557 | −7.219 | yes | 0.000 |
| **`hpi_income_gap`** | **−0.003795** | **−2.840** | yes | **0.000** |

Secondary replacement variant (`hpi_income_gap` in place of `hpi_gap`, §14.9):
**−0.002877, t = −2.778**, share positive 0.000. No sign split.

This is the cleanest result in the cell. Within the same 2010-onward origins where the
denominator-free gap comes out positive, the income-denominated gap comes out **negative and
significant**, at both horizons and in both variants:

| Variant | h=5 | h=3 |
|---|---|---|
| Primary (with `hpi_gap`) | −0.003795, t = −2.840 | −0.004115, t = −2.632 |
| Secondary (replacing `hpi_gap`) | −0.002877, t = −2.778 | −0.001906, t = −2.204 |

Four of four negative, four of four significant, 0.000 share positive in all four. Giving the
valuation gap a denominator is what fixes it, and it works without touching the sample period.

## 4. Registered predictions, judged as written

| | Prediction | Result | Holds |
|---|---|---|---|
| **P1** | `hpi_gap` negative in LONG h=5, LOO share positive < 0.5 | −0.000621, share 0.000, **t = −0.653** | **yes, weakly** |
| **P2** | `hpi_income_gap` negative in WINDOW h=5 primary, share < 0.5 | −0.003795, t = −2.840, share 0.000 | **yes** |
| **P3** | \|t\| on `hpi_vol` < 2.0 in WINDOW h=5 given `hpi_drawdown` | **t = +3.202** | **no** |
| **P4** | LONG ≥ 20 origins and ≥ 150 median metros; WINDOW ≥ 8 origins | 27, 409, 12 | yes |

Accept rule §14.5: P4 passes and both P1 and P2 hold → **SUPPORTED**. P3 is a diagnostic and
cannot change the verdict.

Three honest qualifications, none of which the verdict conveys.

**P1 passed on sign and stability, not on significance.** The accept rule deliberately required a
negative coefficient and LOO sign stability rather than a significant negative, chosen in advance
to avoid rewarding a fishing expedition for stars. That choice was defensible and it let a
coefficient of t = −0.653 count as a pass. The defensible reading of P1 is that **the wrong sign on
`hpi_gap` is destroyed, not reversed.** At no specification anywhere in this cell is `hpi_gap`
significantly negative. In LONG h=3 it is still *positive* (+0.001447, t = +1.892, share positive
1.000); h=3 was pre-declared secondary and excluded from the accept rule, which is the only reason
that does not count against P1. In hindsight the P1 accept criterion was too lenient, and §14.5
should have required significance for a prediction whose whole content is a sign flip.

**P3 was registered in the wrong cell — my error.** The entire diagnosis says the 2010-onward
window is the contaminated sample, and I then registered the `hpi_vol` test *inside* that window.
It failed there: controlling `hpi_drawdown` cuts the coefficient roughly in half but leaves
t = +3.202. In LONG, `hpi_vol` does carry its registered negative sign, significantly, at both
horizons (h=5: −0.001418, t = −2.682, 0 of 27 refits positive; h=3: −0.001846, t = −3.888, 0 of 29).
That is an **unregistered observation** and it is recorded as one. P3 failed as written and is
reported as failed.

**The verdict is not evidence for the memo's headline claim.** See §5.

## 5. Post-hoc decomposition — UNREGISTERED

Which change did the work: the added origins, or the added bust control? Locked verdict, so this
can only weaken the claim. `y_hpi`, h=5.

`hpi_gap`:

| Specification | Origins | n | Coef | t | Share positive |
|---|---|---|---|---|---|
| Graded window, no bust control | 2010–2021 | 4,919 | +0.003439 | +3.471 | 1.000 |
| Graded window, with bust control | 2010–2021 | 4,919 | +0.000517 | +0.507 | 0.750 |
| Full long panel, no bust control | 1995–2021 | 10,717 | +0.001797 | +2.073 | 1.000 |
| Full long panel, with bust control (E10) | 1995–2021 | 10,717 | −0.000621 | −0.653 | 0.000 |
| Added origins only, no bust control | 1995–2009 | 5,798 | −0.000534 | −0.401 | 0.200 |
| Added origins only, with bust control | 1995–2009 | 5,798 | −0.002230 | −1.731 | 0.000 |

`hpi_vol`:

| Specification | Coef | t | Share positive |
|---|---|---|---|
| Graded window, no bust control | +0.006013 | +11.657 | 1.000 |
| Graded window, with bust control | +0.002868 | +4.722 | 1.000 |
| Full long panel, no bust control | +0.001594 | +4.172 | 1.000 |
| Full long panel, with bust control (E10) | −0.001418 | −2.682 | 0.000 |
| Added origins only, no bust control | −0.000323 | −0.443 | 0.267 |
| Added origins only, with bust control | −0.001600 | −2.139 | 0.067 |

What this says, plainly:

1. **The memo overclaimed the sample extension.** For `hpi_gap`, extending the sample alone moves
   the coefficient from +0.0034 to −0.0005, and adding the bust control alone moves it from +0.0034
   to +0.0005. Both routes destroy the wrong sign; neither produces a significant negative; the two
   together produce t = −0.653. The claim that "origins 1995–2009 are the only sample in which the
   registered sign can be identified" is **not supported**. The bust control does comparable work
   inside the existing window.
2. **`hpi_vol` genuinely needs both.** The registered negative sign appears only with the longer
   sample *and* the control. In the graded window the control halves a t of +11.7 to +4.7 and cannot
   finish the job, which is why P3 failed.
3. **The wrong signs were artifacts, and the right signs are weak.** Every one of the six `hpi_gap`
   specifications is statistically indistinguishable from zero except the two contaminated positives.
   The correct summary is that `hpi_gap` carries almost no forecasting content once crash depth is
   accounted for. It was never an affordability variable, and it is not a useful momentum variable
   either, because `hpi_g1` and `hpi_g5` already carry momentum far more sharply.

## 6. What follows

- `hpi_gap` should be **retired as a feature**, not repaired. It is momentum measured badly
  (corr +0.909 with `hpi_g5`, per `out/feature_audit.json`) and it is uninformative once
  `hpi_drawdown` is present.
- `hpi_income_gap` is the replacement, and it earned that on its own evidence rather than by
  sample choice.
- `hpi_drawdown` should be a standing control in every price cell. It is among the strongest
  predictors in every specification here (|t| = 7.2 to 9.7) and its absence is what made the
  graded shocks look wrong.
- The §14.1 disclosure stands and is strengthened: the shock gate as written could not be passed on
  a single-episode sample, and the decomposition now shows the missing ingredient was an explicit
  bust control as much as a longer sample.
- **The reject clause in §14.7 is NOT triggered.** The verdict is SUPPORTED, so the mean-reversion
  mechanism is not declared dead — and independently, `hpi_g5` at t = −13.031 shows medium-horizon
  mean reversion is strongly present. It was the measurement that failed, not the mechanism.
- Re-grading requires a fresh blind re-registration and a full backtest under §13. That is GRIP-2,
  not an amendment to GRIP-1.

## 7. Deviations, as disclosed in §14.8

1. FHFA revises index history; features for a 1995 origin come from the 2026 file. Inherited from
   existing practice, but the long panel enlarges the exposure. FHFA also expresses its full history
   under current CBSA definitions, so early-year metro geography is anachronistic by FHFA's own
   construction.
2. BEA revises personal income history, so WINDOW is **Class B** under Amendment 1, not Class A.
3. LONG is **not comparable to the published scorecard** (§14.6): reduced price-only feature set,
   and it includes origins 2011 and 2021 that the graded panel omits.
4. No licensed data. HUD-USPS address vacancy data excluded — access restricted to governmental
   entities and registered non-profits. Zillow and Redfin excluded from graded use as
   licensed-with-attribution rather than public-domain federal data.

**Sources.** FHFA House Price Index, metro quarterly, public domain:
[hpi_at_metro.csv](https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv).
BEA Regional Economic Accounts CAINC1, county personal income 1969–2024, public domain:
[CAINC1.zip](https://apps.bea.gov/regional/zip/CAINC1.zip).

*This product uses FHFA Data but is neither endorsed nor certified by FHFA.*

Reproduce: `python run_long_panel.py` and `python run_long_panel_decomp.py`. Raw output in
`out/long_panel_*.json` and `out/long_panel_decomp_*.json`.
