#!/usr/bin/env python3
"""Render out/E6_PREMIUM_SIGN.md from the newest premium diagnostic JSON."""
from __future__ import annotations

import glob
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
LABEL = {
    "premium_log_2022": "Premium level (log median premium per policy, 2022)",
    "premium_g4": "Premium growth (annualised log change 2018-2022)",
    "nonrenewal_2022": "Nonrenewal rate (2022)",
    "pop_g3": "Population momentum (3-year, through 2022)",
    "hpi_g5": "Price momentum (5-year, through 2022)",
}
TNAME = {"y_pop": "Population growth", "y_hpi": "House-price growth"}


def sign_cell(e: dict) -> str:
    mark = "as pre-registered" if e["matches_expected"] else "**inverted**"
    star = "" if e["significant_5pct"] else " (n.s.)"
    return f"{e['beta_per_sd']:+.5f} | {e['t']:+.2f}{star} | {mark}"


def main() -> None:
    p = sorted(glob.glob(str(OUT / "premium_diagnostic_*.json")))[-1]
    d = json.load(open(p))
    cov = d["fio_coverage"]
    L = []
    A = L.append

    A("# E6 — Premium sign diagnostic")
    A("")
    A(f"Generated {d['generated_utc']} · **{d['status']}**")
    A("")
    A("## What this is, and what it is not")
    A("")
    A(
        "GRIP-1 grades a `premium_shock_40pct` counterfactual with a pre-registered "
        "direction of **relative decline**: raise the cost of insuring a home and the "
        "metro should grow relatively more slowly. In all four graded cells that shock "
        "returns the wrong sign. But the feature being shocked is `hpi_vol`, a "
        "house-price volatility term standing in for insurance cost, because no free "
        "premium series existed when the protocol was written."
    )
    A("")
    A(
        "Treasury FIO's Property and Casualty Market Intelligence data is a real "
        "premium series. It is **not eligible to be a graded predictor** and is not "
        "used as one — see the vintage ruling below. This diagnostic asks one "
        "question only: with actual premiums instead of a proxy, does the sign come "
        "out negative as pre-registered? Nothing here is scored and nothing here "
        "enters a certification gate."
    )
    A("")
    A("## Vintage ruling: FIO cannot enter the panel")
    A("")
    for para in d["why_not_graded"].split("\n\n"):
        A(para.replace("\n", " ").strip())
        A("")
    A("## Coverage")
    A("")
    A("| Property | Value |")
    A("|---|---|")
    A(f"| Published | {cov['published']} |")
    A(f"| Content window | {cov['data_years'][0]}–{cov['data_years'][1]} |")
    A(f"| ZIP-year rows | {cov['zip_rows']:,} |")
    A(f"| Unique ZIP Codes | {cov['unique_zips']:,} |")
    A(f"| ZIPs mapping to a metro | {cov['zips_matched_to_metro_pct']}% |")
    A(f"| Metros with premium features | {cov['metros_with_features']} |")
    A(f"| Median covered ZIPs per metro | {cov['median_zips_per_metro']} |")
    A(f"| Median within-metro ZIP coverage | {cov['median_covered_share_pct']}% |")
    A(f"| Eligible as graded predictor | **no** |")
    A("")
    A(
        f"Outcome windows: population {d['outcome_windows']['y_pop']}, "
        f"house prices {d['outcome_windows']['y_hpi']}. Both are annualised growth "
        "measured from the end of the FIO content window forward. All variables are "
        "demeaned within Census division, matching the panel convention, so every "
        "coefficient below is a within-division effect. Standard errors are HC1. "
        "Predictors are standardised, so a coefficient is the change in annualised "
        "growth per one standard deviation of the predictor."
    )
    A("")

    A("## Result")
    A("")
    for r in d["results"]:
        A(f"### {TNAME[r['target']]} ({r['target']}), n = {r['n_metros']} metros")
        A("")
        A("| Predictor | β per SD | t | Sign |")
        A("|---|---|---|---|")
        for c in ("premium_log_2022", "premium_g4", "nonrenewal_2022"):
            A(f"| {LABEL[c]} | {sign_cell(r['with_momentum'][c])} |")
        # The momentum control carries no pre-registered sign, so it gets no verdict.
        cc = r["with_momentum"][r["control"]]
        star = "" if cc["significant_5pct"] else " (n.s.)"
        A(
            f"| {LABEL[r['control']]} (control) | {cc['beta_per_sd']:+.5f} | "
            f"{cc['t']:+.2f}{star} | no pre-registered sign |"
        )
        A("")
        q = r["quartile_contrast"]
        A(
            f"Top vs bottom premium quartile, no controls: "
            f"**{q['high_premium_mean_growth'] * 100:.2f}%** a year in the most "
            f"expensive quartile against **{q['low_premium_mean_growth'] * 100:.2f}%** "
            f"in the cheapest, a gap of {q['difference'] * 100:+.2f} points "
            f"({q['n_high']} and {q['n_low']} metros). "
            + ("Pre-registered direction." if q["matches_expected"] else "**Inverted.**")
        )
        A("")
        e = r["ex_south"]["premium_log_2022"]
        A(
            f"Excluding the South Atlantic, East South Central and West South Central "
            f"divisions (n = {r['ex_south']['n_metros']}), the premium level "
            f"coefficient is {e['beta_per_sd']:+.5f} (t = {e['t']:+.2f}"
            + ("" if e["significant_5pct"] else ", not significant")
            + ")."
        )
        A("")

    A("## Reading")
    A("")
    A(
        "**The proxy was the problem on prices.** With real premiums the price "
        "coefficient is strongly negative and highly significant — the "
        "pre-registered direction. The `hpi_vol` stand-in produced the opposite "
        "sign. That identifies the graded price inversion as a proxy artifact "
        "rather than a broken mechanism, and it names the fix precisely."
    )
    A("")
    A(
        "**The proxy was not the problem on population.** Premium *level* stays "
        "positively signed on population even with real premiums: people kept "
        "moving toward expensive-insurance metros over this window. Both facts hold "
        "at once and are consistent — insurance cost is capitalised into the house "
        "rather than deterring the mover. A high premium shows up as a discount on "
        "the price, not as fewer arrivals."
    )
    A("")
    A(
        "**Premium level and premium growth are different signals.** The annualised "
        "*change* in premium is negatively signed on population while the *level* is "
        "positively signed. Level is confounded with coastal and Sun Belt "
        "desirability; change is closer to a shock. Any future feature should use "
        "both, not one."
    )
    A("")
    A(
        "**Nonrenewal is not a usable cost signal.** It is positively signed on both "
        "targets, reproducing an inversion already on record in Geometryx production."
    )
    A("")
    A(
        "**The effect is regionally conditional.** Drop the three Southern divisions "
        "and the population coefficient turns negative while the price coefficient "
        "loses most of its magnitude. A single global expected sign was the wrong "
        "specification. PROTOCOL section 8 forbids revising a pre-registered sign "
        "after a run, so the correct response is not to flip `premium_shock_40pct` "
        "but to register a new, separately named shock whose expected sign is stated "
        "per target and per region, and to leave the original shock failing on the "
        "record."
    )
    A("")
    A("## Sources")
    A("")
    A(
        "- Treasury FIO, *Analyses of U.S. Homeowners Insurance Markets, 2018-2022: "
        "Climate-Related Risks and Other Factors*, January 2025 — "
        "https://home.treasury.gov/news/press-releases/jy2791"
    )
    A(
        "- Supporting Underlying Metrics workbook — "
        "https://home.treasury.gov/system/files/311/Supporting_Underlying_Metrics_and_"
        "Disclaimer_for_Analyses_of_US_Homeowners_Insurance_Markets_2018-2022.xlsx"
    )
    A(
        "- Census 2020 ZCTA-to-county relationship file — "
        "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
        "tab20_zcta520_county20_natl.txt"
    )
    A(
        "- FHFA House Price Index, metro annual — "
        "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv . "
        "This product uses FHFA Data but is neither endorsed nor certified by FHFA."
    )
    A(
        "- Census Population Estimates Program, county totals — "
        "https://www2.census.gov/programs-surveys/popest/datasets/"
    )
    A("")
    A("## Declared deviations")
    A("")
    for i, dev in enumerate(cov["deviations"], 1):
        A(f"{i}. {dev}")
    A("")

    (OUT / "E6_PREMIUM_SIGN.md").write_text("\n".join(L))
    print("wrote", OUT / "E6_PREMIUM_SIGN.md", len("\n".join(L)), "chars")


if __name__ == "__main__":
    main()
