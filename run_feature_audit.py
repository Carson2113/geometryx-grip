"""Feature-space audit: what do hpi_gap and hpi_vol actually measure?

Integrity note: every quantity here is computed from PREDICTORS and from price
HISTORY only. No forecast target is read, and no coefficient on a target is
estimated. This is deliberate. Under PROTOCOL.md section 13 the prediction that
a longer panel flips the focal signs must be registered before it is run, so
this script is restricted to describing the features themselves.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from grip.sources import fhfa as fhfa_src

OUT = Path("out")
TREND, MINYRS = 15, 8


def wide_hpi() -> pd.DataFrame:
    h = fhfa_src.annual_hpi()
    return h.pivot_table(index="year", columns="cbsa_code", values="hpi", aggfunc="first").sort_index()


def origin_feasibility(w: pd.DataFrame) -> list[dict]:
    """How many metros could be graded at each candidate origin, on price data alone."""
    rows = []
    for Y in range(1990, 2022):
        base = Y - 1
        win = w.loc[(w.index > base - TREND) & (w.index <= base)]
        feat = (win.notna().sum(axis=0) >= MINYRS) & w.reindex([base]).notna().iloc[0]
        def truth(h):
            return int((feat & w.reindex([base + h]).notna().iloc[0]).sum()) if base + h in w.index else 0
        rows.append({"origin": Y, "window": f"{int(win.index.min())}-{base}",
                     "metros_with_features": int(feat.sum()),
                     "metros_with_h5_truth": truth(5), "metros_with_h3_truth": truth(3)})
    return rows


def gap_is_momentum(panel: pd.DataFrame) -> dict:
    """hpi_gap is deviation from a 15y log-price trend. Is that just momentum?"""
    per = []
    for y, g in panel.groupby("origin_year"):
        per.append({"origin": int(y), "n": len(g),
                    "corr_gap_g5": round(float(g["hpi_gap"].corr(g["hpi_g5"])), 4),
                    "corr_gap_g1": round(float(g["hpi_gap"].corr(g["hpi_g1"])), 4)})
    return {"pooled_corr_gap_g5": round(float(panel["hpi_gap"].corr(panel["hpi_g5"])), 4),
            "pooled_corr_gap_g1": round(float(panel["hpi_gap"].corr(panel["hpi_g1"])), 4),
            "per_origin": per}


def vol_is_crash_depth(panel: pd.DataFrame, w: pd.DataFrame) -> dict:
    """hpi_vol is the sd of 5y growth. Over 2010-2020, is it a GFC crash flag?"""
    peak = np.log(w.loc[2000:2007].max())
    trough = np.log(w.loc[2008:2012].min())
    crash = (trough - peak).rename("crash_log")          # more negative = deeper bust
    boom = (np.log(w.loc[2006]) - np.log(w.loc[2000])).rename("boom_00_06")
    hist = pd.concat([crash, boom], axis=1).rename_axis("cbsa_code").reset_index()
    d = panel[["cbsa_code", "origin_year", "hpi_vol"]].merge(hist, on="cbsa_code")
    per = [{"origin": int(y), "n": len(g),
            "corr_vol_crashdepth": round(float(g["hpi_vol"].corr(g["crash_log"])), 4),
            "corr_vol_boom0006": round(float(g["hpi_vol"].corr(g["boom_00_06"])), 4)}
           for y, g in d.groupby("origin_year")]
    return {"pooled_corr_vol_crashdepth": round(float(d["hpi_vol"].corr(d["crash_log"])), 4),
            "pooled_corr_vol_boom0006": round(float(d["hpi_vol"].corr(d["boom_00_06"])), 4),
            "per_origin": per}


def main() -> None:
    w = wide_hpi()
    panel = pd.read_parquet(OUT / "panel_hpi_h5.parquet")
    res = {
        "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "predictors and price history only; no target read, no target coefficient estimated",
        "fhfa_coverage": {"first_year": int(w.index.min()), "last_year": int(w.index.max()),
                          "metros": int(w.shape[1])},
        "graded_origins_now": sorted(int(x) for x in panel.origin_year.unique()),
        "origin_feasibility": origin_feasibility(w),
        "gap_is_momentum": gap_is_momentum(panel),
        "vol_is_crash_depth": vol_is_crash_depth(panel, w),
    }
    p = OUT / "feature_audit.json"
    p.write_text(json.dumps(res, indent=2))
    f = res["origin_feasibility"]
    add = [r for r in f if 1995 <= r["origin"] <= 2009]
    print(f"FHFA metro HPI in cache: {res['fhfa_coverage']['first_year']}-"
          f"{res['fhfa_coverage']['last_year']}, {res['fhfa_coverage']['metros']} metros")
    print(f"graded origins now: {len(res['graded_origins_now'])}")
    print(f"addable origins 1995-2009: {len(add)}, "
          f"median metros with h=5 truth {int(np.median([r['metros_with_h5_truth'] for r in add]))}")
    print(f"pooled corr(hpi_gap, hpi_g5)      = {res['gap_is_momentum']['pooled_corr_gap_g5']:+.3f}")
    print(f"pooled corr(hpi_vol, crash depth) = {res['vol_is_crash_depth']['pooled_corr_vol_crashdepth']:+.3f}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
