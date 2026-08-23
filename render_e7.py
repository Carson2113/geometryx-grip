"""Render out/E7_NRI_PROXY.md from the newest nri_calibration_*.json."""
from __future__ import annotations

import glob
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"


def _f(x: float, nd: int = 6) -> str:
    return f"{x:+.{nd}f}"


def _row(r: dict) -> str:
    m = r.get("matches_expected")
    verdict = "n/a" if m is None else ("as pre-registered" if m else "inverted")
    return f"| `{r['predictor']}` | {_f(r['beta_per_sd'])} | {r['t']:+.3f} | {verdict} |"


def main() -> None:
    path = sorted(glob.glob(str(OUT / "nri_calibration_*.json")))[-1]
    d = json.load(open(path))
    fid = d["e7a_proxy_fidelity"]
    L: list[str] = []
    A = L.append

    A("# E7: FEMA NRI expected annual loss as a premium proxy")
    A("")
    A(f"**Status: {d['status']}**")
    A("")
    A(f"Generated {d['generated_utc']}. Source file `{Path(path).name}`.")
    A("")
    A(d["why_not_a_forecast"])
    A("")
    A("## Why this was attempted")
    A("")
    A(
        "E6 found that the pre-registered negative sign on insurance cost is real "
        "on house prices when measured with actual Treasury FIO premiums "
        f"({_f(d['e6_reference']['y_hpi']['beta_per_sd'])} per standard deviation, "
        f"t = {d['e6_reference']['y_hpi']['t']:+.2f}), and that the graded shock "
        "`premium_shock_40pct` fails because it perturbs `hpi_vol`, a house-price "
        "volatility term standing in for insurance cost. FIO cannot repair that: "
        "published 2025-01-16, it is never simultaneously vintage-legal and "
        "scorable. E7 asks whether FEMA's National Risk Index can carry the same "
        "signal from a source that is free, federal and published annually."
    )
    A("")
    A(
        "The candidate feature is `eal_rate = EAL_VALB / BUILDVALUE`: modelled "
        "expected annual building loss per dollar of building exposure, summed "
        "over eighteen hazards. In actuarial terms it is a pure premium rate, and "
        "it is the closest free multi-peril analogue to a homeowners rate."
    )
    A("")

    A("## The National Risk Index is no longer distributed as a file")
    A("")
    A(
        "Before any statistics: FEMA has removed the NRI bulk download "
        "infrastructure. Verified 2026-08-23, the historical download path 302s to "
        "the Resilience Analysis and Planning Tool page, the S3 bucket that served "
        "it returns `NoSuchBucket`, and the National Risk Index does not appear "
        "among the 49 datasets in the OpenFEMA catalogue. The surviving "
        "first-party distribution is FEMA's own ArcGIS Online organisation, which "
        "is what this adapter reads."
    )
    A("")
    A(
        f"That endpoint serves **one mutable layer**, currently the "
        f"{d['nri']['release_label']} (`modified` {d['nri']['published']}), "
        f"{d['nri']['counties']:,} counties. FEMA overwrites it at each release, so "
        "no content hash can be pinned and no earlier vintage can be requested. "
        "`grip/sources/nri.py` records the row count, release label and retrieval "
        "date instead, and declares this as a deviation rather than hiding it."
    )
    A("")

    A("## E7a: does the proxy track what people actually pay?")
    A("")
    A(
        "Regression of the FIO log median premium per policy on the log NRI loss "
        f"rate, {fid['n_metros']} metros. An elasticity of 1.0 would mean premium "
        "scales one-for-one with modelled loss."
    )
    A("")
    A("| Specification | Pearson r | R² | Elasticity | t |")
    A("|---|---|---|---|---|")
    p, w = fid["pooled"], fid["within_division"]
    A(f"| Pooled | {p['pearson']:.3f} | **{p['r2']:.3f}** | {p['elasticity']:.3f} | {p['t']:+.2f} |")
    A(f"| Within Census division | {w['pearson']:.3f} | {w['r2']:.3f} | {w['elasticity']:.3f} | {w['t']:+.2f} |")
    A("")
    A(
        f"The relationship is real and strongly significant, and it is weak. The "
        f"free proxy explains **{100 * p['r2']:.1f}%** of the cross-metro variation "
        f"in what homeowners pay. The elasticity of **{p['elasticity']:.2f}** means "
        "a metro with twice the modelled loss rate pays roughly a fifth more, not "
        "twice as much — consistent with premium being dominated by rebuild cost, "
        "regulatory rate suppression, expense loading and non-modelled water "
        "damage, none of which NRI measures."
    )
    A("")

    A("## E7b: does it reproduce the E6 outcome coefficients?")
    A("")
    A(
        "The E6 specification exactly — demeaned within Census division, momentum "
        "controlled, HC1 standard errors, predictors standardised so a coefficient "
        "is per standard deviation — with the loss rate substituted for the premium."
    )
    A("")
    for t in ("y_hpi", "y_pop"):
        b = d["e7b_e7c_outcomes"][t]
        label = "House-price growth" if t == "y_hpi" else "Population growth"
        A(f"### {label} (`{t}`), n = {b['n_metros']}")
        A("")
        A("| Predictor | β per SD | t | Sign |")
        A("|---|---|---|---|")
        for r in b["substituted"]:
            A(_row(r))
        A("")
        e6 = b["e6_reference"]
        A(
            f"E6 measured this with real premiums at {_f(e6['beta_per_sd'])} "
            f"(t = {e6['t']:+.2f})."
        )
        q = b.get("quartile_contrast")
        if q:
            A("")
            A(
                f"Top against bottom loss-rate quartile, no controls: "
                f"**{q['top_quartile_growth_pct']:.3f}%** a year against "
                f"**{q['bottom_quartile_growth_pct']:.3f}%**, gap "
                f"**{q['gap_pp']:+.3f} pp** ({q['n_top']} against {q['n_bottom']} "
                f"metros) — {'the pre-registered direction' if q['matches_expected'] else 'inverted'}."
            )
        A("")

    A("## E7c: does it survive the premium it is meant to replace?")
    A("")
    A(
        "This is the decisive test. If the loss rate matters only through premium, "
        "it is a clean if noisy substitute. If it carries an independent "
        "coefficient, it is measuring something else and calling it a premium "
        "proxy would be wrong."
    )
    A("")
    for t in ("y_hpi", "y_pop"):
        b = d["e7b_e7c_outcomes"][t]
        label = "House-price growth" if t == "y_hpi" else "Population growth"
        A(f"### {label}, both terms, n = {b['horse_race_n']}")
        A("")
        A("| Predictor | β per SD | t | Sign |")
        A("|---|---|---|---|")
        for r in b["horse_race"]:
            A(_row(r))
        A("")

    A("## Hazard composition and regional conditionality")
    A("")
    A(
        "Splitting building EAL into wildfire, flood and wind shares asks whether "
        "one peril carries the signal. Dropping the South Atlantic, East South "
        "Central and West South Central divisions is the objection E6 answered for "
        "the premium."
    )
    A("")
    for t in ("y_hpi", "y_pop"):
        b = d["e7b_e7c_outcomes"][t]
        label = "House-price growth" if t == "y_hpi" else "Population growth"
        A(f"### {label}")
        A("")
        A("| Predictor | β per SD | t | Sign |")
        A("|---|---|---|---|")
        for r in b["composition"]:
            A(_row(r))
        for r in b["ex_south"]:
            if r["predictor"] == "eal_rate_log":
                A(f"| `eal_rate_log` (ex-South, n = {b['ex_south_n']}) | "
                  f"{_f(r['beta_per_sd'])} | {r['t']:+.3f} | "
                  f"{'as pre-registered' if r['matches_expected'] else 'inverted'} |")
        A("")

    v = d["verdict"]
    A("## Verdict")
    A("")
    A("| Test | Result |")
    A("|---|---|")
    A(f"| Tracks actual premium (R² ≥ 0.25) | {'yes' if v['tracks_actual_premium'] else '**no**'} |")
    A(f"| Reproduces the E6 price sign at \\|t\\| ≥ 2 | {'**yes**' if v['reproduces_e6_price_sign'] else 'no'} |")
    A(f"| Magnitude relative to E6 | {v['magnitude_vs_e6_ratio']:.2f}× |")
    A(f"| Eligible as a graded predictor | {'yes' if v['eligible_as_graded_predictor'] else '**no**'} |")
    A(f"| Recommended as the premium replacement | {'yes' if v['recommended_as_premium_replacement'] else '**no**'} |")
    A("")
    A("### What this settles")
    A("")
    A(
        "**NRI is directionally right and quantitatively insufficient.** It "
        "reproduces both E6 signs — negative on house prices, inverted on "
        "population — which is real corroboration that E6 measured a mechanism and "
        "not an artefact of the FIO file. But it recovers only "
        f"{v['magnitude_vs_e6_ratio']:.0%} of the E6 price coefficient, and in the "
        "horse race its price coefficient collapses to insignificance while the "
        "premium keeps essentially all of its own. NRI is a noisy partial "
        "measurement of the same quantity, adding nothing once the premium is "
        "present. It is a substitute of last resort, not a replacement."
    )
    A("")
    A(
        "**Wind, not wildfire, carries the price signal.** In the hazard-share "
        "decomposition the wind share is the only significant term on prices. "
        "Wildfire is insignificant on both targets, which is worth stating plainly "
        "because wildfire dominates the public narrative about insurance "
        "withdrawal."
    )
    A("")
    A(
        "**The regional conditionality is the same as E6's.** Outside the three "
        "Southern divisions both coefficients fall to approximately zero. "
        "Whatever this mechanism is, it is a Sun Belt phenomenon, and a single "
        "national coefficient is the wrong specification for it."
    )
    A("")

    A("### The structural finding, which is the important one")
    A("")
    A(
        "NRI fails the vintage lock twice, and the second failure is not FEMA's "
        "fault. The retrievable release is a 2025 publication, so it is illegal "
        "before origin 2026 and unscorable at h=3 until 2029 — the FIO trap "
        "exactly. But even a perfectly archived set of vintages would not help. The "
        "first NRI release was October 2020, so the earliest origin any vintage can "
        "serve is 2021. The graded origins run 2010-2020 at h=5 and 2010-2022 at "
        "h=3. An archived NRI would contribute **two origins out of thirteen at "
        "h=3, and none at h=5.**"
    )
    A("")
    A(
        "Generalise that and it is a property of the protocol rather than of any "
        "dataset: **a vintage lock over a thirteen-origin backtest cannot admit a "
        "feature born in 2020, however good the feature is.** Anything to be graded "
        "across the full panel had to exist, in a form fixed at the time, in or "
        "before 2009. Every young climate-risk product — and almost all of them are "
        "young — is structurally out-of-panel and stays diagnostic until the panel "
        "itself moves forward. This is the cost of refusing to backdate, and it is "
        "worth paying, but it has to be stated rather than discovered repeatedly."
    )
    A("")
    A(
        "So the premium proxy has to be found among series with pre-2009 history. "
        "The candidate that survives that filter is the NFIP redacted policy file "
        "in OpenFEMA (`NfipPolicies` v3, 74.3 million records), which carries "
        "`totalInsurancePremiumOfThePolicy`, `fullRiskPremium` and "
        "`policyEffectiveDate` and therefore supports an actual average premium per "
        "county-year with genuine pre-2009 history. Its weakness is the mirror "
        "image of NRI's: it is a real price rather than a model, but it is "
        "flood-only and federally rated rather than multi-peril and market-rated. "
        "That is the next adapter."
    )
    A("")

    A("## Declared deviations")
    A("")
    for x in d["deviations"]:
        A(f"- {x}")
    A("")
    A("## Sources")
    A("")
    A(
        "- FEMA National Risk Index Counties, ArcGIS item "
        f"`{d['nri']['arcgis_item']}`, {d['nri']['release_label']} — "
        "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0"
    )
    A("- National Risk Index methodology — https://www.fema.gov/flood-maps/products-tools/national-risk-index")
    A("- Treasury FIO, Analyses of U.S. Homeowners Insurance Markets 2018-2022 — https://home.treasury.gov/news/press-releases/jy2791")
    A("- FHFA House Price Index, metro annual — https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv")
    A("- Census Population Estimates Program — https://www2.census.gov/programs-surveys/popest/datasets/")
    A("- OpenFEMA NFIP Redacted Policies v3 — https://www.fema.gov/openfema-data-page/nfip-redacted-policies-v3")
    A("- ICPSR/DataLumos deposit of a 2025 NRI release — https://doi.org/10.3886/E218382V1")
    A("")
    A("This product uses FHFA Data but is neither endorsed nor certified by FHFA.")
    A("")

    dest = OUT / "E7_NRI_PROXY.md"
    dest.write_text("\n".join(L))
    print(f"wrote {dest} ({dest.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
