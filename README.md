# geometryx-grip

Reference implementation of **GRIP-1**, the Geometryx Relocation Intercomparison
Protocol: a public, vintage-locked evaluation harness for US metro population and
house-price forecasts, built entirely on public-domain federal data.

Read [`PROTOCOL.md`](PROTOCOL.md) first. The protocol is the product; this repo
is the reference implementation that proves it runs.

## Why

Geometryx cannot buy a moat. Parcel and property licences quoted during
diligence ran $25,000 to $135,000 a year, and FRED's terms now prohibit training
any model on its content, so the usual path — buy better data than competitors —
is closed.

[AIMIP](https://allenai.org/blog/aimip) demonstrates the alternative. It holds
authority in machine-learning climate emulation without owning the best model,
because it owns the **experimental design** everyone is graded against. That
position is unoccupied in relocation and climate-insurance forecasting, it costs
nothing to take, and a public timestamped track record cannot be backdated by a
better-funded competitor.

## Install and run

```bash
pip install -r requirements.txt

# two targets x two horizons = the four graded cells
python run_backtest.py --target y_pop_wr --horizon 5 --first-origin 2010 --last-origin 2020
python run_backtest.py --target y_pop_wr --horizon 3 --first-origin 2010 --last-origin 2022
python run_backtest.py --target y_hpi_wr --horizon 5 --first-origin 2010 --last-origin 2020
python run_backtest.py --target y_hpi_wr --horizon 3 --first-origin 2010 --last-origin 2022
python -m grip.scorecard          # renders out/SCORECARD.md

# out-of-panel diagnostics E6 and E7 (descriptive, never scored)
python run_premium_diagnostic.py && python render_e6.py
python run_nri_calibration.py && python render_e7.py
```

First run retrieves roughly 30 federal files and caches them under `cache/`
with a sha256 manifest. Subsequent runs are offline. Expect ~4 minutes cold.

## What it does

| Module | Responsibility |
|---|---|
| `grip/fetch.py` | Cached HTTP with 2 req/s politeness and a sha256 manifest |
| `grip/sources/cbsa.py` | OMB delineation vintages 2009-2023; boundary-comparable metro sets |
| `grip/sources/pep.py` | Per-vintage Census population; the vintage stack that enforces the lock |
| `grip/sources/fhfa.py` | Metro quarterly HPI, annualised |
| `grip/sources/bps.py` | Census Building Permits Survey, metro annual totals |
| `grip/panel.py` | Vintage-locked feature builder and within-region/within-origin demeaning |
| `grip/leakage.py` | CLOCK_LEAK audit and frozen-percentile assertions |
| `grip/evaluate.py` | Expanding-origin evaluation, bootstrap intervals, coefficient stability |
| `grip/shocks.py` | E5 pre-registered shock suite |
| `grip/sources/fio.py` | Treasury FIO premiums, metro-aggregated. **Ineligible as a predictor** |
| `grip/sources/nri.py` | FEMA National Risk Index expected annual loss. **Ineligible as a predictor** |
| `grip/scorecard.py` | Renders the publishable markdown scorecard |
| `run_premium_diagnostic.py` | E6 out-of-panel premium sign diagnostic |
| `run_nri_calibration.py` | E7 out-of-panel NRI premium-proxy calibration |

Features offered to the model, all demeaned within `(origin_year, division)`:

`pop_g1`, `pop_g3`, `pop_accel`, `hpi_g1`, `hpi_g5`, `hpi_gap` (deviation from
the metro's own 15-year log-price trend), `hpi_vol`, `permits_pc`, `permits_g3`.

Two graded targets, each with its own mandatory baseline — the prior one-year
change in the same quantity being forecast:

| Target | Quantity | Source | Baseline | Metros/origin |
|---|---|---|---|---|
| `y_pop_wr` | annualised population growth | Census PEP | `pop_g1_wr` | 245 |
| `y_hpi_wr` | annualised house-price growth | FHFA HPI | `hpi_g1_wr` | 231 |

## Out-of-panel diagnostics

A diagnostic uses data the graded panel may not use, is never scored, and may
only be cited as evidence about a mechanism or a feature — never as evidence of
skill. PROTOCOL section 8.

[`out/E6_PREMIUM_SIGN.md`](out/E6_PREMIUM_SIGN.md) tests the pre-registered
`premium_shock_40pct` direction against real Treasury FIO premiums instead of the
`hpi_vol` proxy the graded shock perturbs. Premium level carries the
pre-registered negative sign on house prices (−0.0052 per standard deviation,
t = −6.8) and inverts on population (+0.0007, t = +2.1). The graded price
inversion is therefore a proxy failure, and E6 is the calibration target any
vintage-legal premium proxy has to reproduce. The registered shock is not
revised; it stays on the record failing.

[`out/E7_NRI_PROXY.md`](out/E7_NRI_PROXY.md) tests the fix E6 named. FEMA's
National Risk Index expected annual loss per dollar of building exposure explains
13.2% of the cross-metro variation in actual premiums, reproduces both E6 signs at
56% of the E6 price magnitude, and loses its price coefficient entirely in a horse
race against the premium. It corroborates E6 and is not the replacement.

E7 also produced the **minimum-history rule**, now PROTOCOL section 4: a feature
first published in year P can serve no origin before P + 1, so a feature published
after 2009 cannot be graded across the full panel. NRI was first released October
2020 and would reach two of thirteen h=3 origins and none at h=5 even if every
historical vintage were archived. Almost every climate-risk product is younger than
this backtest and is therefore structurally out-of-panel.

## Reference-run result

Read [`out/SCORECARD.md`](out/SCORECARD.md) for the full grading. The headline,
stated plainly because the protocol requires it:

**The multi-feature model is NOT CERTIFIED for forward-looking claims in any of
the four graded cells.** Certification is a conjunction of four gates, not a
skill score:

| Cell | Skill | Shock signs | Interval | Members | Certified |
|---|---|---|---|---|---|
| `y_pop_wr` h=5 | 3/7 | 2 of 3 wrong | 89.2% | 35.2% | no |
| `y_pop_wr` h=3 | 1/8 | 2 of 3 wrong | 90.7% | 18.2% | no |
| `y_hpi_wr` h=5 | **4/7** | 2 of 3 wrong | **93.0%** | **52.5%** | no |
| `y_hpi_wr` h=3 | 3/8 | 2 of 3 wrong | 92.3% | 29.6% | no |

Three results are worth stating plainly.

**1. The shock inversion is in the features, not in the target.** House-price
growth is a separate outcome variable from a separate federal source with its
own baseline, and it reproduces both wrong-signed shocks at roughly **five times
the magnitude**: the affordability shock moves the most over-trend metros
`+0.0059` on prices against `+0.0011` on population, and the insurance-cost
shock `+0.0029` against `+0.0006`. Prices are the shorter causal path for both
mechanisms — affordability constraint and insurance-cost capitalisation act on
price directly and on population only through a subsequent migration response —
so this is precisely where a real mechanism should have appeared with the right
sign. It did not. Note also that the two coefficients driving these responses,
`hpi_gap_wr` and `hpi_vol_wr`, are both **SIGN-UNSTABLE** on the price target.

**2. One cell is barred by the shock gate alone.** `y_hpi_wr` at h=5 clears
skill (4 of 7 origins, paired Spearman gain **+0.0138**), member robustness
(52.5%) and interval calibration (93.0%). It more than doubles its baseline's
out-of-sample R² — **0.368 against 0.161**. Its only binding constraint is the
pre-registered shock signs. That is a considerably more useful result than a flat
failure, because it names exactly one thing to fix.

**3. The verdict logic itself was wrong until this release.** Certification was
graded on the rolling-origin win count alone. That defect was latent for as long
as the model lost the skill gate, and `y_hpi_wr` at h=5 is the first cell that
would have been mislabelled **CERTIFIED** while inverting both the affordability
and the insurance shock. A model that appreciates the most over-trend and the
most hazard-exposed metros fastest ranks metros well for the wrong reason. The
gate is now an explicit conjunction, and expected shock signs may never be
revised after a target is run — the signs graded here were registered in release
`v1.0.0-grip1`, published before `y_hpi` was ever scored.

Genuinely positive findings:

1. `permits_pc` is sign-stable across every origin on the population target, and
   it is free.
2. `hpi_g5` carries a **stable negative** coefficient on both targets, and on the
   price target it is the single largest stable coefficient (mean **−0.0148**) —
   mean reversion in metro house prices is the most robust mechanism in this
   panel.
3. The clock audit, coefficient-stability test and shock suite all fired on real
   data and caught real problems, including three bugs in this harness itself.
4. **The 90% predictive interval is calibrated in all four cells**, 89.2% to
   93.0% realised coverage against a nominal 90%, measured out-of-sample on
   origins the interval was never fitted to. Calibration is the one property that
   survives every target and horizon tested, which makes a stated uncertainty
   band the first thing here safe to publish.

The correct reading is not that the model is bad. It is that the honest test now
exists, it is specific about what fails, and it says: ship the descriptive Index,
keep the forecast in the lab, and fix the hazard and affordability features
before anything is sold as forward-looking.

## Known gaps

- Both graded targets are outcome variables, not intermediate quantities. Metro
  rents, vacancy and net domestic migration are not yet graded.
- The insurance shock uses `hpi_vol` as a stand-in. It should use the Treasury
  FIO premium series, which is public-domain but ends in 2022.
- No FEMA hazard feature yet. `hazards.fema.gov/nri` now redirects into FEMA's
  Resilience Analysis and Planning Tool; the ICPSR/DataLumos mirror is the
  working archival source.
- Census ACS requires an API key for every request as of ~May 2026.
- Member spread is parameter uncertainty only, roughly a tenth of the realised
  forecast error. The reportable interval is the residual-widened predictive
  interval, not the member spread. See PROTOCOL.md section 9.

## Attribution

This product uses FHFA Data but is neither endorsed nor certified by FHFA.
Census population estimates, building permits and metro delineations are US
Government works in the public domain.

Protocol modelled on AIMIP ([blog](https://allenai.org/blog/aimip),
[code](https://github.com/ai2cm/AIMIP),
[PCMDI hub](https://github.com/PCMDI/AI-MIP)).
