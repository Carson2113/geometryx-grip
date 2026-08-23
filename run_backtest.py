#!/usr/bin/env python3
"""GRIP-1 reference run.

Builds a vintage-locked metro panel from public-domain federal files, runs the
rolling-origin evaluation, the CLOCK_LEAK audit and the shock suite, and writes
an immutable scorecard to out/.

    python run_backtest.py --horizon 5
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV

from grip import evaluate, leakage, panel as panel_mod, shocks
from grip.sources import bps as bps_src
from grip.sources import cbsa as cbsa_src
from grip.sources import fhfa as fhfa_src

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

RAW_FEATURES = [
    "pop_g1", "pop_g3", "pop_accel",
    "hpi_g1", "hpi_g5", "hpi_gap", "hpi_vol",
    "permits_pc", "permits_g3",
]
MODEL_FEATURES = [f + "_wr" for f in RAW_FEATURES]
BASELINE = "pop_g1_wr"  # prior one-year population growth: beat the composite 8/8


def build(origins: list[int], horizon: int) -> pd.DataFrame:
    # Boundary-comparable metro set across the delineation vintages in play.
    vints = sorted({cbsa_src.delineation_for_origin(o) for o in origins})
    print(f"[geo] delineation vintages in play: {vints}")
    eligible = cbsa_src.boundary_comparable(vints)
    print(f"[geo] boundary-comparable metros across all vintages: {len(eligible)}")

    truth_cw = cbsa_src.crosswalk(max(vints))
    frames = []
    for o in origins:
        try:
            f = panel_mod.features_at_origin(o, eligible=eligible)
        except Exception as exc:  # noqa: BLE001
            print(f"[skip] origin {o}: {exc}")
            continue
        if f.empty:
            print(f"[skip] origin {o}: no rows")
            continue
        t = panel_mod.targets_from_base(o - 1, horizon, truth_cw)
        merged = f.merge(t, on="cbsa_code", how="inner")
        merged = merged.dropna(subset=["y_pop"])
        if merged.empty:
            print(f"[skip] origin {o}: no realised outcomes at h={horizon}")
            continue
        frames.append(merged)
        print(f"[panel] origin {o}: {len(merged)} metros, base={o-1}, target {o-1}->{o-1+horizon}")

    if not frames:
        raise SystemExit("no usable origins -- check horizon against available truth years")
    p = pd.concat(frames, ignore_index=True)
    p = panel_mod.demean_within(p, RAW_FEATURES + ["y_pop", "y_hpi"], by=("origin_year", "division"))
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--first-origin", type=int, default=2006)
    ap.add_argument("--last-origin", type=int, default=2025)
    ap.add_argument("--members", type=int, default=20,
                    help=f"ensemble members per origin (protocol floor {evaluate.MIN_MEMBERS})")
    args = ap.parse_args()

    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    origins = list(range(args.first_origin, args.last_origin + 1))
    p = build(origins, args.horizon)

    target = "y_pop_wr"
    print(f"\n[panel] {len(p)} rows across {p['origin_year'].nunique()} origins")

    # --- CLOCK_LEAK audit -------------------------------------------------
    leak = leakage.clock_leak_report(p, MODEL_FEATURES)
    vintage_checks = leakage.assert_no_frozen_percentiles(p)
    print("\n=== CLOCK_LEAK audit ===")
    print(leak.to_string(index=False))
    print(json.dumps(vintage_checks, indent=2))

    banned = set(leak.loc[leak["verdict"] == "FAIL", "feature"]) if not leak.empty else set()
    feats = [f for f in MODEL_FEATURES if f not in banned]
    if banned:
        print(f"\n[leak] excluded from the model: {sorted(banned)}")

    # --- E1 descriptive ---------------------------------------------------
    desc = evaluate.descriptive_skill(p, feats, target)

    # --- E2/E3 rolling origin --------------------------------------------
    res, preds = evaluate.expanding_origin_eval(
        p, feats, target, BASELINE, n_members=args.members
    )
    print("\n=== E2/E3 rolling-origin skill (strictly causal, ensemble mean) ===")
    if res.empty:
        print("insufficient origins for an expanding-window test")
    else:
        cols = [
            "test_origin", "n_test_metros", "n_members", "model_spearman",
            "member_spearman_min", "member_spearman_max", "members_beating_baseline",
            "single_fit_spearman", "baseline_spearman", "beats_baseline",
        ]
        print(res[cols].to_string(index=False))
        print("\n=== ensemble dispersion ===")
        print(
            res[[
                "test_origin", "mean_member_spread", "ensemble_rmse",
                "parameter_spread_to_error_ratio",
                "predictive_interval_width_90", "predictive_interval_coverage_90",
            ]].to_string(index=False)
        )

    # Protocol section 10 submission format, emitted so the reference run is
    # itself a conformant submission rather than a special case.
    if not preds.empty:
        pred_path = OUT / f"predictions_h{args.horizon}.csv"
        preds.to_csv(pred_path, index=False)
        per_cell = preds.groupby(["origin_year", "cbsa_code"]).size()
        print(
            f"\n[submission] wrote {pred_path.name}: {len(preds):,} rows, "
            f"min members per (origin, metro) = {int(per_cell.min())}"
        )
        assert int(per_cell.min()) >= evaluate.MIN_MEMBERS, "submission violates the member floor"

    # --- E4 coefficient stability ----------------------------------------
    stab = evaluate.coefficient_stability(res, feats)
    print("\n=== E4 coefficient stability ===")
    print(stab.to_string(index=False) if not stab.empty else "n/a")

    # --- E5 shock suite ---------------------------------------------------
    Xall = p.dropna(subset=feats + [target])
    Xs = Xall[feats].to_numpy(float)
    Xs = (Xs - Xs.mean(0)) / np.where(Xs.std(0) == 0, 1, Xs.std(0))
    full_model = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(Xs, Xall[target].to_numpy(float))
    shock_results = shocks.run_suite(full_model, Xall, feats)
    print("\n=== E5 shock plausibility ===")
    for s in shock_results:
        print(f"  {s['shock']}: {s.get('verdict', s['status'])}  rel={s.get('relative_response')}")

    # --- scorecard --------------------------------------------------------
    summary = {}
    if not res.empty:
        beat_counts = [
            int(s.split("/")[0]) for s in res["members_beating_baseline"]
        ]
        member_totals = [int(s.split("/")[1]) for s in res["members_beating_baseline"]]
        summary = {
            "n_origins_scored": int(len(res)),
            # Protocol section 9 compliance, stated as a number rather than a claim.
            "ensemble_members_min": int(res["n_members"].min()),
            "ensemble_protocol_floor": evaluate.MIN_MEMBERS,
            "ensemble_conforms": bool(res["n_members"].min() >= evaluate.MIN_MEMBERS),
            # The verdict-robustness statistic: across all origins, what share of
            # individual members would have beaten the baseline had that member
            # been the one shipped. A verdict that only holds for the ensemble
            # mean is not a verdict about the method.
            "member_share_beating_baseline": round(
                sum(beat_counts) / sum(member_totals), 4
            ),
            "median_single_fit_spearman": round(float(res["single_fit_spearman"].median()), 4),
            "median_mean_member_spread": round(float(res["mean_member_spread"].median()), 6),
            "median_parameter_spread_to_error_ratio": round(
                float(res["parameter_spread_to_error_ratio"].median()), 4
            ),
            # A 90% interval should cover 90% of outcomes. This is the number that
            # decides whether any published Geometryx interval is meaningful.
            "median_predictive_interval_coverage_90": (
                round(float(res["predictive_interval_coverage_90"].median()), 4)
                if res["predictive_interval_coverage_90"].notna().any() else None
            ),
            "median_predictive_interval_width_90": (
                round(float(res["predictive_interval_width_90"].median()), 6)
                if res["predictive_interval_width_90"].notna().any() else None
            ),
            "median_model_spearman": round(float(res["model_spearman"].median()), 4),
            "median_baseline_spearman": round(float(res["baseline_spearman"].median()), 4),
            "origins_beating_baseline": f"{int(res['beats_baseline'].sum())}/{len(res)}",
            "median_model_hit_rate": round(float(res["model_hit_rate"].median()), 4),
            "median_baseline_hit_rate": round(float(res["baseline_hit_rate"].median()), 4),
            "median_model_oos_r2": round(float(res["model_oos_r2"].median()), 4),
            "median_baseline_oos_r2": round(float(res["baseline_oos_r2"].median()), 4),
            # Paired, per-origin differences. Unpaired medians can favour the
            # model while it loses on almost every origin, which is exactly what
            # the first horizon-3 run did: median rho 0.753 vs 0.746 while the
            # baseline won 7 of 8 origins. Only the paired statistic is honest.
            "median_paired_rho_gain": round(
                float((res["model_spearman"] - res["baseline_spearman"]).median()), 4
            ),
            "median_paired_r2_gain": round(
                float((res["model_oos_r2"] - res["baseline_oos_r2"]).median()), 4
            ),
            "median_paired_hit_rate_gain": round(
                float((res["model_hit_rate"] - res["baseline_hit_rate"]).median()), 4
            ),
        }

    scorecard = {
        "protocol": "GRIP-1",
        "run_started_utc": started,
        "target": target,
        "horizon_years": args.horizon,
        "origins_requested": origins,
        "origins_in_panel": sorted(int(x) for x in p["origin_year"].unique()),
        "n_panel_rows": int(len(p)),
        "n_metros_median_per_origin": int(p.groupby("origin_year").size().median()),
        "features_offered": MODEL_FEATURES,
        "features_used": feats,
        "features_banned_by_clock_leak": sorted(banned),
        "baseline": BASELINE,
        "vintage_lock_checks": vintage_checks,
        "E1_descriptive": desc,
        "E2_E3_rolling_origin": json.loads(res.to_json(orient="records")) if not res.empty else [],
        "E4_coefficient_stability": json.loads(stab.to_json(orient="records")) if not stab.empty else [],
        "E5_shocks": shock_results,
        "CLOCK_LEAK_audit": json.loads(leak.to_json(orient="records")) if not leak.empty else [],
        "summary": summary,
        "declared_deviations": [bps_src.DEVIATION, fhfa_src.VINTAGE_DEVIATION],
        "attribution": [
            fhfa_src.DISCLAIMER,
            "Building permits: U.S. Census Bureau Building Permits Survey (public domain).",
            "Population estimates: U.S. Census Bureau Population Estimates Program (public domain).",
            "Metro delineations: OMB/U.S. Census Bureau delineation files (public domain).",
        ],
    }

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = OUT / f"scorecard_h{args.horizon}_{stamp}.json"
    path.write_text(json.dumps(scorecard, indent=2))
    (OUT / "latest.json").write_text(json.dumps(scorecard, indent=2))
    p.to_parquet(OUT / f"panel_h{args.horizon}.parquet", index=False)

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
