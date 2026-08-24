"""SE audit: does E10's inference survive clustering that is not on metro?

grip/fe.py clusters on cbsa_code, which allows residuals to be correlated within
a metro across overlapping origins but assumes metros are INDEPENDENT of each
other inside the same origin year. Demeaning by origin x division absorbs the
common national and regional mean, so that assumption is not absurd -- but it is
untested, and every t-statistic on the scorecard rests on it.

This recomputes the same OLS coefficients under four error assumptions:
  metro    -- current harness (clusters = metros)
  origin   -- clusters = origin years (allows arbitrary cross-metro correlation
              within a year; ignores the overlap across years)
  block    -- clusters = non-overlapping horizon-length origin blocks (allows
              cross-metro correlation AND within-block serial correlation; this
              is the conservative reading of an overlapping-window panel)
  twoway   -- Cameron-Gelbach-Miller: V_metro + V_block - V_intersection

Coefficients are identical across all four. Only the standard errors move.
Nothing here is registered; it is a diagnostic on inference, not a new grade.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from grip.panel import demean_within  # noqa: E402
from grip.sources import fhfa as fhfa_src  # noqa: E402
from run_long_panel import (  # noqa: E402
    FEATS_LONG,
    FEATS_WINDOW_PRIMARY,
    HORIZONS,
    bea_county_income,
    build,
    metro_titles,
)


def _meat(X: np.ndarray, u: np.ndarray, g: np.ndarray) -> np.ndarray:
    m = np.zeros((X.shape[1], X.shape[1]))
    for gv in np.unique(g):
        sel = g == gv
        s = X[sel].T @ u[sel]
        m += np.outer(s, s)
    return m


def _se(xtx_inv, meat, n, k, n_g):
    scale = (n_g / max(n_g - 1, 1)) * ((n - 1) / (n - k))
    v = xtx_inv @ (scale * meat) @ xtx_inv
    return np.sqrt(np.maximum(np.diag(v), 0.0))


def audit(df: pd.DataFrame, feats: list[str], horizon: int) -> pd.DataFrame:
    wr = [f + "_wr" for f in feats]
    d = demean_within(df, feats + ["y_hpi"]).dropna(subset=wr + ["y_hpi_wr"])
    X = d[wr].to_numpy(float)
    X = (X - X.mean(0)) / np.where(X.std(0) == 0, 1.0, X.std(0))
    X = np.column_stack([np.ones(len(X)), X])
    y = d["y_hpi_wr"].to_numpy(float)
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    u = y - X @ beta
    n, k = X.shape

    metro = d["cbsa_code"].to_numpy()
    origin = d["origin_year"].to_numpy()
    # non-overlapping blocks: an h-year horizon makes origins within h years of
    # each other share forward data, so a block is h consecutive origins.
    block = ((origin - origin.min()) // horizon).astype(int)
    inter = np.array([f"{a}|{b}" for a, b in zip(metro, block)])

    se_m = _se(xtx_inv, _meat(X, u, metro), n, k, len(np.unique(metro)))
    se_o = _se(xtx_inv, _meat(X, u, origin), n, k, len(np.unique(origin)))
    se_b = _se(xtx_inv, _meat(X, u, block), n, k, len(np.unique(block)))

    v_m = xtx_inv @ _meat(X, u, metro) @ xtx_inv
    v_b = xtx_inv @ _meat(X, u, block) @ xtx_inv
    v_i = xtx_inv @ _meat(X, u, inter) @ xtx_inv
    se_tw = np.sqrt(np.maximum(np.diag(v_m + v_b - v_i), 0.0))

    rows = []
    for i, nm in enumerate(["const"] + feats):
        if nm == "const":
            continue
        r = {"feature": nm, "coef": round(float(beta[i]), 6)}
        for lbl, se in (("metro", se_m), ("origin", se_o),
                        ("block", se_b), ("twoway", se_tw)):
            t = float(beta[i] / se[i]) if se[i] > 0 else np.nan
            r[f"t_{lbl}"] = round(t, 3)
            r[f"sig_{lbl}"] = bool(abs(t) > 1.96) if np.isfinite(t) else False
        rows.append(r)
    out = pd.DataFrame(rows)
    out.attrs["n"] = n
    out.attrs["n_metro"] = int(len(np.unique(metro)))
    out.attrs["n_origin"] = int(len(np.unique(origin)))
    out.attrs["n_block"] = int(len(np.unique(block)))
    return out


def main() -> None:
    ann = fhfa_src.annual_hpi()
    hpi = ann.pivot(index="cbsa_code", columns="year", values="hpi")
    last = int(ann["year"].max())
    geo = metro_titles().set_index("cbsa_code")
    bea = bea_county_income()
    long_df = build(hpi, last, None)
    win_df = build(hpi, last, bea)
    for d in (long_df, win_df):
        d["division"] = d["cbsa_code"].map(geo["division"]).fillna("Unknown")

    res = {"generated": datetime.now(timezone.utc).isoformat(), "cells": {}}
    for h in HORIZONS:
        for lbl, src, feats in (
            (f"LONG_h{h}", long_df, FEATS_LONG),
            (f"WINDOW_h{h}", win_df, FEATS_WINDOW_PRIMARY),
        ):
            sub = src[src["horizon"] == h]
            if sub.empty:
                continue
            a = audit(sub, feats, h)
            res["cells"][lbl] = {
                "n": a.attrs["n"], "n_metro": a.attrs["n_metro"],
                "n_origin": a.attrs["n_origin"], "n_block": a.attrs["n_block"],
                "rows": a.to_dict("records"),
            }
            print(f"\n=== {lbl}  n={a.attrs['n']}  metros={a.attrs['n_metro']} "
                  f"origins={a.attrs['n_origin']} blocks={a.attrs['n_block']}")
            print(a.to_string(index=False))

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = Path("out") / f"se_audit_{ts}.json"
    p.write_text(json.dumps(res, indent=2))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
