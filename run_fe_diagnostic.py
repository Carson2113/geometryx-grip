#!/usr/bin/env python3
"""E9: metro fixed effects and the E5 re-run.

Pre-registered in PROTOCOL.md section 13 and released, results-free, BEFORE this
script was executed. This is specification attempt 1 of the post-E5 budget: the
E5 failure was already known when the specification was chosen, so nothing here
can certify anything. See PROTOCOL section 13 for the accept/reject rule.

Reads the four cached graded panels rather than rebuilding them, so the panel is
byte-identical to the one v1.0.0-grip1 graded. Runs the UNMODIFIED shock suite
from grip/shocks.py against four specifications per cell:

    S0              the registered baseline, (origin_year, division) demeaning
    S1              two-way (origin_year, cbsa_code) within transformation
    S2              origin demeaning + expanding within-metro, S0's target
    S0_on_S2_sample S0 restricted to the rows S2 can score

The last one is the control that matters. S2 discards every metro's first few
origins, so a coefficient that moves between S0 and S2 could be the
specification or could be the smaller sample. Running S0 on S2's rows separates
them, and without it the comparison would be worthless.

    python run_fe_diagnostic.py
"""
from __future__ import annotations

import glob
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV

from grip import fe, panel as panel_mod, shocks

ROOT = Path(__file__).parent
OUT = ROOT / "out"

RAW_FEATURES = [
    "pop_g1", "pop_g3", "pop_accel",
    "hpi_g1", "hpi_g5", "hpi_gap", "hpi_vol",
    "permits_pc", "permits_g3",
]

# The two coefficients the entire shock gate hangs on. premium_shock_40pct
# perturbs hpi_vol_wr, rate_shock_200bp perturbs hpi_gap_wr, and both are the
# only SIGN-UNSTABLE entries in E4. Named here so the report cannot quietly
# drift onto a different pair.
FOCAL = ["hpi_vol_wr", "hpi_gap_wr"]

# Minimum origins a metro must appear in before it can contribute within-metro
# variation. A metro observed once is absorbed exactly by its own fixed effect
# and contributes a row of zeros, which would shrink the ridge penalty against
# nothing. Declared in the pre-registration.
MIN_ORIGINS_PER_METRO = 4

PREREG = {
    "registered_in": "PROTOCOL.md section 13",
    "specification_attempt": 1,
    "post_hoc": True,
    "post_hoc_reason": (
        "The E5 shock-sign failure was already published in v1.0.0-grip1 when "
        "this specification was selected. E9 is therefore a diagnostic and is "
        "barred from certifying any cell, whatever it returns."
    ),
    "min_within_metro_share": fe.MIN_WITHIN_SHARE,
    "min_origins_per_metro": MIN_ORIGINS_PER_METRO,
    "predictions": {
        "P1": (
            "In S1 the pooled coefficients on hpi_vol_wr and hpi_gap_wr both "
            "turn NEGATIVE, matching the pre-registered shock signs."
        ),
        "P2": (
            "In S1 the leave-one-origin-out share_positive for both focal "
            "features falls below 0.5, i.e. reliably negative rather than "
            "merely stable."
        ),
        "P3": (
            "In S2 the E5 verdicts for rate_shock_200bp and premium_shock_40pct "
            "both flip to PLAUSIBLE."
        ),
        "P4": (
            "Power precondition, not an outcome: any feature whose "
            "within_metro_share is below 0.10 is declared UNINFORMATIVE and its "
            "fixed-effects sign is not read as evidence in either direction."
        ),
    },
    "accept_rule": (
        "The confound hypothesis -- that the wrong-signed shock response is "
        "driven by persistent differences between metros rather than by a "
        "within-metro relationship -- is SUPPORTED only if P1 and P2 both hold "
        "for BOTH focal features and the P4 precondition passes for both. "
        "Anything partial is reported as NOT SUPPORTED."
    ),
    "reject_consequence": (
        "If the coefficients stay positive under a metro effect, the inversion "
        "is within-metro too, the estimator is not the problem, and the "
        "features are. That routes the fix to real measured quantities such as "
        "the NFIP realised losses graded in E8, not to a different regression."
    ),
    "cannot_do": (
        "E9 cannot certify. The four NOT CERTIFIED verdicts in v1.0.0-grip1 "
        "stand regardless of outcome. If P3 holds, S2 becomes a CANDIDATE that "
        "requires a fresh full backtest under a fresh pre-registration before "
        "any shock claim is made."
    ),
}


