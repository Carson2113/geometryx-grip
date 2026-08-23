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

python run_backtest.py --horizon 5 --first-origin 2010 --last-origin 2020
python run_backtest.py --horizon 3 --first-origin 2010 --last-origin 2022
python -m grip.scorecard          # renders out/SCORECARD.md
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
| `grip/scorecard.py` | Renders the publishable markdown scorecard |

Features offered to the model, all demeaned within `(origin_year, division)`:

`pop_g1` (the mandatory baseline), `pop_g3`, `pop_accel`, `hpi_g1`, `hpi_g5`,
`hpi_gap` (deviation from the metro's own 15-year log-price trend), `hpi_vol`,
`permits_pc`, `permits_g3`.

## Reference-run result

Read [`out/SCORECARD.md`](out/SCORECARD.md) for the full grading. The headline,
stated plainly because the protocol requires it:

**The multi-feature model is NOT CERTIFIED for forward-looking claims.** Across
7 rolling origins at a 5-year horizon it beat prior one-year within-region
population growth on 3 of 7 origins, with a median paired Spearman gain of
**−0.0117**. At a 3-year horizon it won 1 of 8 origins, paired gain **−0.0162**.

Two of the three pre-registered shocks returned the **wrong sign**: metros
already priced furthest above their own long-run trend, and metros with the
highest price volatility, are currently predicted to do *better* under an
affordability or insurance-cost shock. That is the same inversion already on
record in Geometryx's own data, now measured rather than stumbled upon.

Three findings are genuinely positive:

1. `permits_pc` is the second-strongest stable coefficient after the population
   baseline, sign-stable across every origin, and it is free.
2. `hpi_g5` carries a **stable negative** coefficient across all origins — a
   real mean-reversion signal, not a fit artifact.
3. The clock audit, coefficient-stability test and shock suite all fired on real
   data and caught real problems, including two bugs in this harness itself.

The correct reading is not that the model is bad. It is that the honest test now
exists, and it says: ship the descriptive Index, keep the forecast in the lab,
and let the scoreboard accumulate.

## Known gaps

- Population is the only graded target so far; `y_hpi` is computed but not scored.
- The insurance shock uses `hpi_vol` as a stand-in. It should use the Treasury
  FIO premium series, which is public-domain but ends in 2022.
- No FEMA hazard feature yet. `hazards.fema.gov/nri` now redirects into FEMA's
  Resilience Analysis and Planning Tool; the ICPSR/DataLumos mirror is the
  working archival source.
- Census ACS requires an API key for every request as of ~May 2026.
- No ensemble generator. The protocol mandates ≥5 members; the reference model
  is currently a single ridge fit.

## Attribution

This product uses FHFA Data but is neither endorsed nor certified by FHFA.
Census population estimates, building permits and metro delineations are US
Government works in the public domain.

Protocol modelled on AIMIP ([blog](https://allenai.org/blog/aimip),
[code](https://github.com/ai2cm/AIMIP),
[PCMDI hub](https://github.com/PCMDI/AI-MIP)).
