# GRIP-2 §6 precondition check — `y_hpi`

Run under anchor `v2.0.0-prereg`, commit `667be2c0`, specification hash
`f27b2cf9acb0af461d0817a98348ddae8f28175db609d4fc3af6626180d7fceb`.

**Nothing was estimated.** No coefficient, standard error, R², or feature-outcome correlation was
computed or written. `y_hpi` was constructed only to identify rows with a missing outcome, because §6
counts *usable* rows. A single feature-outcome relationship computed here would spend the anchor's
blindness, so `run_precondition_check.py` cannot produce one. Verify by reading it.

## Result

| Cell | Origins | Range | Blocks | Rows | Median metros | G7 scheme | Verdict |
|---|---|---|---|---|---|---|---|
| `PRICE_ONLY_h5` | 27 | 1995–2021 | 6 | 10,717 | 409 | origin | **PRECONDITIONS MET** |
| `PRICE_ONLY_h3` | 29 | 1995–2023 | 10 | 11,536 | 409 | **block** | **PRECONDITIONS MET** |
| `WITH_INCOME_h5` | **19** | 2003–2021 | 4 | 6,305 | 324 | origin | **UNINFORMATIVE** |
| `WITH_INCOME_h3` | 21 | 2003–2023 | 7 | 7,008 | 343 | origin | **PRECONDITIONS MET** |

Thresholds are §6 as tagged: ≥20 origins, median ≥150 metros per origin, ≥60 rows after demeaning,
≥5 metros per demeaning group, ≥10 clusters under the graded scheme.

## The one failure, and why it cannot be worked around

`WITH_INCOME_h5` misses the 20-origin precondition by **one origin**. This is the cell containing
`hpi_income_gap` at a five-year horizon — the only feature in the entire programme that survived every
clustering scheme in the inference audit, and the strongest under block clustering at t = −4.186. It is
the result GRIP-2 was principally built to test, and it is not gradeable.

The bound is arithmetic and closed at both ends:

- **Lower bound, origin 2003.** `hpi_income_gap` needs BEA county personal income aggregated to metros,
  which needs a county→CBSA crosswalk, which under **G4** must come from a delineation vintage at or
  before the origin year. OMB created CBSAs in 2003; before that the units were MSAs and PMSAs, which
  §10 declares out of scope as a genuine discontinuity rather than a missing file. There is no legal
  2002 crosswalk to find.
- **Upper bound, origin 2021.** A five-year target from base 2020 lands on 2025, and 2025 is the last
  complete four-quarter FHFA year (verified: 4 quarters, 410 metros; 2026 has only Q1 and is excluded
  by the `n_q == 4` filter). Origin 2022 needs 2026 data that does not exist yet.

2003 through 2021 inclusive is 19 origins. §6 forbids working around a failed precondition by pooling
horizons or widening a window after the fact, so there is no move available.

**The threshold will not be lowered to 19.** Changing a declared threshold after seeing that a cell
we care about misses it by one is the precise offence this protocol exists to prevent, and it would be
worse here than usual because the cell in question is the one we most want to pass. §6 says a failed
precondition returns UNINFORMATIVE, so `WITH_INCOME_h5` returns UNINFORMATIVE and that is published
next to the cells that pass.

What this cell is *not* is a failure. The five-year affordability result is neither confirmed nor
refuted by GRIP-2 run one. It is untested, for a reason stated in advance, and it becomes gradeable in
**2027** when FHFA publishes a complete 2026 and origin 2022 brings the count to 20 without any
specification change. That is a legitimate GRIP-3 cell.

## Two secondary findings

**A 2003 delineation exists and the harness did not know it.** `grip/sources/cbsa.py` registered 2009
as its earliest vintage, which is why E10's income-gap window started at 2010. Probing Census located
the December 2003 CBSA file (`0312cbsas-csas.xls`, 1,853 rows, same combined-FIPS layout as the 2009
list3 file). The 2004–2008 annual updates are not served at any URL reachable from here, so origins in
2004–2008 correctly inherit the 2003 vintage — the most recent delineation available on or before that
origin. This uses older geography, never newer, so it is G4-legal and is not a relaxation. It moved the
income-gap cells six origins earlier and is the only reason `WITH_INCOME_h3` clears 20 at all.

**Block clustering is reachable at three years and unreachable at five.** `PRICE_ONLY_h3` gets exactly
**10 non-overlapping blocks** and therefore grades on block clustering, G7's most conservative tier.
At five years, thirty-one years of data yield at most 6 blocks, so every five-year cell falls back to
origin clustering permanently. This partially corrects an earlier claim of mine that G7's conservative
tier was decorative — it is decorative at h=5, and fully live at h=3.

## Files

- `run_precondition_check.py` — the check. Fits nothing.
- `probe_delineations.py` — the vintage probe.
- `out/precondition_check.json` — machine-readable result.
- `out/probe_delineations.json` — which vintages are reachable.

*This product uses FHFA Data but is neither endorsed nor certified by FHFA. BEA regional accounts and
Census metro delineations are US Government works in the public domain.*
