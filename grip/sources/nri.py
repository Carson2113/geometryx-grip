"""FEMA National Risk Index -> metro expected-annual-loss rate.

Purpose. Diagnostic E6 (v1.3.0-grip1) showed that the pre-registered negative
sign on insurance cost is real on house prices when measured with actual
Treasury FIO premiums, and that the graded shock fails because it perturbs
`hpi_vol`, a house-price volatility term standing in for insurance cost. FIO
itself cannot enter the graded panel: it was published 2025-01-16, so no origin
exists at which it is both vintage-legal and scorable.

This module is the search for a replacement. FEMA's National Risk Index
publishes, per county, a modelled Expected Annual Loss in dollars for eighteen
natural hazards alongside the building exposure it is computed against. The
ratio

    eal_rate = EAL_VALB / BUILDVALUE

is an expected annual building loss per dollar of building exposure: a pure
premium rate, in the actuarial sense, and the closest free multi-peril analogue
to what a homeowners insurer charges. If it tracks FIO premiums it is a
candidate premium proxy.

Availability. FEMA deleted the National Risk Index download infrastructure
between the 2025 releases and now. Both

    https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload/...
    https://nri-data-downloads.s3.amazonaws.com/...

are gone: the first 302s to the Resilience Analysis and Planning Tool page, the
second returns S3 `NoSuchBucket`. The National Risk Index is also absent from
the OpenFEMA API catalogue (49 datasets, none of them NRI). The surviving
first-party distribution is FEMA's own ArcGIS Online organisation, owner
`FEMA_NationalRiskIndex`, which is what this adapter reads. See ARCHIVE_NOTE.

Source:
  National Risk Index Counties, FEMA, ArcGIS Online item
  39485e8035d446a5bff03259508ae355, tagged "December 2025 Release".
  https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0
  Methodology: National Risk Index Technical Documentation, FEMA.
  https://www.fema.gov/flood-maps/products-tools/national-risk-index
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from ..fetch import CACHE
from . import cbsa as cbsa_src

SERVICE = (
    "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
    "National_Risk_Index_Counties/FeatureServer/0"
)
ITEM = "39485e8035d446a5bff03259508ae355"
PAGE = 2000

# Vintage of the release this adapter actually reads. The ArcGIS item is tagged
# "December 2025 Release" and its `modified` timestamp is 2025-12-18. It is a
# single mutable layer: FEMA overwrites it in place at each release, so there is
# no way to request an earlier vintage from this endpoint.
PUBLISHED = "2025-12-18"
RELEASE_LABEL = "December 2025 Release"

# Original publication dates of the National Risk Index releases, from the
# archived data dictionaries. Recorded because the vintage argument below turns
# on them, and because the files themselves are no longer retrievable.
RELEASES = {
    "1.17.0": "2020-10",  # first public release
    "1.18.0": "2021-08",
    "1.18.1": "2021-11",
    "1.19.0": "2023-03",
    "1.20.0": "2024-03",
    "current": "2025-12",
}

VINTAGE_VERDICT = """\
FEMA NRI is INELIGIBLE as a GRIP-1 graded predictor, for two independent
reasons. Neither is fixable by this adapter.

1. The retrievable file is a 2025 publication. FEMA serves one mutable layer
   and overwrites it at each release. The layer this adapter reads is the
   December 2025 release, so under the vintage lock its earliest legal origin is
   2026 and grading h=3 would require a realised 2029 outcome. This is exactly
   the FIO verdict: legal or scorable, never both.

2. Even with a perfectly archived set of vintages, NRI cannot fill the panel.
   The first public release was October 2020, so the earliest origin any NRI
   vintage can serve is 2021. The graded origins run 2010-2020 at h=5 and
   2010-2022 at h=3. An archived NRI would therefore contribute two origins out
   of thirteen at h=3 and none at all at h=5.

The second reason is the more important one and it is a property of the
protocol, not of FEMA. A vintage lock over a thirteen-origin backtest cannot
admit a dataset born in 2020, however good it is. Any feature that is to be
graded across the full panel must have been published, in a form fixed at the
time, in or before 2009. Datasets younger than the backtest are structurally
out-of-panel and stay diagnostic until the panel itself moves forward.
"""

ARCHIVE_NOTE = """\
The National Risk Index bulk download endpoints no longer resolve. Verified
2026-08-23:

  hazards.fema.gov/nri/Content/StaticDocuments/DataDownload/...
      -> HTTP 200 after redirect to fema.gov/emergency-managers/practitioners/
         resilience-analysis-and-planning-tool (an HTML page, not the data)
  nri-data-downloads.s3.amazonaws.com
      -> HTTP 404, S3 <Code>NoSuchBucket</Code>
  www.fema.gov/api/open/v1/DataSets
      -> 49 datasets, none of them the National Risk Index

