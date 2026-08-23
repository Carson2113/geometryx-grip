"""Treasury FIO homeowners insurance metrics -> metro-level premium series.

This is the first source in GRIP that is NOT eligible to be a graded predictor,
and the adapter says so in code rather than in a footnote. See VINTAGE_VERDICT.

The Property and Casualty Market Intelligence (PCMI) data call is the only
public-domain, nationwide, ZIP-level record of what homeowners actually pay for
insurance. Every commercial alternative we priced was five to six figures a year.
It exists because FIO, the NAIC and state regulators collected it once, in 2024,
and published it in January 2025 -- and because it was a one-off collection with
no successor, its content window is frozen at 2018-2022.

Source:
  Supporting Underlying Metrics and Disclaimer for Analyses of U.S. Homeowners
  Insurance Markets, 2018-2022
  https://home.treasury.gov/system/files/311/Supporting_Underlying_Metrics_and_Disclaimer_for_Analyses_of_US_Homeowners_Insurance_Markets_2018-2022.xlsx
  Report: Analyses of U.S. Homeowners Insurance Markets, 2018-2022:
  Climate-Related Risks and Other Factors, FIO, January 2025.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from ..fetch import get
from . import cbsa as cbsa_src

FIO_URL = (
    "https://home.treasury.gov/system/files/311/"
    "Supporting_Underlying_Metrics_and_Disclaimer_for_Analyses_of_US_"
    "Homeowners_Insurance_Markets_2018-2022.xlsx"
)
ZCTA_COUNTY_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
    "tab20_zcta520_county20_natl.txt"
)

# Publication date of the report and the accompanying data file.
PUBLISHED = "2025-01-16"
# Content window. Fixed: the data call was a one-off and has no successor.
FIRST_DATA_YEAR = 2018
LAST_DATA_YEAR = 2022

VINTAGE_VERDICT = """\
FIO PCMI is INELIGIBLE as a GRIP-1 graded predictor.

The vintage lock (PROTOCOL section 4) admits a file into origin year Y only if
it was published on or before 31 December Y. FIO PCMI was published 2025-01-16,
so the earliest origin it could serve is 2025. Grading an origin requires the
realised outcome at origin + horizon, which for the shorter graded horizon
(h=3) is 2028. There is therefore no origin at which FIO can currently be both
legal and scorable, and adding it to the panel would be backdating a forecast.

That the content covers 2018-2022 is irrelevant. The lock is on publication,
not on the period described, precisely because a file published later embeds
revisions, hindsight and -- in this case -- a data call designed after the
outcomes it describes had already occurred.

