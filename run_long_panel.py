"""E10 -- the long panel. Attempt 2 under PROTOCOL.md section 14.

Registered results-free at tag v1.7.0-prereg, commit
89b98a19931368b98f0ab906aab6db8719bf544f, before this file existed.

Two cells, both target y_hpi:

  LONG    origins from 1995, FHFA only, features hpi_g1 hpi_g5 hpi_gap hpi_vol
          hpi_drawdown. No PEP, no BPS, no CBSA delineation, therefore no new
          vintage exposure beyond the FHFA revision issue already disclosed.
  WINDOW  origins from 2010, the same features plus hpi_income_gap built on BEA
          CAINC1 per-capita personal income. Primary retains hpi_gap alongside
          (PROTOCOL 14.9); the replacement variant runs as a registered
          secondary.

Feature and target formulas are copied from grip/panel.py verbatim so LONG and
the graded panel differ ONLY in sample period and in the two added features.
The estimation path is untouched: same RidgeCV grid, same (origin_year, division)
demeaning via panel.demean_within, same metro-clustered OLS and leave-one-origin-out
stability via grip/fe.py.

This cell cannot certify anything. Section 13 caps it at CANDIDATE, and LONG is
not comparable to the published scorecard (reduced feature set; includes origins
2011 and 2021 that the graded panel omits).
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV

from grip import fe
from grip.fetch import get
from grip.panel import TREND_WINDOW, _log_trend_gap, demean_within
from grip.sources import cbsa as cbsa_src
from grip.sources import fhfa as fhfa_src

OUT = Path("out")
OUT.mkdir(exist_ok=True)

FIRST_LONG_ORIGIN = 1995
FIRST_WINDOW_ORIGIN = 2010
HORIZONS = (5, 3)
BEA_URL = "https://apps.bea.gov/regional/zip/CAINC1.zip"
MIN_BEA_COVERAGE = 0.80

FOCAL_LONG = ["hpi_gap", "hpi_vol"]
FEATS_LONG = ["hpi_g1", "hpi_g5", "hpi_gap", "hpi_vol", "hpi_drawdown"]
FEATS_WINDOW_PRIMARY = FEATS_LONG + ["hpi_income_gap"]
FEATS_WINDOW_SECONDARY = ["hpi_g1", "hpi_g5", "hpi_vol", "hpi_drawdown", "hpi_income_gap"]

DIVISION = {
    "New England": "CT ME MA NH RI VT",
    "Middle Atlantic": "NJ NY PA",
    "East North Central": "IL IN MI OH WI",
    "West North Central": "IA KS MN MO NE ND SD",
    "South Atlantic": "DE DC FL GA MD NC SC VA WV",
    "East South Central": "AL KY MS TN",
    "West South Central": "AR LA OK TX",
    "Mountain": "AZ CO ID MT NV NM UT WY",
    "Pacific": "AK CA HI OR WA",
    "Puerto Rico": "PR VI",
}
STATE_TO_DIV = {s: d for d, ss in DIVISION.items() for s in ss.split()}


# ---------------------------------------------------------------- geography


def metro_titles() -> pd.DataFrame:
    """cbsa_code -> title and derived census division.

    Divisions have been fixed since 1950, so deriving one from the state
    abbreviation in the FHFA title introduces no vintage dependency and needs no
    delineation file. That is what makes origins before 2009 legal at all.
    """
    q = pd.read_csv(
        get(fhfa_src.URL, name="hpi_at_metro.csv"),
        header=None,
        names=["cbsa_title", "cbsa_code", "year", "quarter", "hpi_nsa", "hpi_sa"],
        dtype=str,
        usecols=[0, 1],
    )
    q["cbsa_code"] = pd.to_numeric(q["cbsa_code"], errors="coerce")
    q = q.dropna(subset=["cbsa_code"]).drop_duplicates("cbsa_code")
    q["cbsa_code"] = q["cbsa_code"].astype(int)

    def div(title: str) -> str:
        if "," not in str(title):
            return "Unknown"
        st = str(title).rsplit(",", 1)[1].strip().split("-")[0].strip().upper()
        return STATE_TO_DIV.get(st, "Unknown")

    q["division"] = q["cbsa_title"].map(div)
    return q[["cbsa_code", "cbsa_title", "division"]]


# ---------------------------------------------------------------- income


def bea_county_income() -> pd.DataFrame:
    """BEA CAINC1: county personal income (thousands) and population, 1969-2024.

    Public domain. Revision-contaminated in the same way FHFA is, which is why
    WINDOW is reported Class B rather than Class A (PROTOCOL 14.8).
    """
    path = get(BEA_URL, name="CAINC1.zip")
    with zipfile.ZipFile(path) as z:
        member = next(n for n in z.namelist() if n.endswith("ALL_AREAS_1969_2024.csv"))
        raw = pd.read_csv(
            io.BytesIO(z.read(member)), encoding="latin-1", low_memory=False, dtype=str
        )
    raw["fips"] = pd.to_numeric(raw["GeoFIPS"].str.strip().str.strip('"'), errors="coerce")
    raw["LineCode"] = pd.to_numeric(raw["LineCode"], errors="coerce")
    raw = raw[raw["LineCode"].isin([1, 2])].dropna(subset=["fips"])
    raw["fips"] = raw["fips"].astype(int)
    raw = raw[(raw["fips"] % 1000 != 0)]  # drop state and national aggregates

    years = [c for c in raw.columns if c.isdigit()]
    long = raw.melt(
        id_vars=["fips", "LineCode"], value_vars=years, var_name="year", value_name="v"
    )
    long["year"] = long["year"].astype(int)
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    wide = long.pivot_table(index=["fips", "year"], columns="LineCode", values="v").reset_index()
    wide.columns = ["fips", "year", "income_k", "pop"]
    return wide.dropna(subset=["income_k", "pop"])


def metro_pci(origin_year: int, bea: pd.DataFrame) -> pd.DataFrame:
    """Metro per-capita personal income by year, plus the BEA county match rate."""
    cw = cbsa_src.crosswalk(cbsa_src.delineation_for_origin(origin_year))
    cw = cw[["fips", "cbsa_code"]].dropna().drop_duplicates()
    cw["fips"] = cw["fips"].astype(int)

    n_expected = cw.groupby("cbsa_code")["fips"].nunique().rename("n_cw")
    m = cw.merge(bea, on="fips", how="inner")
    n_matched = m.groupby("cbsa_code")["fips"].nunique().rename("n_bea")
    cov = pd.concat([n_expected, n_matched], axis=1).fillna(0)
    cov["coverage"] = cov["n_bea"] / cov["n_cw"]
    keep = set(cov.index[cov["coverage"] >= MIN_BEA_COVERAGE])

    agg = (
        m[m["cbsa_code"].isin(keep)]
        .groupby(["cbsa_code", "year"], as_index=False)[["income_k", "pop"]]
        .sum()
    )
    agg["pci"] = agg["income_k"] * 1000.0 / agg["pop"]
    return agg[["cbsa_code", "year", "pci"]], cov


# ---------------------------------------------------------------- features


def _drawdown(win: pd.Series) -> float:
    """Deepest peak-to-trough log decline inside the window. <= 0 always.

    The rolling, vintage-legal generalisation of '2000s crash depth': defined
    identically at every origin, so it cannot encode one particular episode.
    """
    lv = np.log(win.to_numpy(float))
    run_max = np.maximum.accumulate(lv)
    return float(np.min(lv - run_max))


def price_features(base: int, hpi_wide: pd.DataFrame) -> pd.DataFrame:
    """hpi_g1 / hpi_g5 / hpi_gap / hpi_vol copied from grip/panel.py, plus hpi_drawdown."""
    rows = []
    for code, series in hpi_wide.iterrows():
        h = series.dropna()
        if h.empty or base not in h.index:
            continue
        hpi_g1 = h[base] / h[base - 1] - 1 if (base - 1) in h.index else np.nan
        hpi_g5 = (h[base] / h[base - 5]) ** (1 / 5) - 1 if (base - 5) in h.index else np.nan

        win = h[(h.index >= base - TREND_WINDOW) & (h.index <= base)]
        hpi_gap = hpi_dd = np.nan
        if len(win) >= 8:
            hpi_gap = _log_trend_gap(win.index.values.astype(float), np.log(win.values))
            hpi_dd = _drawdown(win)

        g5 = h.pct_change().dropna()
        g5 = g5[(g5.index > base - 6) & (g5.index <= base)]
        hpi_vol = float(np.std(g5.values, ddof=1)) if len(g5) >= 4 else np.nan

        rows.append(
            {
                "cbsa_code": code,
                "base_year": base,
                "hpi_g1": hpi_g1,
                "hpi_g5": hpi_g5,
                "hpi_gap": hpi_gap,
                "hpi_vol": hpi_vol,
                "hpi_drawdown": hpi_dd,
            }
        )
    return pd.DataFrame(rows)


def income_gap(base: int, hpi_wide: pd.DataFrame, pci: pd.DataFrame) -> pd.DataFrame:
    """Deviation of log(HPI / per-capita income) from its own 15-year trend.

    Because it is a deviation from the metro's own trend, the arbitrary constant
    in an index-over-dollars ratio drops out. Unlike hpi_gap this has a
    denominator that moves independently of price, so it is not momentum by
    construction.
    """
    pw = pci.pivot(index="cbsa_code", columns="year", values="pci")
    rows = []
    for code in hpi_wide.index.intersection(pw.index):
        h = hpi_wide.loc[code].dropna()
        p = pw.loc[code].dropna()
        yrs = sorted(set(h.index) & set(p.index) & set(range(base - TREND_WINDOW, base + 1)))
        if len(yrs) < 8 or yrs[-1] != base:
            continue
        r = np.log(h[yrs].to_numpy(float)) - np.log(p[yrs].to_numpy(float))
        rows.append(
            {
                "cbsa_code": code,
                "base_year": base,
                "hpi_income_gap": _log_trend_gap(np.array(yrs, dtype=float), r),
            }
        )
    return pd.DataFrame(rows)


def build(hpi_wide: pd.DataFrame, last_year: int, bea: pd.DataFrame | None) -> pd.DataFrame:
    """One row per (origin, metro) with features, y_hpi at each horizon."""
    frames = []
    coverage_report = {}
    first = FIRST_LONG_ORIGIN if bea is None else FIRST_WINDOW_ORIGIN
    for h in HORIZONS:
        for origin in range(first, last_year + 2):
            base = origin - 1
            if base + h > last_year or base not in hpi_wide.columns:
                continue
            f = price_features(base, hpi_wide)
            if f.empty:
                continue
            if bea is not None:
                pci, cov = metro_pci(origin, bea)
                coverage_report[origin] = round(float(cov["coverage"].median()), 3)
                ig = income_gap(base, hpi_wide, pci)
                if ig.empty:
                    continue
                f = f.merge(ig, on=["cbsa_code", "base_year"], how="inner")
            end = base + h
            y = (hpi_wide[end] / hpi_wide[base]) ** (1 / h) - 1
            f["y_hpi"] = f["cbsa_code"].map(y)
            f["origin_year"] = origin
            f["horizon"] = h
            frames.append(f)
    out = pd.concat(frames, ignore_index=True)
    if coverage_report:
        out.attrs["bea_coverage"] = coverage_report
    return out


# ---------------------------------------------------------------- estimation


def fit_cell(df: pd.DataFrame, feats: list[str]) -> dict:
    """Ridge coefficients, clustered inference and LOO stability. Untouched path."""
    wr = [f + "_wr" for f in feats]
    d = demean_within(df, feats + ["y_hpi"]).dropna(subset=wr + ["y_hpi_wr"])
    if len(d) < 60:
        return {"status": "INSUFFICIENT", "n": int(len(d))}

    X = d[wr].to_numpy(float)
    Xs = (X - X.mean(0)) / np.where(X.std(0) == 0, 1.0, X.std(0))
    m = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(Xs, d["y_hpi_wr"].to_numpy(float))

    ols = fe.cluster_ols(d, wr, "y_hpi_wr")
    loo = fe.loo_origin_coefficients(d, wr, "y_hpi_wr")
    stab = fe.stability_from_loo(loo, wr)

    per_origin = d.groupby("origin_year")["cbsa_code"].nunique()
    return {
        "status": "OK",
        "n": int(len(d)),
        "n_metros": int(d["cbsa_code"].nunique()),
        "n_origins": int(d["origin_year"].nunique()),
        "origins": [int(o) for o in sorted(d["origin_year"].unique())],
        "median_metros_per_origin": int(per_origin.median()),
        "min_metros_per_origin": int(per_origin.min()),
        "alpha": float(m.alpha_),
        "ridge": {f: round(float(c), 6) for f, c in zip(feats, m.coef_)},
        "cluster_ols": [] if ols.empty else ols.assign(
            feature=lambda x: x["feature"].str.replace("_wr$", "", regex=True)
        ).to_dict("records"),
        "loo_stability": [] if stab.empty else stab.assign(
            feature=lambda x: x["feature"].str.replace("_wr$", "", regex=True)
        ).to_dict("records"),
    }


def look(cell: dict, feature: str) -> tuple[float | None, float | None, float | None]:
    """(ridge coef, clustered t, LOO share_positive) for one feature."""
    if cell.get("status") != "OK":
        return None, None, None
    coef = cell["ridge"].get(feature)
    t = next((r["t"] for r in cell["cluster_ols"] if r["feature"] == feature), None)
    sp = next((r["share_positive"] for r in cell["loo_stability"] if r["feature"] == feature), None)
    return coef, t, sp


def main() -> None:
    ann = fhfa_src.annual_hpi()
    hpi_wide = ann.pivot(index="cbsa_code", columns="year", values="hpi")
    last_year = int(ann["year"].max())
    geo = metro_titles().set_index("cbsa_code")

    long_df = build(hpi_wide, last_year, None)
    bea = bea_county_income()
    win_df = build(hpi_wide, last_year, bea)

    for d in (long_df, win_df):
        d["division"] = d["cbsa_code"].map(geo["division"]).fillna("Unknown")

    res: dict = {
        "cell": "E10_LONG_PANEL",
        "protocol": "PROTOCOL.md section 14",
        "prereg_tag": "v1.7.0-prereg",
        "prereg_commit": "89b98a19931368b98f0ab906aab6db8719bf544f",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fhfa_last_full_year": last_year,
        "status_ceiling": "CANDIDATE -- section 13. Cannot re-grade v1.0.0-grip1.",
        "not_comparable_to_scorecard": (
            "LONG uses a reduced price-only feature set and includes origins 2011 and "
            "2021 which the graded panel omits. Do not compare to published E4/E5."
        ),
        "bea_median_county_coverage_by_origin": win_df.attrs.get("bea_coverage", {}),
        "cells": {},
    }

    for h in HORIZONS:
        res["cells"][f"LONG_h{h}"] = fit_cell(long_df[long_df["horizon"] == h], FEATS_LONG)
        res["cells"][f"WINDOW_h{h}"] = fit_cell(
            win_df[win_df["horizon"] == h], FEATS_WINDOW_PRIMARY
        )
        res["cells"][f"WINDOW_SECONDARY_h{h}"] = fit_cell(
            win_df[win_df["horizon"] == h], FEATS_WINDOW_SECONDARY
        )

    # ------------------------------------------------ registered predictions
    L5 = res["cells"]["LONG_h5"]
    W5 = res["cells"]["WINDOW_h5"]
    S5 = res["cells"]["WINDOW_SECONDARY_h5"]

    p4_long = (
        L5.get("status") == "OK"
        and L5["n_origins"] >= 20
        and L5["median_metros_per_origin"] >= 150
    )
    p4_window = W5.get("status") == "OK" and W5["n_origins"] >= 8
    p4 = bool(p4_long and p4_window)

    g_coef, _, g_sp = look(L5, "hpi_gap")
    p1 = bool(p4 and g_coef is not None and g_coef < 0 and g_sp is not None and g_sp < 0.5)

    i_coef, _, i_sp = look(W5, "hpi_income_gap")
    p2 = bool(p4 and i_coef is not None and i_coef < 0 and i_sp is not None and i_sp < 0.5)
    s_coef, _, _ = look(S5, "hpi_income_gap")
    ambiguity_split = bool(
        i_coef is not None and s_coef is not None and (i_coef < 0) != (s_coef < 0)
    )

    _, v_t, _ = look(W5, "hpi_vol")
    p3 = bool(p4 and v_t is not None and abs(v_t) < 2.0)

    if not p4:
        verdict = "UNINFORMATIVE"
    elif p1 and p2:
        verdict = "PARTIAL (14.9 sign split)" if ambiguity_split else "SUPPORTED"
    elif p1 or p2:
        verdict = "PARTIAL"
    else:
        verdict = "REJECTED"

    res["predictions"] = {
        "P1_hpi_gap_negative_in_LONG_h5": {
            "coef": g_coef, "loo_share_positive": g_sp, "holds": p1,
        },
        "P2_hpi_income_gap_negative_in_WINDOW_h5_primary": {
            "coef": i_coef, "loo_share_positive": i_sp, "holds": p2,
            "secondary_replacement_coef": s_coef,
            "sign_split_between_variants": ambiguity_split,
        },
        "P3_hpi_vol_insignificant_given_drawdown_WINDOW_h5": {
            "t": v_t, "holds": p3, "note": "diagnostic only, cannot change verdict",
        },
        "P4_power": {
            "long_origins": L5.get("n_origins"),
            "long_median_metros": L5.get("median_metros_per_origin"),
            "window_origins": W5.get("n_origins"),
            "holds": p4,
        },
    }
    res["verdict"] = verdict
    res["reject_clause_triggered"] = bool(verdict == "REJECTED")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"long_panel_{stamp}.json"
    path.write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res["predictions"], indent=2, default=str))
    print("\nVERDICT:", verdict)
    print("wrote", path)


if __name__ == "__main__":
    main()
