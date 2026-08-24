"""Does the PUBLISHED scorecard's inference survive non-metro clustering?

run_se_audit.py showed that on the E10 long panel, metro-clustered t-statistics
are inflated roughly 3-7x relative to clustering that allows cross-metro
correlation within a period. Every graded cell in SCORECARD.md, and every
diagnostic E6-E9, used the same metro-clustered path in grip/fe.py.

This re-runs the four GRADED cells on their own saved panels under the same four
error assumptions. Coefficients do not change. Only the standard errors do.

Diagnostic only. Nothing here regrades anything.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from run_se_audit import audit  # noqa: E402

GRADED = ["pop_g1", "pop_g3", "pop_accel", "hpi_g1", "hpi_g5",
          "hpi_gap", "hpi_vol", "permits_pc", "permits_g3"]


def main() -> None:
    res = {"generated": datetime.now(timezone.utc).isoformat(), "cells": {}}
    for target in ("pop", "hpi"):
        for h in (5, 3):
            p = Path("out") / f"panel_{target}_h{h}.parquet"
            if not p.exists():
                print(f"missing {p}")
                continue
            df = pd.read_parquet(p)
            # the saved panel already carries _wr columns and BOTH targets;
            # drop them so demean_within rebuilds cleanly and y_hpi is unique
            df = df.drop(columns=[c for c in df.columns if c.endswith("_wr")])
            other = "hpi" if target == "pop" else "pop"
            df = df.drop(columns=[f"y_{other}"], errors="ignore")
            feats = [f for f in GRADED if f in df.columns]
            df = df.rename(columns={f"y_{target}": "y_hpi"})
            a = audit(df, feats, h)
            lbl = f"{target}_h{h}"
            res["cells"][lbl] = {
                "n": a.attrs["n"], "n_metro": a.attrs["n_metro"],
                "n_origin": a.attrs["n_origin"], "n_block": a.attrs["n_block"],
                "rows": a.to_dict("records"),
            }
            print(f"\n=== GRADED {lbl}  n={a.attrs['n']} metros={a.attrs['n_metro']} "
                  f"origins={a.attrs['n_origin']} blocks={a.attrs['n_block']}")
            print(a.to_string(index=False))

    # how many metro-clustered "significant" verdicts survive?
    flips = []
    for lbl, c in res["cells"].items():
        for r in c["rows"]:
            if r["sig_metro"] and not r["sig_twoway"]:
                flips.append((lbl, r["feature"], r["t_metro"], r["t_twoway"]))
    res["significance_lost_under_twoway"] = [
        {"cell": a, "feature": b, "t_metro": c, "t_twoway": d} for a, b, c, d in flips
    ]
    print(f"\n--- {len(flips)} metro-significant coefficients lose significance "
          f"under two-way clustering:")
    for a, b, c, d in flips:
        print(f"    {a:10s} {b:12s} {c:+8.3f} -> {d:+8.3f}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path("out") / f"se_audit_graded_{ts}.json"
    out.write_text(json.dumps(res, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
