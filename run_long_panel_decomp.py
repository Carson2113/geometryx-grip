"""Post-hoc decomposition of E10. UNREGISTERED. Cannot change the E10 verdict.

The E10 verdict is locked at SUPPORTED by the accept rule in PROTOCOL.md 14.5.
This script exists to answer a question that verdict does not answer: is the sign
change on hpi_gap caused by the added 1995-2009 origins, or by the added
hpi_drawdown control, or by both? A registered verdict that cannot be attributed
is not much use, and these diagnostics can only weaken the claim, never widen it.

Explicitly labelled post-hoc. Run after the registered result was written.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV

from grip import fe
from grip.panel import demean_within
import run_long_panel as R

BASE = ["hpi_g1", "hpi_g5", "hpi_gap", "hpi_vol"]
WITH_DD = BASE + ["hpi_drawdown"]


def one(df: pd.DataFrame, feats: list[str], label: str) -> dict:
    wr = [f + "_wr" for f in feats]
    d = demean_within(df, feats + ["y_hpi"]).dropna(subset=wr + ["y_hpi_wr"])
    if len(d) < 60:
        return {"label": label, "status": "INSUFFICIENT", "n": int(len(d))}
    X = d[wr].to_numpy(float)
    Xs = (X - X.mean(0)) / np.where(X.std(0) == 0, 1.0, X.std(0))
    m = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(Xs, d["y_hpi_wr"].to_numpy(float))
    ols = {r["feature"].replace("_wr", ""): r for r in fe.cluster_ols(d, wr, "y_hpi_wr").to_dict("records")}
    loo = fe.loo_origin_coefficients(d, wr, "y_hpi_wr")
    st = {r["feature"].replace("_wr", ""): r for r in fe.stability_from_loo(loo, wr).to_dict("records")}
    out = {
        "label": label, "status": "OK", "n": int(len(d)),
        "n_origins": int(d["origin_year"].nunique()),
        "origins": f"{int(d['origin_year'].min())}-{int(d['origin_year'].max())}",
        "has_drawdown": "hpi_drawdown" in feats,
    }
    for f in ("hpi_gap", "hpi_vol", "hpi_g5", "hpi_drawdown"):
        if f not in feats:
            continue
        out[f] = {
            "coef": round(float(dict(zip(feats, m.coef_))[f]), 6),
            "t": ols.get(f, {}).get("t"),
            "share_positive": st.get(f, {}).get("share_positive"),
        }
    return out


def main() -> None:
    ann = R.fhfa_src.annual_hpi()
    hpi_wide = ann.pivot(index="cbsa_code", columns="year", values="hpi")
    last_year = int(ann["year"].max())
    geo = R.metro_titles().set_index("cbsa_code")

    df = R.build(hpi_wide, last_year, None)
    df["division"] = df["cbsa_code"].map(geo["division"]).fillna("Unknown")
    h5 = df[df["horizon"] == 5]

    early = h5[h5["origin_year"] <= 2009]
    late = h5[h5["origin_year"] >= 2010]

    rows = [
        one(h5, BASE, "LONG 1995-2021, no drawdown control"),
        one(h5, WITH_DD, "LONG 1995-2021, with drawdown (registered E10)"),
        one(late, BASE, "graded window 2010-2021, no drawdown control"),
        one(late, WITH_DD, "graded window 2010-2021, with drawdown"),
        one(early, BASE, "added origins only 1995-2009, no drawdown control"),
        one(early, WITH_DD, "added origins only 1995-2009, with drawdown"),
    ]

    res = {
        "cell": "E10_DECOMPOSITION",
        "registered": False,
        "status": "POST-HOC. Cannot change the E10 verdict (SUPPORTED) or any grade.",
        "purpose": "attribute the hpi_gap sign change to sample period vs bust control",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": "y_hpi", "horizon": 5,
        "specifications": rows,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = Path("out") / f"long_panel_decomp_{stamp}.json"
    p.write_text(json.dumps(res, indent=2, default=str))

    print(f"{'specification':46}{'origins':>10}{'n':>7}{'gap_coef':>11}{'gap_t':>8}{'gap_sp':>8}")
    for r in rows:
        if r.get("status") != "OK":
            print(f"{r['label']:46}{'--':>10}{r.get('n',0):>7}"); continue
        g = r["hpi_gap"]
        print(f"{r['label']:46}{r['origins']:>10}{r['n']:>7}{g['coef']:>11.6f}"
              f"{g['t']:>8}{g['share_positive']:>8}")
    print(f"\n{'specification':46}{'vol_coef':>11}{'vol_t':>8}{'vol_sp':>8}")
    for r in rows:
        if r.get("status") != "OK":
            continue
        v = r["hpi_vol"]
        print(f"{r['label']:46}{v['coef']:>11.6f}{v['t']:>8}{v['share_positive']:>8}")
    print("\nwrote", p)


if __name__ == "__main__":
    main()