def latest_scorecard(slug: str, horizon: int) -> dict | None:
    hits = sorted(glob.glob(str(OUT / f"scorecard_{slug}_h{horizon}_*.json")))
    if not hits:
        return None
    return json.loads(Path(hits[-1]).read_text())


def build_specs(p: pd.DataFrame, target_raw: str) -> dict[str, tuple[pd.DataFrame, str]]:
    """Return {spec_name: (frame with *_wr columns, target column)}."""
    cols = RAW_FEATURES + [target_raw]

    # S0 -- exactly the transform run_backtest.py applies.
    s0 = panel_mod.demean_within(p, cols, by=("origin_year", "division"))
    tgt0 = target_raw + "_wr"

    # Metros with enough origins to carry within-metro information at all.
    counts = p.groupby("cbsa_code")["origin_year"].nunique()
    keep = set(counts[counts >= MIN_ORIGINS_PER_METRO].index)
    p_fe = p[p["cbsa_code"].isin(keep)].copy()

    # S1 -- features AND target within metro. Diagnostic only: the target term
    # is not computable at forecast time.
    s1 = fe.demean_twoway(p_fe, cols, keys=("origin_year", "cbsa_code"))

    # S2 -- features within metro on an expanding window; target as in S0.
    s2 = fe.demean_expanding_metro(p_fe, RAW_FEATURES)
    s2_t = panel_mod.demean_within(p_fe, [target_raw], by=("origin_year", "division"))
    s2 = s2.merge(
        s2_t[["origin_year", "cbsa_code", tgt0]],
        on=["origin_year", "cbsa_code"],
        how="left",
    )

    # Control -- S0's transform on the rows S2 can actually score.
    feat_wr = [f + "_wr" for f in RAW_FEATURES]
    s2_ok = s2.dropna(subset=feat_wr + [tgt0])[["origin_year", "cbsa_code"]]
    s0_ctl = s0.merge(s2_ok, on=["origin_year", "cbsa_code"], how="inner")

    return {
        "S0": (s0, tgt0),
        "S1": (s1, tgt0),
        "S2": (s2, tgt0),
        "S0_on_S2_sample": (s0_ctl, tgt0),
    }


def analyse(frame: pd.DataFrame, feats: list[str], target: str) -> dict:
    sub = frame.dropna(subset=feats + [target])
    if len(sub) < 60:
        return {"status": "INSUFFICIENT_DATA", "n": int(len(sub))}

    X = sub[feats].to_numpy(float)
    Xs = (X - X.mean(0)) / np.where(X.std(0) == 0, 1.0, X.std(0))
    y = sub[target].to_numpy(float)
    model = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(Xs, y)

    # The unmodified E5 suite, same code path as the graded run.
    shock_results = shocks.run_suite(model, sub, feats)

    loo = fe.loo_origin_coefficients(sub, feats, target)
    stab = fe.stability_from_loo(loo, feats)
    ols = fe.cluster_ols(sub, feats, target)

    return {
        "status": "RUN",
        "n": int(len(sub)),
        "n_metros": int(sub["cbsa_code"].nunique()),
        "n_origins": int(sub["origin_year"].nunique()),
        "origins": sorted(int(o) for o in sub["origin_year"].unique()),
        "in_sample_r2": round(float(model.score(Xs, y)), 4),
        "pooled_ridge_coefficients": {
            f: round(float(c), 6) for f, c in zip(feats, model.coef_)
        },
        "E5_shocks": shock_results,
        "loo_origin_stability": json.loads(stab.to_json(orient="records"))
        if not stab.empty
        else [],
        "clustered_ols": json.loads(ols.to_json(orient="records"))
        if not ols.empty
        else [],
    }


