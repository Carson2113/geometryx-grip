# E6 — Premium sign diagnostic

Generated 20260823T163139Z · **DESCRIPTIVE -- NOT A GRADED FORECAST**

## What this is, and what it is not

GRIP-1 grades a `premium_shock_40pct` counterfactual with a pre-registered direction of **relative decline**: raise the cost of insuring a home and the metro should grow relatively more slowly. In all four graded cells that shock returns the wrong sign. But the feature being shocked is `hpi_vol`, a house-price volatility term standing in for insurance cost, because no free premium series existed when the protocol was written.

Treasury FIO's Property and Casualty Market Intelligence data is a real premium series. It is **not eligible to be a graded predictor** and is not used as one — see the vintage ruling below. This diagnostic asks one question only: with actual premiums instead of a proxy, does the sign come out negative as pre-registered? Nothing here is scored and nothing here enters a certification gate.

## Vintage ruling: FIO cannot enter the panel

FIO PCMI is INELIGIBLE as a GRIP-1 graded predictor.

The vintage lock (PROTOCOL section 4) admits a file into origin year Y only if it was published on or before 31 December Y. FIO PCMI was published 2025-01-16, so the earliest origin it could serve is 2025. Grading an origin requires the realised outcome at origin + horizon, which for the shorter graded horizon (h=3) is 2028. There is therefore no origin at which FIO can currently be both legal and scorable, and adding it to the panel would be backdating a forecast.

That the content covers 2018-2022 is irrelevant. The lock is on publication, not on the period described, precisely because a file published later embeds revisions, hindsight and -- in this case -- a data call designed after the outcomes it describes had already occurred.

FIO is used here for one thing only: an out-of-panel sign diagnostic that checks the pre-registered premium_shock direction against real premiums rather than against the hpi_vol proxy. That diagnostic is descriptive and is reported as such. It is not a forecast, it is not scored, and it does not enter any certification gate.

## Coverage

| Property | Value |
|---|---|
| Published | 2025-01-16 |
| Content window | 2018–2022 |
| ZIP-year rows | 127,965 |
| Unique ZIP Codes | 25,593 |
| ZIPs mapping to a metro | 62.3% |
| Metros with premium features | 384 |
| Median covered ZIPs per metro | 22 |
| Median within-metro ZIP coverage | 85.0% |
| Eligible as graded predictor | **no** |

Outcome windows: population 2022->2024, house prices 2022->2025. Both are annualised growth measured from the end of the FIO content window forward. All variables are demeaned within Census division, matching the panel convention, so every coefficient below is a within-division effect. Standard errors are HC1. Predictors are standardised, so a coefficient is the change in annualised growth per one standard deviation of the predictor.

## Result

### Population growth (y_pop), n = 380 metros

| Predictor | β per SD | t | Sign |
|---|---|---|---|
| Premium level (log median premium per policy, 2022) | +0.00072 | +2.12 | **inverted** |
| Premium growth (annualised log change 2018-2022) | -0.00120 | -3.46 | as pre-registered |
| Nonrenewal rate (2022) | +0.00078 | +2.41 | **inverted** |
| Population momentum (3-year, through 2022) (control) | +0.00445 | +9.81 | no pre-registered sign |

Top vs bottom premium quartile, no controls: **1.11%** a year in the most expensive quartile against **0.57%** in the cheapest, a gap of +0.53 points (95 and 95 metros). **Inverted.**

Excluding the South Atlantic, East South Central and West South Central divisions (n = 224), the premium level coefficient is -0.00061 (t = -1.34, not significant).

### House-price growth (y_hpi), n = 357 metros

| Predictor | β per SD | t | Sign |
|---|---|---|---|
| Premium level (log median premium per policy, 2022) | -0.00523 | -6.82 | as pre-registered |
| Premium growth (annualised log change 2018-2022) | -0.00062 | -0.64 (n.s.) | as pre-registered |
| Nonrenewal rate (2022) | +0.00211 | +2.39 | **inverted** |
| Price momentum (5-year, through 2022) (control) | -0.00258 | -2.71 | no pre-registered sign |

Top vs bottom premium quartile, no controls: **3.84%** a year in the most expensive quartile against **5.67%** in the cheapest, a gap of -1.84 points (90 and 90 metros). Pre-registered direction.

Excluding the South Atlantic, East South Central and West South Central divisions (n = 211), the premium level coefficient is -0.00157 (t = -1.54, not significant).

## Reading

**The proxy was the problem on prices.** With real premiums the price coefficient is strongly negative and highly significant — the pre-registered direction. The `hpi_vol` stand-in produced the opposite sign. That identifies the graded price inversion as a proxy artifact rather than a broken mechanism, and it names the fix precisely.

**The proxy was not the problem on population.** Premium *level* stays positively signed on population even with real premiums: people kept moving toward expensive-insurance metros over this window. Both facts hold at once and are consistent — insurance cost is capitalised into the house rather than deterring the mover. A high premium shows up as a discount on the price, not as fewer arrivals.

**Premium level and premium growth are different signals.** The annualised *change* in premium is negatively signed on population while the *level* is positively signed. Level is confounded with coastal and Sun Belt desirability; change is closer to a shock. Any future feature should use both, not one.

**Nonrenewal is not a usable cost signal.** It is positively signed on both targets, reproducing an inversion already on record in Geometryx production.

**The effect is regionally conditional.** Drop the three Southern divisions and the population coefficient turns negative while the price coefficient loses most of its magnitude. A single global expected sign was the wrong specification. PROTOCOL section 8 forbids revising a pre-registered sign after a run, so the correct response is not to flip `premium_shock_40pct` but to register a new, separately named shock whose expected sign is stated per target and per region, and to leave the original shock failing on the record.

## Sources

- Treasury FIO, *Analyses of U.S. Homeowners Insurance Markets, 2018-2022: Climate-Related Risks and Other Factors*, January 2025 — https://home.treasury.gov/news/press-releases/jy2791
- Supporting Underlying Metrics workbook — https://home.treasury.gov/system/files/311/Supporting_Underlying_Metrics_and_Disclaimer_for_Analyses_of_US_Homeowners_Insurance_Markets_2018-2022.xlsx
- Census 2020 ZCTA-to-county relationship file — https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt
- FHFA House Price Index, metro annual — https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv . This product uses FHFA Data but is neither endorsed nor certified by FHFA.
- Census Population Estimates Program, county totals — https://www2.census.gov/programs-surveys/popest/datasets/

## Declared deviations

1. FIO reports ZIP Codes; the only public-domain national crosswalk is Census ZCTA-to-county. ZCTAs approximate but do not equal USPS ZIP Codes. Each ZIP is matched to the identically-numbered ZCTA and assigned to the single county with the largest land-area overlap, then to that county's CBSA. Split ZIPs are therefore assigned whole rather than apportioned.
2. FIO publishes a Policy Decile Grouping (1-10) but not policy counts, so no exact policy weighting is possible. Metro aggregates use the unweighted median across covered ZIPs, which is robust to the acknowledged per-ZIP anomalies; a decile-weighted mean is reported alongside as a robustness check.
3. Only ZIP Codes with at least 10 reporting insurers and 50 policies are published, so coverage is systematically thinner in rural and small-metro areas. Metro aggregates are suppressed below MIN_ZIPS covered ZIPs and the covered share is reported per metro.
4. The FIO report PDF was removed from the Treasury website in autumn 2025 (Consumer Federation of America). The data workbook still resolves at the URL above; its sha256 is pinned in this module so a substituted file fails loudly rather than silently changing results.
