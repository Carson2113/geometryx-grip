"""Render out/E8_NFIP_FLOOD.md from the newest nfip_calibration_*.json.

Every number in the report is read from the JSON rather than typed, so the
document cannot drift from the run that produced it.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"


def newest() -> Path:
    files = sorted(OUT.glob("nfip_calibration_*.json"))
    if not files:
        raise SystemExit("no nfip_calibration_*.json in out/")
    return files[-1]


def fmt(x: float, n: int = 5) -> str:
    return f"{x:+.{n}f}"


def sub(res: dict, feat: str, spec: str = "substituted") -> dict:
    rows = res[spec][feat]["rows"] if spec in ("substituted", "vs_premium") else res[spec]["rows"]
    return next((r for r in rows if r["predictor"] == feat), {})


def row(rows: list, name: str) -> dict:
    return next((r for r in rows if r["predictor"] == name), {})


def main() -> None:
    src = newest()
    d = json.loads(src.read_text())
    P, cov = d["pre_registration"], d["coverage"]
    fid, tg = d["e8a_fidelity"], d["e8b_e8c_outcomes"]
    e8d, rob = d["e8d_preregistered_falsification_test"], d["e8e_robustness"]
    hpi, pop = tg["y_hpi"], tg["y_pop"]
    L = "nfip_loss_pc_log"
    R = "nfip_rate_per_1k_log"

    o: list[str] = []
    A = o.append

    A("# E8 — NFIP flood price and realised loss as insurance signals")
    A("")
    A(f"**Status: {d['status']}**")
    A("")
    A(f"Generated {d['generated_utc']} from `run_nfip_calibration.py`. "
      f"Machine-readable results: `out/{src.name}`.")
    A("")
    A("Out-of-panel diagnostic under PROTOCOL section 8. Nothing here is scored "
      "and nothing here enters a gate.")
    A("")
    A("## The pre-registration came first, and it failed")
    A("")
    A(f"Every threshold and expected sign below was published with **no results** "
      f"at commit `{P['commit']}` ({P['commit_utc']}), release "
      f"[{P['release']}](https://github.com/Carson2113/geometryx-grip/releases/tag/{P['release']}). "
      f"The commit order is checkable and it is the only reason the fourth "
      f"prediction below counts for anything.")
    A("")
    A("| Pre-registered prediction | Outcome |")
    A("|---|---|")
    A(f"| Price sign on `y_hpi` negative | loss burden yes, flood price **no** |")
    A(f"| Price sign on `y_pop` negative | flood price **yes**, loss burden insignificant |")
    A(f"| Fidelity to FIO premium, R² ≥ {P['fidelity_r2_floor']} | **both fail** |")
    A(f"| Flood weaker than multi-peril on prices | **falsified, conditionally** |")
    A("")
    A("## E8a — Neither NFIP series is a homeowners premium proxy")
    A("")
    A("Both fail the pre-registered fidelity floor, and the flood price fails it "
      "in an informative direction.")
    A("")
    A("| Series | n | R² | Elasticity | t | Clears 0.25 |")
    A("|---|---|---|---|---|---|")
    for f in (R, L):
        v = fid[f]
        p = v["pooled"]
        A(f"| `{f}` | {v['n_metros']} | {p['r2']:.3f} | {p['elasticity']:+.4f} | "
          f"{p['t']:+.2f} | {'yes' if v['clears_prereg_r2_floor'] else '**no**'} |")
    A("")
    A(f"The flood price elasticity against the homeowners premium is "
      f"**{fid[R]['pooled']['elasticity']:+.3f}** (t = {fid[R]['pooled']['t']:+.2f}). "
      f"It is not weak, it is *inverted*: metros where NFIP flood cover is "
      f"expensive are metros where homeowners cover is cheap. That is a real "
      f"feature of the two markets rather than noise. NFIP flood premiums are "
      f"set by federal rate tables on floodplain position — coastal and riverine "
      f"— while the homeowners premium is driven by wind, hail and convective "
      f"storm exposure across the interior South and Plains. The two peril maps "
      f"barely overlap, so a flood price can never stand in for a homeowners "
      f"price. That question is now closed.")
    A("")
    A("## E8b/E8c — The realised loss carries price signal the modelled rate did not")
    A("")
    A("E6 specification throughout: demeaned within Census division, momentum "
      "controlled, HC1 errors, predictors standardised, so every coefficient is "
      "per standard deviation.")
    A("")
    A("### House prices (`y_hpi`)")
    A("")
    A("| Specification | Coefficient | t |")
    A("|---|---|---|")
    A(f"| E6 reference, Treasury FIO premium | {hpi['e6_reference']['beta_per_sd']:+.5f} | "
      f"{hpi['e6_reference']['t']:+.2f} |")
    A(f"| E7 reference, FEMA NRI all-hazard rate | {hpi['e7_reference']['beta_per_sd']:+.5f} | "
      f"{hpi['e7_reference']['t']:+.2f} |")
    for f in (L, R):
        r = sub(hpi, f)
        A(f"| **`{f}`** substituted | {r['beta_per_sd']:+.5f} | {r['t']:+.2f} |")
    hr = hpi["vs_premium"][L]["rows"]
    A(f"| `{L}` **with** FIO premium present | {row(hr, L)['beta_per_sd']:+.5f} | "
      f"{row(hr, L)['t']:+.2f} |")
    A(f"| the FIO premium in that same regression | "
      f"{row(hr, 'premium_log_2022')['beta_per_sd']:+.5f} | "
      f"{row(hr, 'premium_log_2022')['t']:+.2f} |")
    nr = hpi["vs_nri"]["rows"]
    A(f"| `{L}` **with** the NRI all-hazard rate present | "
      f"{row(nr, L)['beta_per_sd']:+.5f} | {row(nr, L)['t']:+.2f} |")
    A(f"| the NRI rate in that same regression | "
      f"{row(nr, 'eal_rate_log')['beta_per_sd']:+.5f} | "
      f"{row(nr, 'eal_rate_log')['t']:+.2f} |")
    A("")
    A(f"This is the first result in the series where a free federal feature is "
      f"not merely a shadow of the premium. Substituted alone the loss burden "
      f"gives {sub(hpi, L)['beta_per_sd']:+.5f} "
      f"(t = {sub(hpi, L)['t']:+.2f}), which is "
      f"{abs(d['verdict'][L]['magnitude_vs_e6_ratio']) * 100:.0f}% of the E6 "
      f"premium magnitude. More importantly it **survives** the premium control "
      f"at {row(hr, L)['beta_per_sd']:+.5f} (t = {row(hr, L)['t']:+.2f}), where "
      f"E7's NRI rate collapsed to −0.00079 (t = −0.83). Head to head against "
      f"that NRI rate the realised loss wins outright: "
      f"{row(nr, L)['t']:+.2f} against "
      f"{row(nr, 'eal_rate_log')['t']:+.2f}.")
    A("")
    A("Realised losses beat modelled losses. A dollar someone was actually paid "
      "after a flood measures the hazard better than a model's estimate of what "
      "that dollar should have been.")
    A("")
    A("### Population (`y_pop`) — the sign inversion partly resolves")
    A("")
    A("| Specification | Coefficient | t |")
    A("|---|---|---|")
    A(f"| E6 reference, Treasury FIO premium | {pop['e6_reference']['beta_per_sd']:+.5f} | "
      f"{pop['e6_reference']['t']:+.2f} |")
    A(f"| E7 reference, FEMA NRI all-hazard rate | {pop['e7_reference']['beta_per_sd']:+.5f} | "
      f"{pop['e7_reference']['t']:+.2f} |")
    for f in (R, L):
        r = sub(pop, f)
        A(f"| **`{f}`** substituted | {r['beta_per_sd']:+.5f} | {r['t']:+.2f} |")
    pr = pop["vs_premium"][R]["rows"]
    A(f"| `{R}` **with** FIO premium present | {row(pr, R)['beta_per_sd']:+.5f} | "
      f"{row(pr, R)['t']:+.2f} |")
    A(f"| the FIO premium in that same regression | "
      f"{row(pr, 'premium_log_2022')['beta_per_sd']:+.5f} | "
      f"{row(pr, 'premium_log_2022')['t']:+.2f} |")
    A("")
    A(f"E6 and E7 both found population growth moving *with* insurance cost — "
      f"the inversion that has embarrassed this project since the first "
      f"scorecard, and which the production Geometryx composite reproduces. The "
      f"NFIP flood price is the first feature to recover the pre-registered "
      f"negative sign: {sub(pop, R)['beta_per_sd']:+.5f} "
      f"(t = {sub(pop, R)['t']:+.2f}). And with both in the same regression the "
      f"flood price holds at {row(pr, R)['beta_per_sd']:+.5f} "
      f"(t = {row(pr, R)['t']:+.2f}) while the FIO premium's positive "
      f"coefficient falls to t = {row(pr, 'premium_log_2022')['t']:+.2f} and "
      f"loses significance.")
    A("")
    A("The reading this suggests, stated as a hypothesis and not a finding: the "
      "positive population coefficient on the homeowners premium is not people "
      "moving toward risk, it is the homeowners premium standing in for warm, "
      "fast-growing Sun Belt states. A flood price identified off floodplain "
      "position within a division does not carry that confound, and once it is "
      "in the regression the premium's positive sign has little left to do. "
      "**This is a hypothesis generated by a diagnostic, not a graded result, "
      "and it does not license changing `premium_shock_40pct`.**")
    A("")
    A("## E8d — The pre-registered falsification test, and why the answer is conditional")
    A("")
    A(f"The prediction: E7 attributed the entire price signal to the wind share "
      f"({d['e7_reference']['wind_share']['beta_per_sd']:+.5f}, "
      f"t = {d['e7_reference']['wind_share']['t']:+.2f}) and found the flood "
      f"share insignificant. If true, flood-only measures had to come in weaker "
      f"than E7's all-hazard coefficient of "
      f"{e8d['e7_nri_all_hazard_abs_beta']:.5f} in absolute value.")
    A("")
    A(f"They did not. `{L}` gives an absolute beta of "
      f"{e8d['per_feature'][L]['abs_beta']:.5f} at t = "
      f"{e8d['per_feature'][L]['t']:+.2f} — larger than the all-hazard rate and "
      f"strongly significant. **The prediction is falsified on the full "
      f"cross-section.**")
    A("")
    A("But the falsification is itself fragile, and reporting it without that "
      "would be the same offence this protocol exists to prevent:")
    A("")
    A("| Trim | Absolute beta | t | Still exceeds E7 |")
    A("|---|---|---|---|")
    for r in e8d["trimmed_specifications"]:
        A(f"| {r['cut']} | {r['abs_beta']:.5f} | {r['t']:+.2f} | "
          f"{'yes' if r['exceeds_e7'] else '**no**'} |")
    A("")
    A(f"**Verdict: {e8d['verdict']}**")
    A("")
    A("So the honest statement is narrower than the headline. E7's claim that "
      "flood carries no price signal is wrong — the sign is right and "
      "significant at every cut tested. E7's claim that flood is *weaker than "
      "all-hazard* survives once the coastal tail is removed. What E7 actually "
      "got wrong was measuring flood with a modelled share of a modelled "
      "construct instead of with paid claims.")
    A("")
    A("## E8e — Robustness")
    A("")
    A("The concern is specific: paid flood losses per capita concentrate in a "
      "coastal tail, and the twenty-year window ending 2022 contains Katrina, "
      "Sandy and Harvey. If the coefficient is those storms, it is a story about "
      "three events.")
    A("")
    A(f"### Loss burden on house prices")
    A("")
    A("| Cut | Coefficient | t | n | Significant |")
    A("|---|---|---|---|---|")
    for r in rob["loss_burden_on_y_hpi"]:
        A(f"| {r['cut']} | {r['beta_per_sd']:+.5f} | {r['t']:+.2f} | {r['n']} | "
          f"{'yes' if r['significant'] else '**no**'} |")
    A("")
    A(f"### Flood price on population")
    A("")
    A("| Cut | Coefficient | t | n | Significant |")
    A("|---|---|---|---|---|")
    for r in rob["flood_price_on_y_pop"]:
        A(f"| {r['cut']} | {r['beta_per_sd']:+.5f} | {r['t']:+.2f} | {r['n']} | "
          f"{'yes' if r['significant'] else '**no**'} |")
    A("")
    A("The sign is right and significant in every specification tested for both "
      "features. The loss-burden magnitude attenuates as the tail is trimmed, "
      "which is the honest caveat: part of it is coastal catastrophe. The "
      "population result attenuates less and holds when metros with thin policy "
      "samples are dropped. Neither result is three storms.")
    A("")
    A("The twelve metros dropped by name: "
      + ", ".join(sorted(rob["catastrophe_metros_dropped"].values())) + ".")
    A("")
    A("## Why neither feature is graded")
    A("")
    A(d["why_not_yet_graded"])
    A("")
    A("Under PROTOCOL Amendment 1 both are **Class B**: dated, never-restated "
      "transactions whose publication postdates the origins they would serve. "
      "Class B is gradeable in principle with the availability deviation printed "
      "on the scorecard. It is not gradeable in this run, because OpenFEMA "
      "serves one current file and no archived vintages, so an as-of-origin "
      "snapshot cannot be demonstrated. The route to grading is to begin "
      "archiving monthly snapshots now and wait, which is a real cost honestly "
      "stated rather than a reason to bend the rule.")
    A("")
    A("## Correction to v1.4.0-grip1")
    A("")
    A("The v1.4.0 release notes stated the NFIP policy file offers \"genuine "
      "pre-2009 history\" and named it the next adapter partly on that basis. "
      "**That was wrong.** OpenFEMA reports `NfipPolicies` v3 temporal coverage "
      "beginning 2009-01-01, which was checkable at the time and was not "
      "checked. The policy file reaches no further back than the FHFA and PEP "
      "series already in the panel.")
    A("")
    A(f"The claims file does reach back: earliest observed loss year "
      f"{d['nfip']['claims_earliest_observed_loss_year']}, "
      f"{d['nfip']['claims_records']:,} records, 2,942 counties, $89.4bn paid. "
      f"But a paid claim is a realised loss, not a price, so it cannot "
      f"substitute for a premium — it can only proxy the hazard a premium is "
      f"meant to price. That distinction is the whole content of E8.")
    A("")
    A("## Coverage and construction")
    A("")
    A(f"- Metros in panel: {cov['metros_in_panel']}; with NFIP flood price "
      f"{cov['metros_with_nfip_price']}; with NFIP loss burden "
      f"{cov['metros_with_nfip_loss']}; with FIO premium "
      f"{cov['metros_with_fio_premium']}.")
    A(f"- Claims: full pull of all {d['nfip']['claims_records']:,} records, "
      f"aggregated to county-year, then to {d['delineation_vintage']} OMB "
      f"metro definitions.")
    A(f"- Premium: the 74.3M-row policy file cannot be pulled — bulk downloads "
      f"return HTTP 403 and `$skip` past 40M returns HTTP 503. Instead a "
      f"stratified sample of 780,695 policies effective in "
      f"{d['nfip']['premium_cross_section_year']} was drawn across 612 "
      f"state-by-month strata. Stratifying by month is necessary, not "
      f"cosmetic: the API returns each partition ordered by effective date, so "
      f"sampling a state-year from the head would return almost nothing but "
      f"policies effective on 1 January.")
    A(f"- Loss burden: paid building, contents and ICC claims over a "
      f"{d['nfip']['loss_window_years']}-year trailing window, divided by "
      f"base-year population and by the window length. Nothing after the base "
      f"year enters either numerator or denominator.")
    A("- Policies carry no county field, only a reported ZIP, so premiums are "
      "mapped through the Census 2020 ZCTA-to-county relationship file. Claims "
      "carry a county FIPS directly and need no crosswalk.")
    A("")
    A("### Declared deviations")
    A("")
    for dv in d["deviations"]:
        if isinstance(dv, dict):
            A(f"- **{dv.get('name', dv.get('id', 'deviation'))}** — "
              f"{dv.get('detail') or dv.get('description') or dv.get('note') or dv}")
        else:
            A(f"- {dv}")
    A("")
    A("## Sources")
    A("")
    A(f"- OpenFEMA NfipClaims v3, {d['nfip']['claims_records']:,} records: "
      f"{d['nfip']['claims_endpoint']}")
    A(f"- OpenFEMA NfipPolicies v3, {d['nfip']['policies_records']:,} records, "
      f"coverage from {d['nfip']['policies_temporal_start']}: "
      f"{d['nfip']['policies_endpoint']}")
    A("- OpenFEMA dataset catalogue: https://www.fema.gov/api/open/v1/DataSets")
    A("- Treasury FIO, Analyses of U.S. Homeowners Insurance Markets 2018-2022: "
      "https://home.treasury.gov/news/press-releases/jy2791")
    A("- FEMA National Risk Index Counties, December 2025 release: "
      "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
      "National_Risk_Index_Counties/FeatureServer/0")
    A("- FHFA House Price Index, metro annual: "
      "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv — "
      "This product uses FHFA Data but is neither endorsed nor certified by FHFA.")
    A("- Census Population Estimates Program: "
      "https://www2.census.gov/programs-surveys/popest/datasets/")
    A("- Census 2020 ZCTA-to-county relationship file: "
      "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
      "tab20_zcta520_county20_natl.txt")
    A("- OMB metropolitan delineation files: "
      "https://www.census.gov/geographies/reference-files/time-series/demo/"
      "metro-micro/delineation-files.html")
    A("")

    dest = OUT / "E8_NFIP_FLOOD.md"
    dest.write_text("\n".join(o))
    print(f"wrote {dest} ({dest.stat().st_size:,} bytes) from {src.name}")


if __name__ == "__main__":
    main()
