#!/usr/bin/env python3
"""E6: does the pre-registered premium sign survive contact with real premiums?

GRIP-1 grades a `premium_shock_40pct` counterfactual whose pre-registered
direction is a RELATIVE DECLINE in the shocked metros. In every graded cell that
shock returns the wrong sign. The shocked feature, however, is `hpi_vol` -- a
house-price volatility term standing in for insurance cost, because no free
premium series existed when the protocol was written.

Treasury FIO PCMI is a real premium series. It cannot be a graded predictor
(grip.sources.fio.VINTAGE_VERDICT), so this is not a forecast test and nothing
here enters a certification gate. It answers one narrower question:

    when we regress subsequent metro growth on ACTUAL insurance premiums,
    does the sign come out negative, as pre-registered?

If it does, the graded inversion is an artifact of the hpi_vol proxy and the
named fix is to swap the feature. If it does not, the pre-registered sign is
itself wrong about the United States, and PROTOCOL section 8 forbids quietly
flipping it.

Usage: python run_premium_diagnostic.py
Writes out/premium_diagnostic_<stamp>.json and prints a summary.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grip.sources import cbsa as cbsa_src
from grip.sources import fhfa as fhfa_src
from grip.sources import fio as fio_src
from grip.sources import pep as pep_src

OUT = Path(__file__).resolve().parent / "out"
DELINEATION = 2020  # the delineation in force over the FIO content window

# Pre-registered direction, copied verbatim in spirit from PROTOCOL section 8:
# a rise in insurance cost should be associated with RELATIVELY SLOWER growth.
EXPECTED_SIGN = -1

PREDICTORS = ["premium_log_2022", "premium_g4", "nonrenewal_2022"]


def _ols_hc1(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS with heteroskedasticity-robust (HC1) standard errors."""
    n, k = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    meat = (X * resid[:, None]).T @ (X * resid[:, None])
    cov = xtx_inv @ meat @ xtx_inv * (n / max(n - k, 1))
    return beta, np.sqrt(np.diag(cov))


def _demean(df: pd.DataFrame, cols: list[str], by: str = "division") -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        out[c] = out[c] - out.groupby(by)[c].transform("mean")
    return out


def build() -> pd.DataFrame:
    cw = cbsa_src.crosswalk(DELINEATION)

    # Population, aggregated to metro on the same delineation.
    truth = pep_src.truth_population()
    pop = (
        truth.merge(cw[["fips", "cbsa_code"]], on="fips", how="inner")
        .groupby(["cbsa_code", "year"], as_index=False)["pop"]
        .sum()
        .pivot(index="cbsa_code", columns="year", values="pop")
    )
    pop_last = int(max(c for c in pop.columns))

    hpi = fhfa_src.annual_hpi().pivot(index="cbsa_code", columns="year", values="hpi")
    hpi_last = int(max(c for c in hpi.columns))

    base = fio_src.LAST_DATA_YEAR  # 2022
    pop_h = pop_last - base
    hpi_h = hpi_last - base

    d = pd.DataFrame(index=pop.index.union(hpi.index))
    # Outcomes: annualised growth from the end of the FIO window forward.
    d["y_pop"] = (pop[pop_last] / pop[base]) ** (1 / pop_h) - 1
    d["y_hpi"] = (hpi[hpi_last] / hpi[base]) ** (1 / hpi_h) - 1
    # Momentum controls measured through the same base year, so the premium
    # coefficient is not just reading off pre-existing trend.
    d["pop_g3"] = (pop[base] / pop[base - 3]) ** (1 / 3) - 1
    d["hpi_g5"] = (hpi[base] / hpi[base - 5]) ** (1 / 5) - 1

    feat = fio_src.metro_premium_features(DELINEATION).set_index("cbsa_code")
    d = d.join(feat, how="inner")

    # Census division, inherited as the modal division of the metro's counties,
    # matching grip.sources.pep.
    div = (
        truth.merge(cw[["fips", "cbsa_code"]], on="fips", how="inner")
        .groupby("cbsa_code")["division"]
        .agg(lambda s: s.mode().iat[0])
    )
    d = d.join(div.rename("division"), how="inner")
    d.attrs["pop_h"] = pop_h
    d.attrs["hpi_h"] = hpi_h
    d.attrs["pop_last"] = pop_last
    d.attrs["hpi_last"] = hpi_last
    d.attrs["base"] = base
    return d.reset_index()


