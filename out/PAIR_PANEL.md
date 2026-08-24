# The §3a pair cell is built, and it returns UNINFORMATIVE

Run under anchor `v2.0.0-prereg`, specification hash
`f27b2cf9acb0af461d0817a98348ddae8f28175db609d4fc3af6626180d7fceb`.

**Nothing was estimated.** No censored PPML, no persistence baseline, no gravity baseline, no
coefficient, no standard error. `build_pair_panel.py` counts available data and stops. The estimator
is deliberately absent until the scheduled grading run.

## Verdict

| Cell | Origins | Range | Median pairs at base | Two-way clusters | Verdict |
|---|---|---|---|---|---|
| `FLOW_PAIR_h5` | 17 | 2003–2019 | **19,998** | 361 | **UNINFORMATIVE** |
| `FLOW_PAIR_h3` | 19 | 2003–2021 | **19,644** | 361 | **UNINFORMATIVE** |

§6 requires ≥15 origins, median ≥20,000 named directed pairs per origin, and named-edge coverage
≥70% of flow volume. Origin counts and cluster counts pass comfortably. The pair counts do not.

`FLOW_PAIR_h5` misses the 20,000-pair median by **two pairs.** That is the third cell in this
programme to fail a registered threshold by a hair, after `WITH_INCOME_h5` missed 20 origins by one.

### The verdict survives the one ambiguity in §6

§6 says "median ≥ 20,000 named directed pairs per origin" without pinning whether the count is taken
at the base year or across the cell's whole year span. Having now seen the numbers, I am not entitled
to pick the reading that passes, so both are reported:

| Cell | Median at base | Median over span | Origins surviving the 70% rule applied per origin |
|---|---|---|---|
| `FLOW_PAIR_h5` | 19,998 (fail) | 20,050 (**pass**) | 11 of 17 → fails ≥15 origins |
| `FLOW_PAIR_h3` | 19,644 (fail) | 19,809 (fail) | 15 of 19 → passes ≥15 origins |

Both cells are UNINFORMATIVE under either reading, but by different failing checks. `h5` fails the
pair median at base and, if you take the span reading that clears it, then fails the origin count once
the coverage rule is applied per origin. `h3` fails the pair median under both readings. The ambiguity
is a real defect in the frozen text and should be pinned in GRIP-3 — but it does not decide anything
here, which is the only reason it is safe for me to describe it now.

Named-edge coverage is 69.64% in flow year 2015, below the 70% floor, and 71.9%–78.7% everywhere
else. 2015 is the single year that fails outright.

## §3a overstated the available pair count by about tenfold

The registration says the pair panel offers "up to roughly **168,000** ordered metro pairs per year
from files already in hand." That is wrong, and it is my error, now frozen into the anchor where I
cannot edit it.

168,000 is the number of *possible* ordered pairs among 410 metros (410 × 409 = 167,690). The number
IRS actually *releases* is an order of magnitude smaller, because a county pair below the disclosure
threshold is never published:

| Flow year | Released metro pairs | Named coverage |
|---|---|---|
| 2012 | 22,799 | 78.7% |
| 2013 | 23,288 | 78.6% |
| 2014 | 12,103 | 72.0% |
| 2015 | **9,579** | 69.6% |
| 2016 | 12,538 | 72.4% |
| 2020 | 13,563 | 74.1% |

So the true figure is roughly **20,000 pairs before 2014 and 10,000–13,000 after**, i.e. about 6–14%
of the possible pair space. The structural argument for the pair cell — that it buys identifying
variation without buying data — is much weaker than registered. It is not empty: 20,000 rows against
361 origin clusters and 361 destination clusters is still far more variation than 410 metros across
27 origins. But it is not the tenfold gain §3a claimed.

**Released pairs roughly halve after 2013.** The disclosure threshold rose from 10 to 20 returns with
the 2011–2012 transition, yet the collapse appears in 2014, so the threshold change alone does not
explain it; the IRS also documents an unpublished percentage rule excluding certain dominant-return
cells. Either way this is a **disclosure-rule break in the middle of the panel**, and it is not
benign. Origin × year and destination × year fixed effects absorb shifts common to a year, but this
one bites hardest on pairs made of small counties, so it is not fully absorbed. Any future pair result
spanning 2013–2014 has a regime change inside it.

## §3a's suppression requirement cannot be met as written