A dated third-party deposit of a 2025 release exists at ICPSR/DataLumos,
doi:10.3886/E218382V1, distributed 2025-02-07, but it carries geodatabase and
shapefile bundles rather than the county CSV table and it is a 2025
distribution, so it does not improve the vintage position.

Consequence for reproducibility: this adapter reads a mutable endpoint. It
cannot pin a content hash the way grip/sources/fio.py does, so it records the
row count, the release label and the retrieval date into its output instead, and
a rerun after FEMA's next release will legitimately differ. That is a declared
weakness, not an accident.
"""

DEVIATIONS = [
    "Mutable source. FEMA overwrites one ArcGIS layer per release, so no content "
    "hash can be pinned and no earlier vintage can be requested. Row count, "
    "release label and retrieval timestamp are recorded instead.",
    "EAL is a modelled climatology, not a realisation. It is built from decades "
    "of historical hazard frequency and severity, so it is close to "
    "time-invariant and cannot express a change in risk pricing between two "
    "adjacent origins.",
    "Building exposure denominator. EAL_VALB is measured against BUILDVALUE, "
    "FEMA's estimate of replacement cost, which is not the insured value and "
    "not the FIO policy base. The ratio is therefore a rate on a different "
    "denominator than a premium per policy.",
    "County to metro aggregation is exposure-weighted, so a metro's rate is "
    "dominated by its highest-value county. This is the correct weighting for a "
    "loss cost but it discards within-metro dispersion.",
    "EAL omits the two perils that drive most homeowners rate filings in the "
    "hardest markets: it has no fire-following-wind term, and its flood "
    "components are riverine and coastal inundation, not the non-modelled water "
    "damage that dominates claim frequency.",
]

# Building EAL fields, one per hazard, kept so a hazard-specific proxy can be
# built later without a second retrieval.
HAZARDS = [
    "CFLD", "IFLD", "HRCN", "WFIR", "SWND", "TRND", "HAIL", "ERQK",
    "WNTW", "ISTM", "LNDS", "HWAV", "CWAV", "LTNG", "AVLN", "TSUN", "VLCN",
]
BASE_FIELDS = [
    "STCOFIPS", "STATEABBRV", "COUNTY", "POPULATION", "BUILDVALUE", "AGRIVALUE",
    "AREA", "RISK_SCORE", "EAL_SCORE", "EAL_VALT", "EAL_VALB", "EAL_VALP",
    "EAL_VALPE", "EAL_VALA",
]
FIELDS = BASE_FIELDS + [f"{h}_EALB" for h in HAZARDS]

MIN_COUNTIES = 1


def _fetch_pages(timeout: int = 180) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        params = urllib.parse.urlencode({
            "where": "1=1",
            "outFields": ",".join(FIELDS),
            "returnGeometry": "false",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
            "orderByFields": "STCOFIPS",
        })
        with urllib.request.urlopen(f"{SERVICE}/query?{params}", timeout=timeout) as r:
            payload = json.load(r)
        if "error" in payload:
            raise RuntimeError(f"NRI query failed at offset {offset}: {payload['error']}")
        feats = payload.get("features", [])
        rows.extend(f["attributes"] for f in feats)
        if not payload.get("exceededTransferLimit") and len(feats) < PAGE:
            break
        offset += PAGE
        time.sleep(0.3)
    return rows


def raw(refresh: bool = False) -> pd.DataFrame:
    """County-level NRI records. Cached locally; the upstream layer is mutable."""
    path = CACHE / "nri" / "nri_counties.json"
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_fetch_pages()))
    rows = json.loads(path.read_text())
    df = pd.DataFrame(rows)
    df["fips"] = df["STCOFIPS"].astype(str).str.zfill(5)
    for c in df.columns:
        if c.endswith("_EALB") or c in {
            "POPULATION", "BUILDVALUE", "AGRIVALUE", "AREA",
            "RISK_SCORE", "EAL_SCORE", "EAL_VALT", "EAL_VALB",
            "EAL_VALP", "EAL_VALPE", "EAL_VALA",
        }:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # Hazard EALs are null where a county has no exposure to that hazard. That
    # is a real zero, not a missing value.
    for h in HAZARDS:
        df[f"{h}_EALB"] = df[f"{h}_EALB"].fillna(0.0)
    return df


def metro_eal(delineation_vintage: int = 2020, refresh: bool = False) -> pd.DataFrame:
    """One row per metro: exposure-weighted expected annual loss rate.

    `eal_rate`      total building EAL / total building exposure. The pure
                    premium rate, and the quantity comparable to a premium.
    `eal_rate_log`  its log, so a coefficient is per log point like the FIO
                    premium feature it is meant to replace.
    `eal_per_cap`   total EAL (building + population-equivalent + agriculture)
                    per resident, a severity measure rather than a rate.
    `wfir_share`    wildfire share of building EAL.
    `flood_share`   riverine plus coastal flood share of building EAL.
    `wind_share`    hurricane, strong wind and tornado share of building EAL.
    """
    df = raw(refresh=refresh)
    xw = cbsa_src.crosswalk(delineation_vintage)
    key = "fips" if "fips" in xw.columns else xw.columns[0]
    xw = xw.rename(columns={key: "fips"})
    xw["fips"] = xw["fips"].astype(str).str.zfill(5)

    j = df.merge(xw, on="fips", how="inner")
    grp = j.groupby("cbsa_code")

    agg = pd.DataFrame({
        "eal_b": grp["EAL_VALB"].sum(),
        "eal_t": grp["EAL_VALT"].sum(),
        "buildvalue": grp["BUILDVALUE"].sum(),
        "population": grp["POPULATION"].sum(),
        "n_counties": grp["fips"].nunique(),
    })
    for h in HAZARDS:
        agg[f"{h.lower()}_ealb"] = grp[f"{h}_EALB"].sum()

    agg = agg[agg["buildvalue"] > 0]
    agg = agg[agg["n_counties"] >= MIN_COUNTIES]

    out = pd.DataFrame(index=agg.index)
    out["eal_rate"] = agg["eal_b"] / agg["buildvalue"]
    out["eal_rate_log"] = np.log(out["eal_rate"].where(out["eal_rate"] > 0))
    out["eal_per_cap"] = agg["eal_t"] / agg["population"].where(agg["population"] > 0)
    out["wfir_share"] = agg["wfir_ealb"] / agg["eal_b"].where(agg["eal_b"] > 0)
    out["flood_share"] = (agg["ifld_ealb"] + agg["cfld_ealb"]) / agg["eal_b"].where(agg["eal_b"] > 0)
    out["wind_share"] = (
        agg["hrcn_ealb"] + agg["swnd_ealb"] + agg["trnd_ealb"]
    ) / agg["eal_b"].where(agg["eal_b"] > 0)
    out["n_counties"] = agg["n_counties"]

    if "cbsa_title" in j.columns:
        out = out.join(j.groupby("cbsa_code")["cbsa_title"].first())
    return out.reset_index()


def coverage_report(delineation_vintage: int = 2020) -> dict:
    df = raw()
    feat = metro_eal(delineation_vintage)
    return {
        "source": "FEMA National Risk Index Counties (ArcGIS)",
        "arcgis_item": ITEM,
        "release_label": RELEASE_LABEL,
        "published": PUBLISHED,
        "counties": int(len(df)),
        "counties_with_exposure": int((df["BUILDVALUE"] > 0).sum()),
        "metros_with_features": int(len(feat)),
        "median_counties_per_metro": int(feat["n_counties"].median()),
        "eal_rate_median_bp": round(1e4 * float(feat["eal_rate"].median()), 3),
        "eal_rate_p10_bp": round(1e4 * float(feat["eal_rate"].quantile(0.10)), 3),
        "eal_rate_p90_bp": round(1e4 * float(feat["eal_rate"].quantile(0.90)), 3),
        "eligible_as_graded_predictor": False,
        "ineligibility_reasons": [
            "retrievable release is a 2025 publication (mutable layer)",
            "first NRI release was 2020-10, so no vintage reaches origins before 2021",
        ],
        "deviations": DEVIATIONS,
    }


if __name__ == "__main__":
    print(VINTAGE_VERDICT)
    print(ARCHIVE_NOTE)
    print(json.dumps(coverage_report(), indent=2))
