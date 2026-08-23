"""E8: can the NFIP flood series stand in for an insurance signal?

Out-of-panel diagnostic. Never scored, never in a gate. See PROTOCOL section 8
and Amendment 1.

E6 measured the price channel with actual Treasury FIO premiums and found the
pre-registered negative sign on house prices (-0.00523 per SD, t = -6.82). E7
substituted FEMA's modelled National Risk Index loss rate, reproduced both signs
at 56% of the price magnitude, and then found that in a horse race the NRI rate
collapsed while the premium survived. Both sources are Class C under Amendment 1:
retrospective constructs that can never be graded.

The NFIP is the first insurance source that is not Class C. Each paid claim is a
dollar amount settled on a dated loss and FEMA does not restate it, so the claims
file is Class B -- gradeable with a declared availability deviation. It also
reaches back to loss year 1978, far beyond anything else in the panel.

Two features are tested, and they are different objects:

  nfip_rate_per_1k_log  a regulated PRICE -- premium per $1,000 of building
                        coverage, from a stratified sample of 2022 policies
  nfip_loss_pc_log      a realised LOSS -- paid flood claims per resident per
                        year over a 20-year trailing window

Four questions, in order, because a failure at any stage makes the next moot.

  E8a  Do the NFIP series track what people actually pay for homeowners cover?
       Regress the FIO log premium on each. Pre-registered bar: R-squared >= 0.25.

  E8b  Do they reproduce the E6 outcome coefficients? The E6 specification --
       demeaned within Census division, momentum controlled, HC1 errors,
       predictors standardised -- with each series substituted for the premium.

  E8c  Do they survive controlling for the FIO premium, and for each other? A
       price and a loss measure of the same peril should not both carry
       independent signal if either is doing what it claims.

  E8d  THE PRE-REGISTERED FALSIFICATION TEST. E7 attributed the entire price
       signal to the wind share and found the flood share insignificant. If that
       is right, these flood-only measures must come in weaker than E7's
       all-hazard NRI coefficient. If they come in stronger, E7's hazard
       decomposition is wrong and this file says so.

Every threshold and expected sign in this script was published, with no results,
at commit 6ca77bbf0bcb13bbbf49a9301a3e364379bfb384 (2026-08-23T20:45:59Z),
release v1.5.0-prereg.

Sources
  OpenFEMA NfipClaims v3, 2,724,656 records, loss years 1978-2026
    https://www.fema.gov/api/open/v3/NfipClaims
  OpenFEMA NfipPolicies v3, 74,349,525 records, coverage from 2009-01-01
    https://www.fema.gov/api/open/v3/NfipPolicies
  Treasury FIO, Analyses of U.S. Homeowners Insurance Markets 2018-2022
    https://home.treasury.gov/news/press-releases/jy2791
  FEMA National Risk Index Counties (ArcGIS), December 2025 release
    https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0
  FHFA House Price Index, metro annual (see grip/sources/fhfa.py)
    This product uses FHFA Data but is neither endorsed nor certified by FHFA.
  Census Population Estimates Program (see grip/sources/pep.py)
  Census 2020 ZCTA-to-county relationship file (see grip/sources/nfip.py)
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
from grip.sources import nfip as nfip_src
from grip.sources import nri as nri_src
from grip.sources import pep as pep_src

OUT = Path(__file__).resolve().parent / "out"
DELINEATION = 2020
BASE_YEAR = 2022
LOSS_WINDOW = 20

STATUS = "DESCRIPTIVE -- NOT A GRADED FORECAST"

PREREG = {
    "commit": "6ca77bbf0bcb13bbbf49a9301a3e364379bfb384",
    "commit_utc": "2026-08-23T20:45:59Z",
    "release": "v1.5.0-prereg",
    "expected_sign_y_hpi": -1,
    "expected_sign_y_pop": -1,
    "fidelity_r2_floor": 0.25,
}
EXPECTED_SIGN = -1

# Copied from out/E6_PREMIUM_SIGN.md and out/E7_NRI_PROXY.md so the comparison
# is explicit rather than remembered.
E6_TARGET = {
    "y_hpi": {"beta_per_sd": -0.005234, "t": -6.822},
    "y_pop": {"beta_per_sd": 0.000720, "t": 2.122},
}
E7_TARGET = {
    "y_hpi": {"beta_per_sd": -0.00293, "t": -2.80},
    "y_pop": {"beta_per_sd": 0.00065, "t": 2.05},
    "flood_share_was_significant": False,
    "wind_share": {"beta_per_sd": -0.00366, "t": -2.66},
}

FEATURES = ["nfip_rate_per_1k_log", "nfip_loss_pc_log"]
SOUTH = {5, 6, 7}


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
    """Metro panel: outcomes, momentum, FIO premium, NRI rate, NFIP series."""
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

    base = BASE_YEAR
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
    d = d.join(eal[["eal_rate_log", "flood_share", "wind_share"]], how="left")

    # NFIP price: premium per $1,000 of building coverage, 2022 cross-section.
    pr = nfip_src.metro_premium(BASE_YEAR, delineation_vintage=DELINEATION).set_index("cbsa_code")
    pr["nfip_rate_per_1k_log"] = np.log(pr["nfip_rate_per_1k"].where(pr["nfip_rate_per_1k"] > 0))
    d = d.join(
        pr[["nfip_rate_per_1k", "nfip_rate_per_1k_log", "nfip_premium",
            "nfip_n_policies"]],
        how="left",
    )

    # NFIP realised loss: paid claims per resident per year, 20-year window.
    lo = nfip_src.metro_loss_history(BASE_YEAR, window=LOSS_WINDOW,
                                     delineation_vintage=DELINEATION).set_index("cbsa_code")
    d = d.join(
        lo[["nfip_loss_pc_yr", "nfip_loss_pc_log", "nfip_claims_per_10k_yr",
            "nfip_severity_ratio", "nfip_n_claims", "nfip_claim_years"]],
        how="left",
    )

    div = cty.groupby("cbsa_code")["division"].agg(lambda s: s.mode().iat[0])
    d = d.join(div.rename("division"), how="inner")

    d.attrs.update(pop_h=pop_h, hpi_h=hpi_h, base=base,
                   pop_last=pop_last, hpi_last=hpi_last)
    return d.reset_index()


# --- E8a: do the NFIP series track the homeowners premium? -----------------

def fidelity(d: pd.DataFrame, feature: str) -> dict:
    cols = ["premium_log_2022", feature]
    s = d.dropna(subset=cols + ["division"]).copy()
    n = len(s)
    if n < 30:
        return {"n_metros": n, "insufficient": True}

    X = np.column_stack([np.ones(n), s[feature].to_numpy()])
    y = s["premium_log_2022"].to_numpy()
    b, se = _ols_hc1(X, y)
    r2 = 1 - (y - X @ b).var() / y.var()

    w = _demean(s, cols)
    Xw = np.column_stack([np.ones(len(w)), w[feature].to_numpy()])
    yw = w["premium_log_2022"].to_numpy()
    bw, sew = _ols_hc1(Xw, yw)
    r2w = 1 - (yw - Xw @ bw).var() / yw.var() if yw.var() > 0 else float("nan")

    return {
        "feature": feature,
        "n_metros": n,
        "pooled": {
            "pearson": round(float(np.corrcoef(s[feature], y)[0, 1]), 4),
            "spearman": round(float(s[feature].corr(s["premium_log_2022"],
                                                    method="spearman")), 4),
            "r2": round(float(r2), 4),
            "elasticity": round(float(b[1]), 4),
            "se": round(float(se[1]), 4),
            "t": round(float(b[1] / se[1]), 3),
        },
        "within_division": {
            "pearson": round(float(np.corrcoef(w[feature], yw)[0, 1]), 4),
            "r2": round(float(r2w), 4),
            "elasticity": round(float(bw[1]), 4),
            "se": round(float(sew[1]), 4),
            "t": round(float(bw[1] / sew[1]), 3),
        },
        "clears_prereg_r2_floor": bool(r2 >= PREREG["fidelity_r2_floor"]),
    }


# --- E8b / E8c: outcome coefficients ---------------------------------------

def _fit(frame: pd.DataFrame, cols: list[str], target: str, label: str,
         expected_map: dict[str, int | None]) -> list[dict]:
    f = frame.dropna(subset=cols + [target, "division"]).copy()
    if len(f) < 30:
        return []
    w = _demean(f, cols + [target])
    n = len(w)
    Z = np.column_stack([w[c].to_numpy() for c in cols])
    sd = Z.std(axis=0, ddof=1)
    sd[sd == 0] = 1.0
    X = np.column_stack([np.ones(n), Z / sd])
    b, se = _ols_hc1(X, w[target].to_numpy())
    rows = []
    for i, c in enumerate(cols, start=1):
        r = _entry(c, b[i], se[i], n, X.shape[1], expected=expected_map.get(c, None))
        r["spec"] = label
        rows.append(r)
    return rows


def regress(d: pd.DataFrame, target: str) -> dict:
    momentum = "pop_g3" if target == "y_pop" else "hpi_g5"
    res: dict = {
        "target": target,
        "momentum_control": momentum,
        "e6_reference": E6_TARGET[target],
        "e7_reference": E7_TARGET[target],
        "substituted": {},
        "vs_premium": {},
    }

    for feat in FEATURES:
        s = d.dropna(subset=[target, feat, momentum, "division"])
        res["substituted"][feat] = {
            "n_metros": int(len(s)),
            "rows": _fit(s, [feat, momentum], target, f"{feat} + momentum",
                         {feat: EXPECTED_SIGN}),
        }
        both = s.dropna(subset=["premium_log_2022"])
        res["vs_premium"][feat] = {
            "n_metros": int(len(both)),
            "rows": _fit(both, [feat, "premium_log_2022", momentum], target,
                         f"{feat} + FIO premium + momentum",
                         {feat: EXPECTED_SIGN, "premium_log_2022": EXPECTED_SIGN}),
        }

    # Price against loss, same peril. If both survive, neither is doing what it
    # claims -- a price is supposed to be the market's summary of the loss.
    pl = d.dropna(subset=[target, momentum, "division"] + FEATURES)
    res["price_vs_loss"] = {
        "n_metros": int(len(pl)),
        "rows": _fit(pl, FEATURES + [momentum], target,
                     "NFIP price + NFIP loss + momentum",
                     {f: EXPECTED_SIGN for f in FEATURES}),
    }

    # Flood price and loss against the all-hazard NRI rate: the E8d contest.
    fl = d.dropna(subset=[target, momentum, "division", "eal_rate_log"] + FEATURES)
    res["vs_nri"] = {
        "n_metros": int(len(fl)),
        "rows": _fit(fl, FEATURES + ["eal_rate_log", momentum], target,
                     "NFIP flood + NRI all-hazard + momentum",
                     {**{f: EXPECTED_SIGN for f in FEATURES},
                      "eal_rate_log": EXPECTED_SIGN}),
    }

    # Regional conditionality, the objection E6 answered for the premium.
    res["ex_south"] = {}
    for feat in FEATURES:
        ex = d[~d["division"].isin(SOUTH)]
        res["ex_south"][feat] = {
            "rows": _fit(ex, [feat, momentum], target, f"ex-South, {feat}",
                         {feat: EXPECTED_SIGN}),
        }

    # Quartile contrast on the loss burden, no controls, for a readable number.
    q = d.dropna(subset=[target, "nfip_loss_pc_yr"]).copy()
    if len(q) >= 40:
        lo_q, hi_q = q["nfip_loss_pc_yr"].quantile([0.25, 0.75])
        top = q[q["nfip_loss_pc_yr"] >= hi_q][target]
        bot = q[q["nfip_loss_pc_yr"] <= lo_q][target]
        res["quartile_contrast_loss"] = {
            "top_quartile_growth_pct": round(100.0 * float(top.mean()), 3),
            "bottom_quartile_growth_pct": round(100.0 * float(bot.mean()), 3),
            "gap_pp": round(100.0 * float(top.mean() - bot.mean()), 3),
            "n_top": int(len(top)),
            "n_bottom": int(len(bot)),
            "matches_expected": bool(top.mean() < bot.mean()),
        }
    return res


# --- E8e: robustness ladder ------------------------------------------------

CATASTROPHE_METROS = {
    "35380": "New Orleans-Metairie, LA",
    "25060": "Gulfport-Biloxi, MS",
    "13140": "Beaumont-Port Arthur, TX",
    "15980": "Cape Coral-Fort Myers, FL",
    "36140": "Ocean City, NJ",
    "35100": "New Bern, NC",
    "12940": "Baton Rouge, LA",
    "34940": "Naples-Marco Island, FL",
    "29340": "Lake Charles, LA",
    "19300": "Daphne-Fairhope-Foley, AL",
    "37860": "Pensacola-Ferry Pass-Brent, FL",
    "12100": "Atlantic City-Hammonton, NJ",
}


def robustness(d: pd.DataFrame) -> dict:
    """Is each headline result a handful of catastrophe metros?

    The concern is specific. Paid flood losses per capita are concentrated in a
    coastal tail, and the twenty-year window ending 2022 contains Katrina,
    Sandy and Harvey. If the price coefficient is those three storms, it is a
    story about three events rather than a feature.
    """
    out: dict = {}

    def one(frame: pd.DataFrame, feat: str, target: str, label: str) -> dict:
        mom = "pop_g3" if target == "y_pop" else "hpi_g5"
        rows = _fit(frame, [feat, mom], target, label, {feat: EXPECTED_SIGN})
        r = next((x for x in rows if x["predictor"] == feat), None)
        if not r:
            return {"cut": label, "insufficient": True}
        return {"cut": label, "beta_per_sd": r["beta_per_sd"], "t": r["t"],
                "n": r["n"], "sign_ok": r["matches_expected"],
                "significant": bool(abs(r["t"]) >= 2)}

    f, t = "nfip_loss_pc_log", "y_hpi"
    ladder = [one(d, f, t, "baseline, 20-year window")]
    for q in (0.95, 0.90):
        cut = d[f].quantile(q)
        ladder.append(one(d[d[f] < cut], f, t,
                          f"drop top {round((1 - q) * 100)}% of loss burden"))
    ladder.append(one(d[~d["cbsa_code"].astype(str).isin(CATASTROPHE_METROS)], f, t,
                      "drop the 12 highest-loss metros by name"))
    for w in (10, 30):
        lo = nfip_src.metro_loss_history(BASE_YEAR, window=w,
                                         delineation_vintage=DELINEATION)
        alt = d.drop(columns=[f]).merge(
            lo[["cbsa_code", "nfip_loss_pc_log"]], on="cbsa_code", how="left")
        ladder.append(one(alt, f, t, f"{w}-year loss window"))
    ladder.append(one(d, "nfip_claims_per_10k_yr", t,
                      "claim frequency per 10k residents, not dollars"))
    out["loss_burden_on_y_hpi"] = ladder

    f, t = "nfip_rate_per_1k_log", "y_pop"
    ladder = [one(d, f, t, "baseline")]
    for q in (0.95, 0.90):
        cut = d[f].quantile(q)
        ladder.append(one(d[d[f] < cut], f, t,
                          f"drop top {round((1 - q) * 100)}% of flood price"))
    for mn in (200, 500):
        ladder.append(one(d[d["nfip_n_policies"] >= mn], f, t,
                          f"metros with at least {mn} sampled policies"))
    out["flood_price_on_y_pop"] = ladder
    out["catastrophe_metros_dropped"] = CATASTROPHE_METROS
    return out


def _sub_row(res: dict, feat: str) -> dict | None:
    rows = res["substituted"].get(feat, {}).get("rows", [])
    return next((r for r in rows if r["predictor"] == feat), None)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    d = build()

    fid = {f: fidelity(d, f) for f in FEATURES}
    targets = {t: regress(d, t) for t in ("y_hpi", "y_pop")}
    robust = robustness(d)

    # --- E8d: the pre-registered falsification test ------------------------
    e7_hpi = abs(E7_TARGET["y_hpi"]["beta_per_sd"])
    e8d: dict = {
        "prediction": (
            "E7 attributed the entire price signal to the wind share and found "
            "the flood share insignificant. Flood-only measures must therefore "
            "be WEAKER on house prices than E7's all-hazard NRI coefficient."
        ),
        "e7_nri_all_hazard_abs_beta": round(e7_hpi, 6),
        "per_feature": {},
    }
    for feat in FEATURES:
        r = _sub_row(targets["y_hpi"], feat)
        if not r:
            e8d["per_feature"][feat] = {"measurable": False}
            continue
        e8d["per_feature"][feat] = {
            "measurable": True,
            "abs_beta": abs(r["beta_per_sd"]),
            "t": r["t"],
            "significant": bool(abs(r["t"]) >= 2),
            "weaker_than_multi_peril": bool(abs(r["beta_per_sd"]) < e7_hpi),
        }
    measured = [v for v in e8d["per_feature"].values() if v.get("measurable")]
    sig = [v for v in measured if v["significant"]]
    e8d["any_flood_feature_significant_on_prices"] = bool(sig)
    e8d["all_significant_are_weaker_than_multi_peril"] = bool(
        sig and all(v["weaker_than_multi_peril"] for v in sig)
    )
    e8d["prediction_upheld"] = bool(
        (not sig) or all(v["weaker_than_multi_peril"] for v in sig)
    )
    e8d["e7_hazard_decomposition_falsified"] = bool(
        sig and any(not v["weaker_than_multi_peril"] for v in sig)
    )

    # The falsification must itself be stress-tested. If trimming the coastal
    # loss tail pushes the flood coefficient back below E7's all-hazard beta,
    # then E7 is not refuted outright -- it is refuted only on the untrimmed
    # cross-section, and this file must say so rather than claiming the scalp.
    trimmed = [
        r for r in robust["loss_burden_on_y_hpi"]
        if not r.get("insufficient") and r["cut"].startswith("drop")
    ]
    still = [r for r in trimmed
             if abs(r["beta_per_sd"]) >= e7_hpi and r["significant"]]
    e8d["falsification_survives_trimming"] = bool(
        trimmed and len(still) == len(trimmed)
    )
    e8d["trimmed_specifications"] = [
        {"cut": r["cut"], "abs_beta": abs(r["beta_per_sd"]), "t": r["t"],
         "exceeds_e7": bool(abs(r["beta_per_sd"]) >= e7_hpi)}
        for r in trimmed
    ]
    if e8d["e7_hazard_decomposition_falsified"] and not e8d["falsification_survives_trimming"]:
        e8d["verdict"] = (
            "CONDITIONAL. E7's hazard decomposition is falsified on the full "
            "cross-section, but the falsification does not survive trimming the "
            "top loss decile, so E7 is not refuted outright."
        )
    elif e8d["e7_hazard_decomposition_falsified"]:
        e8d["verdict"] = (
            "FALSIFIED. E7's hazard decomposition fails, and the falsification "
            "survives every trim tested."
        )
    else:
        e8d["verdict"] = (
            "UPHELD. Flood-only measures are weaker than multi-peril on prices."
        )

    verdict = {}
    for feat in FEATURES:
        r = _sub_row(targets["y_hpi"], feat)
        hr = targets["y_hpi"]["vs_premium"].get(feat, {}).get("rows", [])
        own = next((x for x in hr if x["predictor"] == feat), None)
        verdict[feat] = {
            "tracks_actual_homeowners_premium": bool(
                fid[feat].get("clears_prereg_r2_floor")
                and fid[feat].get("pooled", {}).get("elasticity", 0) > 0
            ),
            "reproduces_e6_price_sign": bool(
                r and r["matches_expected"] and abs(r["t"]) >= 2
            ),
            "magnitude_vs_e6_ratio": (
                round(r["beta_per_sd"] / E6_TARGET["y_hpi"]["beta_per_sd"], 3)
                if r else None
            ),
            "survives_premium_control": bool(own and abs(own["t"]) >= 2),
            "vintage_class": "B" if feat == "nfip_loss_pc_log" else "B",
            "eligible_as_graded_predictor": False,
        }

    payload = {
        "diagnostic": "E8",
        "title": "NFIP flood price and realised loss as insurance signals",
        "status": STATUS,
        "pre_registration": PREREG,
        "why_not_yet_graded": (
            "Both NFIP files are Class B under PROTOCOL Amendment 1: dated, "
            "never-restated transactions published later than the origins they "
            "would serve. Class B is gradeable with a declared availability "
            "deviation, but the OpenFEMA API serves only the current file with "
            "no archived vintages, so an as-of-origin snapshot cannot be "
            "demonstrated for this run. Both series were first published "
            "2019-06-01, so the earliest legal origin is 2020: one of eleven "
            "h=5 origins and three of thirteen h=3 origins. This run is a "
            "measurement exercise about two features, not a prediction."
        ),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "delineation_vintage": DELINEATION,
        "nfip": {
            "claims_endpoint": nfip_src.CLAIMS,
            "policies_endpoint": nfip_src.POLICIES,
            "claims_records": 2_724_656,
            "policies_records": 74_349_525,
            "policies_temporal_start": "2009-01-01",
            "claims_earliest_observed_loss_year": 1978,
            "loss_window_years": LOSS_WINDOW,
            "premium_cross_section_year": BASE_YEAR,
        },
        "outcome_windows": {
            "base_year": d.attrs.get("base"),
            "y_pop_horizon_years": d.attrs.get("pop_h"),
            "y_hpi_horizon_years": d.attrs.get("hpi_h"),
        },
        "coverage": {
            "metros_with_nfip_price": int(d["nfip_rate_per_1k_log"].notna().sum()),
            "metros_with_nfip_loss": int(d["nfip_loss_pc_log"].notna().sum()),
            "metros_with_fio_premium": int(d["premium_log_2022"].notna().sum()),
            "metros_in_panel": int(len(d)),
        },
        "e6_reference": E6_TARGET,
        "e7_reference": E7_TARGET,
        "e8a_fidelity": fid,
        "e8b_e8c_outcomes": targets,
        "e8d_preregistered_falsification_test": e8d,
        "e8e_robustness": robust,
        "verdict": verdict,
        "deviations": nfip_src.DEVIATIONS,
        "vintage_verdict": nfip_src.VINTAGE_VERDICT,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"nfip_calibration_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    print(json.dumps(payload, indent=2, default=str))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
