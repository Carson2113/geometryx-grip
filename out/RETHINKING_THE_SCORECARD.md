# Rethinking the Scorecard: The Ceiling, the Inference Bug, and the Flow Turn

Prepared 23 August 2026. Diagnostic. Nothing here regrades any published cell, and nothing here is
pre-registered. Four independent lines of work: an inference audit I ran on our own panels, a
predictability-ceiling review, a social-physics/migration-modelling review, and hands-on verification
of federal origin–destination flow data.

---

## 1. The honest answer on "as close to 100% as possible"

It is not reachable, and the most authoritative evidence against it is the US Census Bureau grading
its own work at exactly our horizon.

Census evaluated its 1995–2025 state projections over the first five years. Total population came in
at a **MAPE of 2.64%** (Series A). Net domestic migration — the component we propose to forecast —
came in at a **MAPE of 193.3%** (Series A) and **174.2%** (Series B), described in the paper's own
words as "the worst component in the projection"
([Census POP-twps0067](https://www.census.gov/library/working-papers/2002/demo/POP-twps0067.html)).

The Utah cell is the one to remember. Census projected net domestic migration of **+112,548** over
1995–2000. The estimate came in at **−5,247**. Wrong sign, 2,245% absolute error, produced by the
agency that owns the data, at our exact horizon.

Reviewed ceilings for a real-time broad-metro model, with the caveat that direct US-metro studies at
exactly 3–5 years are sparse and the 5-year figures are conservative extrapolation rather than
measured constants (full detail in `research_predictability_ceiling.md`):

| Target | 3-year OOS R² | 5-year OOS R² | 5-year directional |
|---|---|---|---|
| Metro house-price growth | 0.10–0.30 | **0.00–0.20** | 52–62% |
| Metro net domestic migration | 0.00–0.20 | **0.00–0.15** | 50–58% |

The best measured metro price result found is **median OOS R² of 43% at twelve months** across 77
MSAs, quartiles 24–55%
([Rady/UCSD](https://rady.ucsd.edu/_files/faculty-research/timmermann/HSI.pdf)) — a one-year number
that does not carry to five. In a genuine three-year MSA test, RMSE ran **10.1 to 37.6 percentage
points**, with severe local declines frequently forecast as increases
([Lincoln Institute](https://www.lincolninst.edu/app/uploads/legacy-files/pubfiles/2142_1468_Follain_WP12JF1.pdf)).

**Consequence for the scorecard.** If the achievable 5-year R² is 0.00–0.20, then any scoreboard
grading point accuracy will show near-failure forever, for us and for every entrant. That is not a
reason to soften the gates. It is a reason to grade the things that *are* achievable at this horizon
— ranking, calibration, and honest abstention — alongside accuracy, and to say plainly that anyone
advertising high 5-year metro migration accuracy is either overfitting or lying.

## 2. An inference bug, and the reason the scorecard mostly survives it

`grip/fe.py` clusters standard errors on metro. It documents why — overlapping five-year windows make
residuals autocorrelated within a metro — and that reasoning is correct as far as it goes. But metro
clustering assumes metros are **independent of each other within the same year**. Demeaning by
origin × division removes the common mean, not the common factor.

I recomputed the same OLS coefficients under four error assumptions: metro (current), origin year,
non-overlapping horizon-length blocks, and two-way (Cameron-Gelbach-Miller). Coefficients are
identical throughout; only standard errors move. Scripts: `run_se_audit.py`, `run_se_audit_graded.py`.

**On the E10 long panel, where there are enough periods to test, inflation is severe:**

| Cell / feature | t metro | t origin | t block | t two-way |
|---|---|---|---|---|
| LONG h5 `hpi_g1` | +20.858 | +4.682 | **+2.886** | +3.165 |
| LONG h5 `hpi_g5` | −13.031 | −5.874 | **−3.710** | −4.051 |
| LONG h5 `hpi_drawdown` | −9.077 | −4.690 | **−2.869** | −3.091 |
| LONG h5 `hpi_vol` | −2.682 | **−0.767** | −0.461 | −0.505 |
| LONG h5 `hpi_gap` | −0.653 | −0.397 | −0.240 | −0.259 |
| WINDOW h5 `hpi_vol` | **+3.202** | **+1.938** | +1.330 | +1.595 |
| WINDOW h5 `hpi_income_gap` | −2.840 | −2.113 | **−4.186** | −3.615 |
| WINDOW h3 `hpi_income_gap` | −2.632 | −2.319 | −1.745 | **−1.900** |

`hpi_g1`'s t-statistic falls by a factor of **7.2**. The panel has 10,717 rows and 410 metros, but
only **27 origins and 6 non-overlapping blocks**. Rows were never the binding constraint.

Three consequences.

**P3 did not fail — it was never identified.** The wrong-signed `hpi_vol` coefficient that failed P3
sits at t = +1.938 under origin clustering: not distinguishable from zero. Under GRIP-2's own
proposed vocabulary this is **UNIDENTIFIED**, not IMPLAUSIBLE. The concept was invented before the
evidence that it was needed, which is the good order.

**The one clean result gets stronger, not weaker.** `hpi_income_gap` at h=5 survives every scheme and
is *most* significant under block clustering (−4.186). This is now the only feature in the programme
that is robust to how you count independent observations. At h=3 it is marginal (−1.900) and should
not be claimed.

**The published scorecard is mostly intact, but for an uncomfortable reason.** Across the four graded
cells, **35 of 36 coefficients keep significance** under two-way clustering; the sole loss is
`permits_pc` in hpi h3 (−2.274 → −1.913). That looks like vindication and is not. The graded window
has only **2 non-overlapping blocks at h=5**, and the block estimator degenerates there — it returned
t = 161.105 and t = 57.346, which are artifacts of two clusters, not precision. The correct reading is
that the graded cells are too short to test this at all. The published scorecard is not falsified by
this audit; it is shown to rest on an untestable assumption.

This should be disclosed on the site. It is exactly the class of self-caught defect the project claims
to exist for.

## 3. What Pentland's world actually offers, and what it does not

The Pentland-style claim does not transfer directly. Reality-mining results are strong but depend on
data we cannot obtain and would not buy: phone and proximity traces inferred **95% of friendships**
([Eagle, Pentland & Lazer](https://pubmed.ncbi.nlm.nih.gov/19706491/)), and a dormitory study reached
**87.3–90.1%** friendship classification
([Madan & Pentland](https://hd.media.mit.edu/tech-reports/TR-624.pdf)) — both requiring calls,
Bluetooth, SMS and surveys. The frequently cited Eagle-Macy-Claxton result that network diversity
explains "over three quarters of variance" in economic development is a **cross-sectional association
in UK telecom data, not out-of-sample prediction**
([Science](https://www.science.org/doi/abs/10.1126/science.1186605)). Importing it as a forecasting
claim would be exactly the error we accuse others of.

What does transfer is the structural idea: **model the network, not the nodes**. The strongest
directly relevant evidence is a temporally held-out US county-flow study where gradient boosting with
extended features reached **OD-flow R² = 0.81** against 0.59 for extended radiation, with predicted
destination-inflow **R² = 0.89**
([Robinson & Dilkina](https://arxiv.org/pdf/1711.05462)). Those are next-year figures and are not
evidence of 3–5 year performance.

## 4. The flow turn — and the target change that matters most

Two findings collide productively.

Census's evaluation shows **net** domestic migration is catastrophically unforecastable (MAPE 174–193%)
while **gross** flows are far better behaved — earlier Census validation achieved roughly **8–12%**
error for one-to-two-year gross interstate flows
([Census RR90-07](https://www.census.gov/content/dam/Census/library/working-papers/1990/adrm/rr90-07.pdf)).
Net migration is a small difference between two large gross flows, so it inherits the noise of both
and the signal of neither.

**The GRIP-2 draft currently registers `y_netdom`, a net measure. That is the worst-behaved target
available and it should change to gross inflow and outflow rates, with net derived.**

And the flow network is the only way I can see to buy identifying variation without buying data. The
metro panel has 410 units and 27 periods. The directed pair panel has up to ~168,000 ordered pairs
per year, and with origin × year and destination × year fixed effects, identification comes from
*pair-level* variation — which survives the national cycle that swamps everything in the metro panel.
That is a structural increase in information from files we already have.

Hands-on verification (full detail in `research_flows/REPORT.md`):

- **IRS SOI county-to-county** covers **1990→1991 through 2022→2023**, 33 annual transitions
  ([IRS](https://www.irs.gov/statistics/soi-tax-stats-migration-data)). Confirmed nine-column header
  `y2_statefips,y2_countyfips,y1_statefips,y1_countyfips,y1_state,y1_countyname,n1,n2,agi`, with
  130,101 rows in 2011→2012 and 90,048 in 2022→2023. Returns, individuals, and aggregate AGI per edge.
- **Suppression is material and must be registered, not discovered.** Named county edges carry
  **78.67%** of county domestic migration returns in 2011→2012 and **73.23%** in 2022→2023; the rest
  cannot be placed on a named edge. Current county threshold is 20 returns. Series breaks at 2011→2012
  and 2022→2023 ([2022–23 guide](https://www.irs.gov/pub/irs-soi/2223inpublicmigdoc.pdf)).
- **ACS county flows** are 12 overlapping five-year releases, 2005–2009 through 2016–2020 — not an
  annual panel, but they carry 90% margins of error and are not disclosure-suppressed
  ([Census](https://www.census.gov/topics/population/migration/guidance/county-to-county-migration-flows.html)).
- Both aggregate to CBSA with the standard county crosswalk, using vintage-appropriate delineations.

IRS is a filer count with a 20-return threshold, so it is **Class B**, never Class A. ACS is the
uncertainty-aware benchmark, not the panel.

## 5. Ranked changes to GRIP-2, highest leverage first

1. **Replace `y_netdom` with gross inflow and outflow rates; derive net.** Free, and it moves the
   target from a MAPE-193% quantity to one with documented 8–12% short-horizon error. Register net as
   a reported derived quantity so we stay comparable to how the market talks.
2. **Add a pair-level cell with origin × year and destination × year fixed effects.** This is the only
   change that increases identifying variation without new data. Baselines must include persistence
   and a gravity model, because a method that cannot beat persistence is not a method.
3. **Fix inference and make it a gate.** Report metro, origin, block and two-way t-statistics for
   every graded coefficient; grade on the most conservative one with an adequate cluster count;
   publish the number of non-overlapping blocks per cell; and return **UNIDENTIFIED** where the
   cluster count is too small to test — which, on present evidence, is most of the graded window.
4. **Grade calibration and ranking, not only accuracy.** Given a 0.00–0.20 ceiling, add interval
   coverage, rank correlation, and a scored **indeterminate** class that a model is rewarded for using
   honestly. This is the part of the scoreboard that can actually be won.
5. **Correct the published site** with the inference audit, including the finding that the graded
   window is too short to test and that the E10 P3 failure is better described as unidentified.

## 6. What is still unsolved

IRS suppression removes a fifth to a quarter of flow volume from named edges, and non-filers are
missing entirely. The annual flow history is deep but has two documented series breaks. Any
pair-level model still needs future covariates it does not have. And none of this repeals the
ceiling in §1 — the flow turn is a route to the top of the achievable range, not past it.

*This product uses FHFA Data but is neither endorsed nor certified by FHFA. Census, IRS and BEA
statistics are US Government works in the public domain.*
