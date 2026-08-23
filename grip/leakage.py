"""CLOCK_LEAK detection.

AIMIP forbids CO2 as a model input because "the steady rise of CO2 during
training could become a proxy for a clock, allowing a model to learn the timing
of individual events." The same failure destroyed the Geometryx composite's
point-in-time backtest: `appreciationYoY` carried coefficient +0.50111 and
inverted across the 2009/2010 crash, and frozen 2026 reference percentiles were
applied to 2010 origins so only 62 of 199 metros cleared the quality floor.

A feature fails CLOCK_LEAK if its cross-sectional mean drifts monotonically
across origin years, because such a feature encodes *when* rather than *where*.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def clock_leak_report(panel: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Per-feature drift diagnostics across origin years.

    Verdict:
      FAIL  - strong monotone drift (|rho| >= 0.8 and p < 0.05): acts as a clock.
      WARN  - moderate drift (|rho| >= 0.6).
      PASS  - no material monotone drift in the cross-sectional mean.
    """
    rows = []
    for f in features:
        if f not in panel:
            continue
        by_origin = panel.groupby("origin_year")[f].mean().dropna()
        if len(by_origin) < 5:
            rows.append({"feature": f, "n_origins": len(by_origin), "verdict": "INSUFFICIENT"})
            continue
        rho, p = stats.spearmanr(by_origin.index.values, by_origin.values)
        # Sign flips of the cross-sectional mean are a second warning sign: a
        # feature that changes sign across regimes cannot carry a stable weight.
        sign_flips = int((np.diff(np.sign(by_origin.values)) != 0).sum())
        verdict = "PASS"
        if abs(rho) >= 0.8 and p < 0.05:
            verdict = "FAIL"
        elif abs(rho) >= 0.6:
            verdict = "WARN"
        rows.append(
            {
                "feature": f,
                "n_origins": int(len(by_origin)),
                "drift_spearman": round(float(rho), 3),
                "p_value": round(float(p), 4),
                "mean_first_origin": round(float(by_origin.iloc[0]), 5),
                "mean_last_origin": round(float(by_origin.iloc[-1]), 5),
                "sign_flips": sign_flips,
                "verdict": verdict,
            }
        )
    return pd.DataFrame(rows).sort_values("verdict")


def assert_no_frozen_percentiles(panel: pd.DataFrame) -> dict:
    """Confirm every origin uses its own-vintage reference distribution.

    A frozen reference distribution computed from a later vintage is a
    look-ahead leak even when the underlying feature is legitimate.
    """
    checks = {}
    for col, expected in (("max_pep_vintage", "base_year"), ):
        if col in panel and expected in panel:
            bad = int((panel[col] != panel[expected]).sum())
            checks[f"{col}_matches_{expected}"] = {"violations": bad, "pass": bad == 0}
    if "delineation_vintage" in panel and "origin_year" in panel:
        bad = int((panel["delineation_vintage"] > panel["origin_year"]).sum())
        checks["delineation_not_from_future"] = {"violations": bad, "pass": bad == 0}
    return checks