FIO is used here for one thing only: an out-of-panel sign diagnostic that
checks the pre-registered premium_shock direction against real premiums rather
than against the hpi_vol proxy. That diagnostic is descriptive and is reported
as such. It is not a forecast, it is not scored, and it does not enter any
certification gate.
"""

DEVIATIONS = [
    "FIO reports ZIP Codes; the only public-domain national crosswalk is Census "
    "ZCTA-to-county. ZCTAs approximate but do not equal USPS ZIP Codes. Each ZIP "
    "is matched to the identically-numbered ZCTA and assigned to the single county "
    "with the largest land-area overlap, then to that county's CBSA. Split ZIPs "
    "are therefore assigned whole rather than apportioned.",
    "FIO publishes a Policy Decile Grouping (1-10) but not policy counts, so no "
    "exact policy weighting is possible. Metro aggregates use the unweighted "
    "median across covered ZIPs, which is robust to the acknowledged per-ZIP "
    "anomalies; a decile-weighted mean is reported alongside as a robustness "
    "check.",
    "Only ZIP Codes with at least 10 reporting insurers and 50 policies are "
    "published, so coverage is systematically thinner in rural and small-metro "
    "areas. Metro aggregates are suppressed below MIN_ZIPS covered ZIPs and the "
    "covered share is reported per metro.",
    "The FIO report PDF was removed from the Treasury website in autumn 2025 "
    "(Consumer Federation of America). The data workbook still resolves at the "
    "URL above; its sha256 is pinned in this module so a substituted file fails "
    "loudly rather than silently changing results.",
]

# Pinned on first retrieval, 2026-08-23. A mismatch is a hard error.
EXPECTED_SHA256 = "99ff8f67d930232d375d3813ffbacacd2a4a8d932d89c81fd8b17b5a6343672e"

MIN_ZIPS = 3  # metro suppressed below this many covered ZIPs

METRICS = {
    "Premiums Per Policy": "premium",
    "Nonrenewal Rate": "nonrenewal",
    "Loss Ratio": "loss_ratio",
    "Claim Frequency": "claim_freq",
    "Claim Severity": "claim_sev",
}


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw() -> pd.DataFrame:
    """ZIP x year FIO metrics, as published."""
    path = get(FIO_URL, name="fio_homeowners_2018_2022.xlsx", timeout=300)
    digest = _sha256(path)
    if EXPECTED_SHA256 and digest != EXPECTED_SHA256:
        raise RuntimeError(
            f"FIO workbook sha256 changed: expected {EXPECTED_SHA256}, got {digest}. "
            "Treasury may have republished or withdrawn the file; do not proceed "
            "with a silently different dataset."
        )
    df = pd.read_excel(path, sheet_name="Supporting Underlying Metrics")
    df = df.rename(columns={"ZIP Code": "zip", "Year": "year",
                            "Policy Decile Grouping": "decile", **METRICS})
    df["zip"] = df["zip"].astype(int).astype(str).str.zfill(5)
    return df


def zip_to_cbsa(delineation_vintage: int = 2020) -> pd.DataFrame:
    """ZCTA5 -> CBSA via dominant-land-area county. See DEVIATIONS[0]."""
    path = get(ZCTA_COUNTY_URL, name="tab20_zcta520_county20_natl.txt", timeout=120)
    rel = pd.read_csv(path, sep="|", dtype=str, encoding="utf-8-sig")
    rel = rel[rel["GEOID_ZCTA5_20"].notna()].copy()
    rel["area"] = pd.to_numeric(rel["AREALAND_PART"], errors="coerce").fillna(0.0)
    rel = rel.sort_values("area", ascending=False)
    dom = rel.drop_duplicates("GEOID_ZCTA5_20")[["GEOID_ZCTA5_20", "GEOID_COUNTY_20"]]
    dom.columns = ["zip", "fips"]
    dom["zip"] = dom["zip"].str.zfill(5)
    dom["fips"] = dom["fips"].str.zfill(5)

    cw = cbsa_src.crosswalk(delineation_vintage)
    return dom.merge(cw[["fips", "cbsa_code", "cbsa_title"]], on="fips", how="inner")


def metro_metrics(
    delineation_vintage: int = 2020, min_zips: int = MIN_ZIPS
) -> pd.DataFrame:
    """Metro x year insurance metrics, median across covered ZIPs.

    Also returns a decile-weighted mean per metric (suffix `_wmean`) and the
    coverage counts needed to report how thin each metro is.
    """
    df = raw()
    xw = zip_to_cbsa(delineation_vintage)
    m = df.merge(xw, on="zip", how="inner")

    # Total ZCTAs mapped into each metro, for a covered-share denominator.
    zips_in_metro = xw.groupby("cbsa_code")["zip"].nunique().rename("zips_total")

    cols = list(METRICS.values())
    out = []
    for (code, year), grp in m.groupby(["cbsa_code", "year"]):
        if len(grp) < min_zips:
            continue
        row = {
            "cbsa_code": code,
            "cbsa_title": grp["cbsa_title"].iat[0],
            "year": int(year),
            "n_zips": len(grp),
        }
        w = grp["decile"].astype(float).values
        for c in cols:
            v = grp[c].astype(float).values
            row[c] = float(np.median(v))
            row[f"{c}_wmean"] = float(np.average(v, weights=w)) if w.sum() > 0 else np.nan
        out.append(row)

    res = pd.DataFrame(out).merge(zips_in_metro, on="cbsa_code", how="left")
    res["covered_share"] = res["n_zips"] / res["zips_total"]
    return res.sort_values(["cbsa_code", "year"]).reset_index(drop=True)


def metro_premium_features(delineation_vintage: int = 2020) -> pd.DataFrame:
    """One row per metro: premium level and growth over the FIO window.

    `premium_log_2022`  log of median premium per policy in the last data year.
    `premium_g4`        annualised log growth in median premium 2018 -> 2022.
    `nonrenewal_2022`   median nonrenewal rate in the last data year.
    `loss_ratio_mean`   mean of the annual median loss ratios, winsorised at
                        the 1st/99th percentile because FIO warns the per-ZIP
                        loss ratios contain anomalies (this panel contains
                        values from -73 to +318).
    """
    mm = metro_metrics(delineation_vintage)
    wide = mm.pivot(index="cbsa_code", columns="year", values="premium")
    need = [FIRST_DATA_YEAR, LAST_DATA_YEAR]
    wide = wide.dropna(subset=need)

    lr = mm.copy()
    lo, hi = lr["loss_ratio"].quantile([0.01, 0.99])
    lr["loss_ratio_w"] = lr["loss_ratio"].clip(lo, hi)
    lr_mean = lr.groupby("cbsa_code")["loss_ratio_w"].mean().rename("loss_ratio_mean")

    last = mm[mm["year"] == LAST_DATA_YEAR].set_index("cbsa_code")
    span = LAST_DATA_YEAR - FIRST_DATA_YEAR

    feat = pd.DataFrame(index=wide.index)
    feat["premium_log_2022"] = np.log(wide[LAST_DATA_YEAR])
    feat["premium_g4"] = np.log(wide[LAST_DATA_YEAR] / wide[FIRST_DATA_YEAR]) / span
    feat["nonrenewal_2022"] = last["nonrenewal"]
    feat["n_zips"] = last["n_zips"]
    feat["covered_share"] = last["covered_share"]
    feat["cbsa_title"] = last["cbsa_title"]
    feat = feat.join(lr_mean)
    return feat.reset_index()


def coverage_report(delineation_vintage: int = 2020) -> dict:
    df = raw()
    xw = zip_to_cbsa(delineation_vintage)
    matched = df[df["year"] == LAST_DATA_YEAR]["zip"].isin(set(xw["zip"]))
    feat = metro_premium_features(delineation_vintage)
    return {
        "published": PUBLISHED,
        "data_years": [FIRST_DATA_YEAR, LAST_DATA_YEAR],
        "zip_rows": int(len(df)),
        "unique_zips": int(df["zip"].nunique()),
        "zips_matched_to_metro_pct": round(100.0 * float(matched.mean()), 1),
        "metros_with_features": int(len(feat)),
        "median_zips_per_metro": int(feat["n_zips"].median()),
        "median_covered_share_pct": round(100.0 * float(feat["covered_share"].median()), 1),
        "eligible_as_graded_predictor": False,
        "deviations": DEVIATIONS,
    }


if __name__ == "__main__":
    import json

    path = get(FIO_URL, name="fio_homeowners_2018_2022.xlsx", timeout=300)
    print("sha256", _sha256(path))
    print(json.dumps(coverage_report(), indent=2))