def regress(d: pd.DataFrame, target: str) -> dict:
    ctrl = "pop_g3" if target == "y_pop" else "hpi_g5"
    cols = [target, ctrl] + PREDICTORS
    sub = d.dropna(subset=cols + ["division"]).copy()
    sub = _demean(sub, cols)  # within-division demeaning == division fixed effects

    res: dict = {"target": target, "control": ctrl, "n_metros": int(len(sub))}

    # Standardise predictors so coefficients are comparable across metrics.
    z = {c: (sub[c] - sub[c].mean()) / sub[c].std(ddof=1) for c in PREDICTORS + [ctrl]}
    y = sub[target].values

    res["univariate"] = {}
    for c in PREDICTORS:
        X = np.column_stack([np.ones(len(sub)), z[c].values])
        b, se = _ols_hc1(X, y)
        res["univariate"][c] = _entry(b[1], se[1], len(sub), 2)

    res["with_momentum"] = {}
    X = np.column_stack([np.ones(len(sub))] + [z[c].values for c in PREDICTORS + [ctrl]])
    b, se = _ols_hc1(X, y)
    for i, c in enumerate(PREDICTORS + [ctrl], start=1):
        res["with_momentum"][c] = _entry(b[i], se[i], len(sub), X.shape[1])
    # The momentum control has no pre-registered direction; do not imply it does.
    for k in ("expected_sign", "matches_expected"):
        res["with_momentum"][ctrl][k] = None

    # Quartile contrast on the raw (not demeaned) premium level, which is the
    # form the Geometryx sign inversions are already on record in.
    raw = d.dropna(subset=[target, "premium_log_2022"]).copy()
    q = raw["premium_log_2022"].quantile([0.25, 0.75])
    lo = raw[raw["premium_log_2022"] <= q.loc[0.25]][target]
    hi = raw[raw["premium_log_2022"] >= q.loc[0.75]][target]
    res["quartile_contrast"] = {
        "high_premium_mean_growth": round(float(hi.mean()), 6),
        "low_premium_mean_growth": round(float(lo.mean()), 6),
        "difference": round(float(hi.mean() - lo.mean()), 6),
        "n_high": int(len(hi)),
        "n_low": int(len(lo)),
        "expected_difference_sign": EXPECTED_SIGN,
        "observed_difference_sign": int(np.sign(hi.mean() - lo.mean())),
        "matches_expected": bool(np.sign(hi.mean() - lo.mean()) == EXPECTED_SIGN),
    }
    # Robustness: the obvious objection is that this is Florida and the Gulf
    # doing all the work. Divisions 5-7 are South Atlantic, East South Central
    # and West South Central. Re-fit the premium level coefficient without them.
    ex = d[~d["division"].isin([5, 6, 7])].dropna(subset=cols + ["division"]).copy()
    ex = _demean(ex, cols)
    zx = (ex["premium_log_2022"] - ex["premium_log_2022"].mean()) / ex[
        "premium_log_2022"
    ].std(ddof=1)
    zc = (ex[ctrl] - ex[ctrl].mean()) / ex[ctrl].std(ddof=1)
    Xe = np.column_stack([np.ones(len(ex)), zx.values, zc.values])
    be, see = _ols_hc1(Xe, ex[target].values)
    res["ex_south"] = {
        "n_metros": int(len(ex)),
        "premium_log_2022": _entry(be[1], see[1], len(ex), 3),
    }
    return res


def _entry(beta: float, se: float, n: int, k: int) -> dict:
    t = beta / se if se > 0 else np.nan
    return {
        "beta_per_sd": round(float(beta), 6),
        "se": round(float(se), 6),
        "t": round(float(t), 3),
        "significant_5pct": bool(abs(t) > 1.96),
        "expected_sign": EXPECTED_SIGN,
        "observed_sign": int(np.sign(beta)),
        "matches_expected": bool(np.sign(beta) == EXPECTED_SIGN),
    }


def main() -> None:
    d = build()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = {
        "diagnostic": "E6_premium_sign",
        "generated_utc": stamp,
        "status": "DESCRIPTIVE -- NOT A GRADED FORECAST",
        "why_not_graded": fio_src.VINTAGE_VERDICT.strip(),
        "fio_coverage": fio_src.coverage_report(DELINEATION),
        "delineation_vintage": DELINEATION,
        "base_year": d.attrs.get("base", fio_src.LAST_DATA_YEAR),
        "outcome_windows": {
            "y_pop": f"{fio_src.LAST_DATA_YEAR}->{d.attrs['pop_last']}",
            "y_hpi": f"{fio_src.LAST_DATA_YEAR}->{d.attrs['hpi_last']}",
        },
        "expected_sign": EXPECTED_SIGN,
        "results": [regress(d, t) for t in ("y_pop", "y_hpi")],
    }

    flat = []
    for r in out["results"]:
        for block in ("univariate", "with_momentum"):
            for c in PREDICTORS:
                flat.append(r[block][c]["matches_expected"])
    out["verdict"] = {
        "tests": len(flat),
        "matching_pre_registered_sign": int(sum(flat)),
        "premium_sign_confirmed": bool(sum(flat) == len(flat)),
    }

    OUT.mkdir(exist_ok=True)
    p = OUT / f"premium_diagnostic_{stamp}.json"
    p.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("why_not_graded", "fio_coverage")}, indent=2))
    print("\nwrote", p)


if __name__ == "__main__":
    main()
