"""GRIP-2 section 6 power-precondition check for y_hpi. Registered under v2.0.0-prereg.

WHAT THIS DOES NOT DO. It fits nothing. No coefficient, no standard error, no R2,
no correlation between any feature and any outcome is computed or written. The
target y_hpi is constructed only so that rows with a missing outcome can be
excluded from the count, because section 6 speaks of *usable* rows. If this
script computed a single feature-outcome relationship it would spend the
blindness of the anchor, so it deliberately cannot.

Preconditions tested, verbatim from section 6:
  - y_hpi: >= 20 origins, median >= 150 metros per origin
  - every cell: >= 60 usable rows after demeaning, >= 5 metros per demeaning group
  - every cell: >= 10 clusters under the scheme it is graded on, per G7

Cell variants are enumerated because section 6 must be checked per cell, and the
graded specification carries hpi_income_gap as a focal feature. That feature needs
BEA county income aggregated to metros, which needs a county->CBSA crosswalk,
which under G4 must come from a delineation vintage <= the origin year. So the
income-gap cells and the price-only cells have structurally different origin
availability, and both are reported.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from grip.panel import demean_within
from grip.sources import cbsa as cbsa_src
from grip.sources import fhfa as fhfa_src
from run_long_panel import (
    STATE_TO_DIV,
    bea_county_income,
    build,
    income_gap,
    metro_titles,
    price_features,
)

OUT = Path("out")
OUT.mkdir(exist_ok=True)

FIRST_ORIGIN = 1995  # section 3: y_hpi origins 1995 onward
HORIZONS = (5, 3)
MIN_ORIGINS = 20
MIN_MEDIAN_METROS = 150
MIN_ROWS = 60
MIN_GROUP = 5
MIN_CLUSTERS = 10

PRICE_ONLY = ["hpi_g1", "hpi_g5", "hpi_drawdown"]
WITH_INCOME = PRICE_ONLY + ["hpi_income_gap"]


def blocks(origins: np.ndarray, horizon: int) -> np.ndarray:
    """Non-overlapping horizon-length blocks, as in run_se_audit.py."""
    return (origins - origins.min()) // horizon


def assess(df: pd.DataFrame, feats: list[str], horizon: int, label: str) -> dict:
    """Count only. Nothing here touches the relationship between feats and y_hpi."""
    need = feats + ["y_hpi"]
    d = df.dropna(subset=need).copy()
    raw_origins = sorted(d["origin_year"].unique().tolist())

    dm = demean_within(d, feats, min_group=MIN_GROUP)
    origins = np.array(sorted(dm["origin_year"].unique()))
    per_origin = dm.groupby("origin_year")["cbsa_code"].nunique()
    blk = blocks(origins, horizon) if len(origins) else np.array([])

    n_origins = int(len(origins))
    n_blocks = int(len(set(blk.tolist()))) if len(blk) else 0
    med_metros = float(per_origin.median()) if len(per_origin) else 0.0
    n_rows = int(len(dm))
    n_metro = int(dm["cbsa_code"].nunique())

    # G7: grade on the most conservative scheme with >= MIN_CLUSTERS clusters.
    # Candidate schemes that permit within-period cross-metro correlation,
    # ordered most conservative first.
    schemes = [("block", n_blocks), ("origin", n_origins)]
    gradeable = [s for s, k in schemes if k >= MIN_CLUSTERS]
    g7_scheme = gradeable[0] if gradeable else None

    checks = {
        "origins_ge_20": n_origins >= MIN_ORIGINS,
        "median_metros_ge_150": med_metros >= MIN_MEDIAN_METROS,
        "rows_ge_60": n_rows >= MIN_ROWS,
        "clusters_ge_10": g7_scheme is not None,
    }
    verdict = "PRECONDITIONS MET" if all(checks.values()) else "UNINFORMATIVE"

    return {
        "cell": label,
        "horizon": horizon,
        "features": feats,
        "origin_range": [int(min(raw_origins)), int(max(raw_origins))] if raw_origins else None,
        "n_origins": n_origins,
        "n_blocks": n_blocks,
        "n_rows_after_demeaning": n_rows,
        "n_metros": n_metro,
        "median_metros_per_origin": round(med_metros, 1),
        "min_metros_per_origin": int(per_origin.min()) if len(per_origin) else 0,
        "g7_gradeable_schemes": gradeable,
        "g7_grading_scheme": g7_scheme,
        "checks": checks,
        "verdict": verdict,
        "failed": [k for k, v in checks.items() if not v],
    }


def main() -> None:
    ann = fhfa_src.annual_hpi()
    hpi_wide = ann.pivot(index="cbsa_code", columns="year", values="hpi")
    last_year = int(ann["year"].max())
    geo = metro_titles().set_index("cbsa_code")
    print(f"FHFA last full year: {last_year}; metros in file: {len(hpi_wide)}")

    usable_vintages = sorted(cbsa_src.DELINEATIONS)
    earliest_cw = min(usable_vintages)
    print(f"delineation vintages registered: {usable_vintages}")

    results = []

    # ---- price-only cells: no crosswalk needed, so origins run from 1995
    price = build(hpi_wide, last_year, None)
    price["division"] = price["cbsa_code"].map(geo["division"]).fillna("Unknown")
    for h in HORIZONS:
        results.append(
            assess(price[price["horizon"] == h], PRICE_ONLY, h, f"PRICE_ONLY_h{h}")
        )

    # ---- income-gap cells: crosswalk-bound, earliest origin = earliest vintage
    bea = bea_county_income()
    frames = []
    for h in HORIZONS:
        for origin in range(max(FIRST_ORIGIN, earliest_cw), last_year + 2):
            base = origin - 1
            if base + h > last_year or base not in hpi_wide.columns:
                continue
            f = price_features(base, hpi_wide)
            if f.empty:
                continue
            try:
                vintage = cbsa_src.delineation_for_origin(origin)
                cw = cbsa_src.crosswalk(vintage)[["fips", "cbsa_code"]].dropna().drop_duplicates()
            except Exception as e:  # noqa: BLE001
                print(f"  origin {origin}: crosswalk unavailable ({e})")
                continue
            cw["fips"] = cw["fips"].astype(int)
            n_cw = cw.groupby("cbsa_code")["fips"].nunique().rename("n_cw")
            m = cw.merge(bea, on="fips", how="inner")
            n_bea = m.groupby("cbsa_code")["fips"].nunique().rename("n_bea")
            cov = pd.concat([n_cw, n_bea], axis=1).fillna(0)
            keep = set(cov.index[(cov["n_bea"] / cov["n_cw"]) >= 0.80])
            agg = (
                m[m["cbsa_code"].isin(keep)]
                .groupby(["cbsa_code", "year"], as_index=False)[["income_k", "pop"]]
                .sum()
            )
            agg["pci"] = agg["income_k"] * 1000.0 / agg["pop"]
            ig = income_gap(base, hpi_wide, agg[["cbsa_code", "year", "pci"]])
            if ig.empty:
                continue
            f = f.merge(ig, on=["cbsa_code", "base_year"], how="inner")
            end = base + h
            y = (hpi_wide[end] / hpi_wide[base]) ** (1 / h) - 1
            f["y_hpi"] = f["cbsa_code"].map(y)
            f["origin_year"] = origin
            f["horizon"] = h
            f["delineation_vintage"] = vintage
            frames.append(f)
    inc = pd.concat(frames, ignore_index=True)
    inc["division"] = inc["cbsa_code"].map(geo["division"]).fillna("Unknown")
    for h in HORIZONS:
        results.append(
            assess(inc[inc["horizon"] == h], WITH_INCOME, h, f"WITH_INCOME_h{h}")
        )

    payload = {
        "check": "GRIP-2 section 6 power preconditions, y_hpi",
        "prereg_tag": "v2.0.0-prereg",
        "prereg_commit": "667be2c0c77609da8e8b0b5c3562bad30a20a304",
        "spec_sha256": "f27b2cf9acb0af461d0817a98348ddae8f28175db609d4fc3af6626180d7fceb",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fhfa_last_full_year": last_year,
        "delineation_vintages_registered": usable_vintages,
        "no_estimation_performed": True,
        "thresholds": {
            "min_origins": MIN_ORIGINS,
            "min_median_metros_per_origin": MIN_MEDIAN_METROS,
            "min_rows_after_demeaning": MIN_ROWS,
            "min_metros_per_demeaning_group": MIN_GROUP,
            "min_clusters": MIN_CLUSTERS,
        },
        "cells": results,
    }
    p = OUT / "precondition_check.json"
    p.write_text(json.dumps(payload, indent=2))

    print(f"\n{'cell':<20}{'origins':>8}{'blocks':>8}{'rows':>7}{'medMetros':>11}"
          f"{'G7':>8}  verdict")
    for r in results:
        print(f"{r['cell']:<20}{r['n_origins']:>8}{r['n_blocks']:>8}"
              f"{r['n_rows_after_demeaning']:>7}{r['median_metros_per_origin']:>11}"
              f"{str(r['g7_grading_scheme']):>8}  {r['verdict']}"
              + (f"  <- {','.join(r['failed'])}" if r["failed"] else ""))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
