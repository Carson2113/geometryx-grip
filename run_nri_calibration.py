"""E7: can FEMA NRI expected annual loss stand in for an insurance premium?

Out-of-panel diagnostic. Never scored, never in a gate. See PROTOCOL section 8.

E6 established two things. On house prices the pre-registered negative sign on
insurance cost is real when measured with actual Treasury FIO premiums
(-0.00523 per SD, t = -6.82). And the graded shock `premium_shock_40pct` fails
because the feature it perturbs, `hpi_vol`, is a house-price volatility term
standing in for insurance cost rather than a measure of it. FIO cannot fix that:
published 2025-01-16, it is never both vintage-legal and scorable.

So the question is whether a free, federal, non-FIO series can carry the same
signal. FEMA's National Risk Index publishes a modelled Expected Annual Loss in
dollars per county against the building exposure it is computed on, and the
ratio is a pure premium rate. This script asks three questions in order, and the
order matters because a failure at any stage makes the next one moot.

  E7a  Does the NRI loss rate track what people actually pay? Regress the FIO
       log premium per policy on the log NRI loss rate. If a proxy does not
       correlate with the thing it proxies, nothing else is worth testing.

  E7b  Does the NRI loss rate reproduce the E6 outcome coefficients? Same
       specification as E6 -- demeaned within Census division, momentum
       controlled, HC1 errors, predictors standardised -- with the loss rate
       substituted for the premium. A usable replacement has to give the same
       sign on both targets, not just on the one that worked.

  E7c  Does it survive controlling for the premium? If the loss rate only
       matters through premium, it is a clean substitute. If it carries an
       independent coefficient, it is measuring something else and the
       substitution is not what it appears to be.

Sources
  FEMA National Risk Index Counties (ArcGIS), December 2025 release
    https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0
  Treasury FIO, Analyses of U.S. Homeowners Insurance Markets 2018-2022
    https://home.treasury.gov/news/press-releases/jy2791
  FHFA House Price Index, metro annual (see grip/sources/fhfa.py)
    This product uses FHFA Data but is neither endorsed nor certified by FHFA.
  Census Population Estimates Program (see grip/sources/pep.py)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from grip.sources import cbsa as cbsa_src
from grip.sources import fhfa as fhfa_src
from grip.sources import fio as fio_src
from grip.sources import nri as nri_src
from grip.sources import pep as pep_src

OUT = Path(__file__).resolve().parent / "out"
DELINEATION = 2020

STATUS = "DESCRIPTIVE -- NOT A GRADED FORECAST"

# The E6 result this diagnostic is calibrated against, copied from
# out/E6_PREMIUM_SIGN.md so the comparison is explicit rather than remembered.
E6_TARGET = {
    "y_hpi": {"beta_per_sd": -0.005234, "t": -6.822},
    "y_pop": {"beta_per_sd": 0.000720, "t": 2.122},
}
EXPECTED_SIGN = -1  # pre-registered in v1.0.0-grip1, unchanged

SOUTH = {5, 6, 7}  # South Atlantic, East South Central, West South Central


def _ols_hc1(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    n, k = X.shape
    scale = n / max(n - k, 1)
    meat = (X * (resid**2)[:, None]).T @ X * scale
    cov = XtX_inv @ meat @ XtX_inv
    return beta, np.sqrt(np.clip(np.diag(cov), 0, None))


def _demean(df: pd.DataFrame, cols: list[str], by: str = "division") -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        out[c] = out[c] - out.groupby(by)[c].transform("mean")
    return out


def _entry(name: str, beta: float, se: float, n: int, k: int,
           expected: int | None = EXPECTED_SIGN) -> dict:
    t = beta / se if se > 0 else float("nan")
    e = {
        "predictor": name,
        "beta_per_sd": round(float(beta), 6),
        "se": round(float(se), 6),
        "t": round(float(t), 3),
        "n": int(n),
        "k": int(k),
    }
    if expected is None:
        e["expected_sign"] = None
        e["matches_expected"] = None
    else:
        e["expected_sign"] = expected
        e["matches_expected"] = bool(np.sign(beta) == expected)
    return e


def build() -> pd.DataFrame:
    """Metro panel: outcomes, momentum, FIO premiums, NRI loss rate, division."""
    cw = cbsa_src.crosswalk(DELINEATION)

    truth = pep_src.truth_population()
    cty = truth.merge(cw[["fips", "cbsa_code"]], on="fips", how="inner")
    pop = (
        cty.groupby(["cbsa_code", "year"], as_index=False)["pop"].sum()
        .pivot(index="cbsa_code", columns="year", values="pop")
    )
    pop_last = int(max(pop.columns))

    hpi = fhfa_src.annual_hpi().pivot(index="cbsa_code", columns="year", values="hpi")
    hpi_last = int(max(hpi.columns))

    base = fio_src.LAST_DATA_YEAR  # 2022, end of the FIO content window
    pop_h = pop_last - base
    hpi_h = hpi_last - base

    d = pd.DataFrame(index=pop.index.union(hpi.index))
    d["y_pop"] = (pop[pop_last] / pop[base]) ** (1 / pop_h) - 1
    d["y_hpi"] = (hpi[hpi_last] / hpi[base]) ** (1 / hpi_h) - 1
    d["pop_g3"] = (pop[base] / pop[base - 3]) ** (1 / 3) - 1
    d["hpi_g5"] = (hpi[base] / hpi[base - 5]) ** (1 / 5) - 1

    prem = fio_src.metro_premium_features(DELINEATION).set_index("cbsa_code")
    d = d.join(prem[["premium_log_2022", "premium_g4", "nonrenewal_2022"]], how="left")

    eal = nri_src.metro_eal(DELINEATION).set_index("cbsa_code")
    keep = ["eal_rate", "eal_rate_log", "eal_per_cap", "wfir_share",
            "flood_share", "wind_share", "n_counties"]
    d = d.join(eal[keep], how="left")

    div = cty.groupby("cbsa_code")["division"].agg(lambda s: s.mode().iat[0])
    d = d.join(div.rename("division"), how="inner")

    d.attrs.update(pop_h=pop_h, hpi_h=hpi_h, base=base,
                   pop_last=pop_last, hpi_last=hpi_last)
    return d.reset_index()


# --- E7a: does the proxy track the premium? -------------------------------

def proxy_fidelity(d: pd.DataFrame) -> dict:
    cols = ["premium_log_2022", "eal_rate_log"]
    s = d.dropna(subset=cols + ["division"]).copy()
    n = len(s)

    raw_pearson = float(np.corrcoef(s["eal_rate_log"], s["premium_log_2022"])[0, 1])
    raw_spearman = float(s["eal_rate_log"].corr(s["premium_log_2022"], method="spearman"))

    # Pooled: log premium on log loss rate.
    X = np.column_stack([np.ones(n), s["eal_rate_log"].to_numpy()])
    y = s["premium_log_2022"].to_numpy()
    b, se = _ols_hc1(X, y)
    resid = y - X @ b
    r2_pooled = 1 - resid.var() / y.var()

    # Within division, which is the space E6 works in.
    w = _demean(s, cols)
    n_w = len(w)
    Xw = np.column_stack([np.ones(n_w), w["eal_rate_log"].to_numpy()])
    yw = w["premium_log_2022"].to_numpy()
    bw, sew = _ols_hc1(Xw, yw)
    r2_within = 1 - (yw - Xw @ bw).var() / yw.var() if yw.var() > 0 else float("nan")
    within_pearson = float(np.corrcoef(w["eal_rate_log"], w["premium_log_2022"])[0, 1])

    # An elasticity of 1 would mean a metro with twice the modelled loss rate
    # charges twice the premium. Report the gap from 1 explicitly.
    return {
        "n_metros": n,
        "pooled": {
            "pearson": round(raw_pearson, 4),
            "spearman": round(raw_spearman, 4),
            "r2": round(float(r2_pooled), 4),
            "elasticity": round(float(b[1]), 4),
            "se": round(float(se[1]), 4),
            "t": round(float(b[1] / se[1]), 3),
        },
        "within_division": {
            "pearson": round(within_pearson, 4),
            "r2": round(float(r2_within), 4),
            "elasticity": round(float(bw[1]), 4),
            "se": round(float(sew[1]), 4),
            "t": round(float(bw[1] / sew[1]), 3),
        },
        "interpretation_note": (
            "An elasticity of 1.0 would mean premium scales one-for-one with "
            "modelled loss rate. r2 is the share of cross-metro variation in "
            "what people pay that the free proxy explains."
        ),
    }


# --- E7b / E7c: outcome coefficients --------------------------------------

def regress(d: pd.DataFrame, target: str) -> dict:
    momentum = "pop_g3" if target == "y_pop" else "hpi_g5"
    base_cols = [target, "eal_rate_log", momentum]
    s = d.dropna(subset=base_cols + ["division"]).copy()

    res: dict = {"target": target, "momentum_control": momentum,
                 "n_metros": int(len(s)), "e6_reference": E6_TARGET[target]}

    def fit(frame: pd.DataFrame, cols: list[str], label: str,
            expected_map: dict[str, int | None]) -> list[dict]:
        f = frame.dropna(subset=cols + [target, "division"]).copy()
        w = _demean(f, cols + [target])
        n = len(w)
        Z = np.column_stack([w[c].to_numpy() for c in cols])
        # Standardise so each beta is per standard deviation, as in E6.
        sd = Z.std(axis=0, ddof=1)
        sd[sd == 0] = 1.0
        Z = Z / sd
        X = np.column_stack([np.ones(n), Z])
        b, se = _ols_hc1(X, w[target].to_numpy())
        rows = []
        for i, c in enumerate(cols, start=1):
            rows.append(_entry(c, b[i], se[i], n, X.shape[1],
                               expected=expected_map.get(c, None)))
        for r in rows:
            r["spec"] = label
        return rows

    # E7b: the E6 specification with the proxy substituted for the premium.
    res["substituted"] = fit(
        s, ["eal_rate_log", momentum], "proxy + momentum",
        {"eal_rate_log": EXPECTED_SIGN},
    )

    # E7c: horse race against the premium it is meant to replace.
    both = s.dropna(subset=["premium_log_2022"])
    res["horse_race"] = fit(
        both, ["eal_rate_log", "premium_log_2022", momentum],
        "proxy + premium + momentum",
        {"eal_rate_log": EXPECTED_SIGN, "premium_log_2022": EXPECTED_SIGN},
    )
    res["horse_race_n"] = int(len(both))

    # Hazard composition, to see whether one peril carries the whole signal.
    res["composition"] = fit(
        s, ["wfir_share", "flood_share", "wind_share", momentum],
        "hazard shares + momentum", {},
    )

    # Regional conditionality, the objection E6 answered for the premium.
    ex = s[~s["division"].isin(SOUTH)]
    res["ex_south"] = fit(
        ex, ["eal_rate_log", momentum], "ex-South, proxy + momentum",
        {"eal_rate_log": EXPECTED_SIGN},
    )
    res["ex_south_n"] = int(len(ex))

    # Quartile contrast on the raw proxy, no controls, for a readable number.
    q = s.dropna(subset=["eal_rate"]).copy()
    if len(q) >= 40:
        lo, hi = q["eal_rate"].quantile([0.25, 0.75])
        top = q[q["eal_rate"] >= hi][target]
        bot = q[q["eal_rate"] <= lo][target]
        res["quartile_contrast"] = {
            "top_quartile_growth_pct": round(100.0 * float(top.mean()), 3),
            "bottom_quartile_growth_pct": round(100.0 * float(bot.mean()), 3),
            "gap_pp": round(100.0 * float(top.mean() - bot.mean()), 3),
            "n_top": int(len(top)),
            "n_bottom": int(len(bot)),
            "matches_expected": bool(top.mean() < bot.mean()),
        }
    return res


def main() -> None:
    OUT.mkdir(exist_ok=True)
    d = build()

    fidelity = proxy_fidelity(d)
    targets = {t: regress(d, t) for t in ("y_hpi", "y_pop")}

    # Verdict. A replacement has to clear all three bars.
    sub_signs = {
        t: next(r for r in targets[t]["substituted"] if r["predictor"] == "eal_rate_log")
        for t in targets
    }
    tracks_premium = fidelity["pooled"]["r2"] >= 0.25 and fidelity["pooled"]["elasticity"] > 0
    reproduces_hpi = sub_signs["y_hpi"]["matches_expected"] and abs(sub_signs["y_hpi"]["t"]) >= 2
    magnitude_ratio = (
        sub_signs["y_hpi"]["beta_per_sd"] / E6_TARGET["y_hpi"]["beta_per_sd"]
        if E6_TARGET["y_hpi"]["beta_per_sd"] else float("nan")
    )

    payload = {
        "diagnostic": "E7",
        "title": "FEMA NRI expected annual loss as a premium proxy",
        "status": STATUS,
        "why_not_a_forecast": (
            "The NRI release read here was published 2025-12-18 and FEMA serves "
            "one mutable layer, so it is not vintage-legal for any scorable "
            "origin. Independently, the first NRI release was 2020-10, so no "
            "archived vintage could reach origins before 2021 -- two of the "
            "thirteen graded h=3 origins and none at h=5. This is a measurement "
            "exercise about a feature, not a prediction."
        ),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "delineation_vintage": DELINEATION,
        "nri": {
            "release_label": nri_src.RELEASE_LABEL,
            "published": nri_src.PUBLISHED,
            "arcgis_item": nri_src.ITEM,
            "counties": int(len(nri_src.raw())),
        },
        "outcome_windows": {
            "base_year": d.attrs.get("base", 2022),
            "y_pop_horizon_years": d.attrs.get("pop_h"),
            "y_hpi_horizon_years": d.attrs.get("hpi_h"),
        },
        "pre_registered_sign": EXPECTED_SIGN,
        "e6_reference": E6_TARGET,
        "e7a_proxy_fidelity": fidelity,
        "e7b_e7c_outcomes": targets,
        "verdict": {
            "tracks_actual_premium": bool(tracks_premium),
            "reproduces_e6_price_sign": bool(reproduces_hpi),
            "magnitude_vs_e6_ratio": round(float(magnitude_ratio), 3),
            "eligible_as_graded_predictor": False,
            "recommended_as_premium_replacement": bool(tracks_premium and reproduces_hpi),
        },
        "deviations": nri_src.DEVIATIONS,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"nri_calibration_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