def verdict(cells: dict) -> dict:
    """Apply the pre-registered accept rule mechanically, per cell and overall."""
    per_cell = {}
    for cell, specs in cells.items():
        s1 = specs.get("S1", {})
        s2 = specs.get("S2", {})
        if s1.get("status") != "RUN":
            per_cell[cell] = {"verdict": "NOT_EVALUABLE"}
            continue

        vd = {f["feature"]: f for f in specs.get("variance_decomposition", [])}
        coefs = s1.get("pooled_ridge_coefficients", {})
        stab = {r["feature"]: r for r in s1.get("loo_origin_stability", [])}

        detail = {}
        p1 = p2 = p4 = True
        for f in FOCAL:
            raw = f.removesuffix("_wr")
            informative = bool(vd.get(raw, {}).get("informative_under_fe", False))
            within = vd.get(raw, {}).get("within_metro_share")
            c = coefs.get(f)
            sp = stab.get(f, {}).get("share_positive")
            f_p1 = c is not None and c < 0
            f_p2 = sp is not None and sp < 0.5
            detail[f] = {
                "within_metro_share": within,
                "informative_under_fe": informative,
                "S1_pooled_coef": c,
                "P1_negative": f_p1,
                "S1_loo_share_positive": sp,
                "P2_reliably_negative": f_p2,
            }
            p1 = p1 and f_p1
            p2 = p2 and f_p2
            p4 = p4 and informative

        s2_shocks = {s["shock"]: s.get("verdict") for s in s2.get("E5_shocks", [])}
        p3 = all(
            s2_shocks.get(k) == "PLAUSIBLE"
            for k in ("rate_shock_200bp", "premium_shock_40pct")
        )
        per_cell[cell] = {
            "P1_both_negative": p1,
            "P2_both_reliably_negative": p2,
            "P3_S2_shocks_plausible": p3,
            "P4_power_precondition_met": p4,
            "confound_hypothesis": "SUPPORTED" if (p1 and p2 and p4) else "NOT_SUPPORTED",
            "per_feature": detail,
            "S2_shock_verdicts": s2_shocks,
        }

    supported = [c for c, v in per_cell.items() if v.get("confound_hypothesis") == "SUPPORTED"]
    return {
        "per_cell": per_cell,
        "cells_supporting_confound_hypothesis": f"{len(supported)}/{len(per_cell)}",
        "certification_effect": "NONE -- E9 is a post-hoc diagnostic and cannot certify.",
    }


def main() -> None:
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cells: dict[str, dict] = {}

    for slug, target_raw in (("pop", "y_pop"), ("hpi", "y_hpi")):
        for horizon in (5, 3):
            pq = OUT / f"panel_{slug}_h{horizon}.parquet"
            if not pq.exists():
                print(f"[skip] {pq.name} missing")
                continue
            cell = f"{slug}_h{horizon}"
            p = pd.read_parquet(pq)

            sc = latest_scorecard(slug, horizon)
            feats = sc["features_used"] if sc else [f + "_wr" for f in RAW_FEATURES]
            banned = sc.get("features_banned_by_clock_leak", []) if sc else []
            print(f"\n=== {cell}: {len(p)} rows, {len(feats)} features "
                  f"(banned by CLOCK_LEAK: {banned or 'none'}) ===")

            specs = build_specs(p, target_raw)
            rec: dict = {
                "target_raw": target_raw,
                "horizon": horizon,
                "features_used": feats,
                "features_banned_by_clock_leak": banned,
                "graded_scorecard_certified": (
                    sc["certification"]["certified"] if sc else None
                ),
                "variance_decomposition": json.loads(
                    fe.variance_decomposition(p, RAW_FEATURES).to_json(orient="records")
                ),
            }
            for name, (frame, tgt) in specs.items():
                res = analyse(frame, feats, tgt)
                rec[name] = res
                if res.get("status") == "RUN":
                    sv = {s["shock"]: s.get("verdict", s["status"]) for s in res["E5_shocks"]}
                    focal = {f: res["pooled_ridge_coefficients"].get(f) for f in FOCAL}
                    print(f"  {name:16s} n={res['n']:5d} "
                          f"vol={focal['hpi_vol_wr']:+.5f} gap={focal['hpi_gap_wr']:+.5f}  {sv}")
                else:
                    print(f"  {name:16s} {res.get('status')} n={res.get('n')}")
            cells[cell] = rec

    report = {
        "experiment": "E9",
        "title": "Metro fixed effects and the E5 re-run",
        "run_started_utc": started,
        "pre_registration": PREREG,
        "specifications": {
            "S0": "registered baseline: (origin_year, division) demeaning",
            "S1": "two-way (origin_year, cbsa_code) within transformation; diagnostic only",
            "S2": "origin demeaning + expanding within-metro features, S0 target; forecast-legal",
            "S0_on_S2_sample": "S0 transform on S2's rows -- separates specification from sample",
        },
        "cells": cells,
        "verdict": verdict(cells),
    }

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = OUT / f"fe_diagnostic_{stamp}.json"
    path.write_text(json.dumps(report, indent=2))
    print("\n=== PRE-REGISTERED VERDICT ===")
    print(json.dumps(report["verdict"]["per_cell"], indent=2)[:4000])
    print(f"\ncells supporting confound hypothesis: "
          f"{report['verdict']['cells_supporting_confound_hypothesis']}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