§3a requires that "suppressed edges are a modelled state, not a dropped row," on the correct reasoning
that suppression is a function of flow size, so dropping suppressed rows conditions on the outcome.

The files do not support that design. Every row carrying `n1 = -1` — 6,433 in flow year 2012, 5,818 in
2023 — is an aggregate, a foreign row, or an "Other flows" bucket. **Not one is a named county pair.**
A suppressed pair is not a row with a withheld value; it is a row that does not exist, with its mass
folded into the regional 58/59 totals.

There is consequently no per-pair flag to model. The censoring that actually exists is:

> for any ordered pair absent from the file, the flow lies in [0, threshold − 1], and the 58/59 rows
> give the row-sum of all such hidden mass per destination and region.

That is interval censoring under an aggregate constraint. A hurdle model can represent it, but a true
zero is not separable from a small suppressed flow, which is a weaker identification claim than §3a
assumes. The requirement's *intent* is satisfiable; its literal text is not.

## What was built

- `grip/sources/irs_flows.py` — loader spanning three publication eras: per-state Excel inside
  `<y1>to<y2>countymigration.zip` for flow years ≤2004, and national CSVs from 2005, in two header
  dialects (`State_Code_Dest…` for 2005–2011, `y2_statefips…` from 2012). Columns are read positionally
  with the dialect asserted first, so an unknown fourth layout fails loudly rather than mis-mapping.
- `build_pair_panel.py` — panel builder and precondition check. Fits nothing.
- `panel/pair_flows_v{2003,2009,2013,2015,2017,2018,2020}.parquet` — directed CBSA-pair flows, flow
  years 2002–2023, one file per delineation vintage.
- `out/flow_coverage.json`, `out/flow_preconditions.json`.

Three correctness details worth recording, because each one silently corrupts the panel if missed:

1. **Non-migrants.** Every county file carries a self-referential `X County Non-Migrants` row counting
   filers who did *not* move. Both endpoints are real counties, so it passes any endpoint test. In
   flow year 2004 these are the twelve largest apparent edges and inflate released mass **fifteenfold**
   (102.8M returns against a true domestic total of 6.9M).
2. **Pseudo-FIPS aggregates.** Origin codes 96, 97, 98, 58 and 59 are totals and residuals, not
   places. Summing all rows double counts migration several times.
3. **Encoding.** The CSVs are Latin-1, not UTF-8; Puerto Rico county names break a UTF-8 read.

**The loader validates against an independent earlier measurement.** Computed here from the legacy and
modern readers: flow year 2012 gives 89,527 named county edges carrying 6,213,920 returns, 78.67%
coverage; flow year 2023 gives 53,614 edges carrying 6,482,290 returns, 73.23%. Those reproduce, to
the digit, figures I derived separately before this loader existed. That is meaningful because the same
code path also produces the pre-2005 Excel era, which had no independent check.

## Geography rule applied

A cell's geography is fixed at its **origin** year and that single delineation vintage is applied to
every flow year in the cell, including target years after it. Using a later vintage for later target
years would let a boundary revision leak into the outcome. This is why the panel is stored per vintage
rather than once.

The G4 delineation floor binds here exactly as it did for income: the earliest CBSA delineation is
December 2003, so the earliest legal origin is 2003 and the earliest base 2002. IRS publishes county
flows back to 1990–1991, and **none of that depth is reachable** — flow years 1992–2001 exist, parse in
principle, and cannot enter any gradeable cell. The 1990–1991 and 1991–1992 fixed-width text archives
are therefore not implemented, which costs nothing.

## What this means for run one

The pair cell was the answer to the metro panel's core weakness: 410 units across 27 origins and 6
non-overlapping blocks, where the binding constraint is independent time periods rather than rows. §13
decision 3 committed the cell to run one, with UNINFORMATIVE (NOT BUILT) as the penalty for missing.

It is built, on time, and it returns UNINFORMATIVE for a better reason than not being built: the data
was measured and found insufficient against thresholds fixed in advance. Run one therefore grades
three price cells and no flow-pair cell.

`FLOW_PAIR_h5` becomes reachable in **2027** without any specification change, when flow year 2025
arrives and the median can be taken over origins that avoid 2015. That is a GRIP-3 cell, and the
honest version of it should pin the median definition first.

*IRS SOI migration data and Census metro delineation files are US Government works in the public
domain. Source: https://www.irs.gov/statistics/soi-tax-stats-migration-data*
