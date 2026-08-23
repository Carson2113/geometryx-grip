"""E9: metro fixed effects as a diagnostic on the E5 shock-sign failure.

Why this exists
---------------
Two of the three pre-registered shocks in E5 return the wrong sign in all four
graded cells. Both failing shocks route through exactly two coefficients --
`hpi_vol_wr` (premium_shock_40pct) and `hpi_gap_wr` (rate_shock_200bp) -- and
both of those are the only SIGN-UNSTABLE entries in E4. E8 then found that the
long-standing positive population coefficient on the Treasury FIO homeowners
premium loses significance once NFIP flood price is in the same regression,
which is consistent with the premium having been a stand-in for persistent warm
-state characteristics rather than a risk price.

That raises one specific, testable question: is the wrong-signed response a
CONFOUND from persistent differences between metros, or a real within-metro
relationship? Metro fixed effects answer exactly that and nothing else.

Three facts constrain the design, and each of them removes an option
-------------------------------------------------------------------
1. For `scope="exposed_only"` shocks, `shocks.run_shock` computes
   `delta[exposed].mean() - delta[~exposed].mean()` from a linear model where
   the perturbation lands only on exposed rows. That difference IS the fitted
   coefficient on the perturbed standardised feature. So "re-running E5" under a
   new specification is precisely "re-estimating those two coefficients". The
   shock suite is executed unmodified here so this is not a claim, it is the
   same code path.

2. Metro fixed effects CANNOT be estimated within a single origin year. Each
   metro contributes exactly one row per origin, so the within-metro
   transformation is identically zero in any one cross-section. E4's
   per-origin coefficient stability therefore has no fixed-effects analogue.
   Leave-one-origin-out is used instead, and it is applied to every
   specification including the baseline so the comparison is like-for-like.
   The published E4 numbers (share_positive 0.429 / 0.857 at h=5) come from
   expanding-window fits and are NOT comparable to the numbers here.

3. A metro fixed effect on the TARGET is not computable at forecast time. To
   demean an outcome by its own metro mean you need that metro's mean outcome,
   which includes the outcome you are trying to forecast. Any specification
   that demeans the target within metro is therefore permanently a diagnostic
   and can never be graded, no matter how good its coefficients look.

Specifications
--------------
S0  registered baseline. Features and target demeaned within
    (origin_year, division). This is what v1.0.0-grip1 graded.

S1  within-metro diagnostic. Features AND target demeaned two-way within
    (origin_year, cbsa_code) by alternating projections, over the whole panel.
    Answers the confound question directly. Not implementable at forecast time
    (see constraint 3) and not gradeable, ever.

S2  candidate specification. Features demeaned by origin_year and then by an
    EXPANDING within-metro mean using only origins <= Y; target left demeaned
    within (origin_year, division) exactly as in S0. Every input is knowable at
    the origin, and the target keeps its cross-sectional meaning, so the ranking
    the product is actually sold on survives. This one could be graded, after a
    fresh pre-registration.

Metro nests inside division, so a metro effect absorbs the division effect and
S1/S2 do not demean by division a second time. The origin_year term is retained
in every specification because dropping it leaves the national cycle in the
residual, and that residual is itself a clock -- the failure that made the first
run of this harness flag every price feature as CLOCK_LEAK.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# A feature whose variance is almost entirely between metros carries almost no
# within-metro information, so the sign of its fixed-effects coefficient is the
# sign of noise. Declared before running: below this share the coefficient is
# reported as UNINFORMATIVE and its sign is not read as evidence either way.
MIN_WITHIN_SHARE = 0.10


def demean_twoway(
    df: pd.DataFrame,
    cols: list[str],
    keys: tuple[str, ...] = ("origin_year", "cbsa_code"),
    suffix: str = "_wr",
    tol: float = 1e-11,
    max_iter: int = 500,
) -> pd.DataFrame:
    """Two-way within transformation by alternating projections.

    The panel is unbalanced -- metros enter and leave as delineations change and
    as HPI coverage starts -- so the closed-form "subtract both means, add back
    the grand mean" identity does not hold. Alternating projections converge to
    the correct within estimator for any unbalanced design.

    Writes `col + suffix` so that the unmodified E5 suite, whose predicates are
    written against `*_wr` names, can be pointed at any specification.
    """
    out = df.copy()
    for c in cols:
        v = out[c].astype(float).to_numpy(copy=True)
        finite = np.isfinite(v)
        if finite.sum() == 0:
            out[c + suffix] = np.nan
            continue
        # Group labels restricted to the finite rows, cached once per key.
        labels = [pd.Series(out.loc[finite, k].to_numpy()) for k in keys]
        w = v[finite]
        for _ in range(max_iter):
            prev = w.copy()
            for lab in labels:
                s = pd.Series(w)
                w = w - s.groupby(lab.to_numpy()).transform("mean").to_numpy()
            if np.max(np.abs(w - prev)) < tol:
                break
        v[finite] = w
        v[~finite] = np.nan
        out[c + suffix] = v
    return out


def demean_expanding_metro(
    df: pd.DataFrame,
    cols: list[str],
    origin_col: str = "origin_year",
    metro_col: str = "cbsa_code",
    suffix: str = "_wr",
    min_prior: int = 3,
) -> pd.DataFrame:
    """Origin demeaning, then an expanding within-metro mean using only origins <= Y.

    This is the forecast-time-legal version of a metro effect. At origin Y the
    forecaster knows this metro's own history of the feature, so subtracting the
    mean over origins <= Y consults nothing that was not already published. The
    current value is included in its own mean, which is what an expanding mean
    means and uses no future data.

    `min_prior` prior origins are required before a value is emitted, because a
    metro's first appearance would otherwise demean to exactly zero and inject a
    block of artificial zeros with no information in them. Rows that cannot meet
    the requirement are NaN and drop out of every downstream fit.
    """
    out = df.sort_values([metro_col, origin_col]).copy()
    for c in cols:
        # Step 1: remove the era. Computable from the origin-Y cross-section.
        centred = out[c].astype(float) - out.groupby(origin_col)[c].transform("mean")
        # Step 2: remove the metro's own expanding mean over origins <= Y.
        g = centred.groupby(out[metro_col])
        exp_mean = g.transform(lambda s: s.expanding(min_periods=1).mean())
        seen = g.transform(lambda s: s.notna().cumsum())
        val = centred - exp_mean
        out[c + suffix] = val.where(seen >= min_prior)
    return out.loc[df.index]


def variance_decomposition(
    df: pd.DataFrame,
    cols: list[str],
    origin_col: str = "origin_year",
    metro_col: str = "cbsa_code",
) -> pd.DataFrame:
    """Share of each feature's variance that survives a metro fixed effect.

    Computed on origin-demeaned values, because the era term is removed in every
    specification and so is not part of what the metro effect is competing with.
    This is the power precondition declared in MIN_WITHIN_SHARE: it is reported
    for every feature before any fixed-effects coefficient is interpreted.
    """
    rows = []
    for c in cols:
        s = df[c].astype(float) - df.groupby(origin_col)[c].transform("mean")
        sub = pd.DataFrame({"v": s, "m": df[metro_col]}).dropna()
        if sub.empty or sub["v"].var(ddof=1) in (0, np.nan):
            continue
        total = float(sub["v"].var(ddof=1))
        between = float(sub.groupby("m")["v"].transform("mean").var(ddof=1))
        within = max(total - between, 0.0)
        rows.append(
            {
                "feature": c,
                "n": int(len(sub)),
                "n_metros": int(sub["m"].nunique()),
                "var_total": round(total, 10),
                "within_metro_share": round(within / total, 4) if total > 0 else np.nan,
                "informative_under_fe": bool(
                    total > 0 and within / total >= MIN_WITHIN_SHARE
                ),
            }
        )
    return pd.DataFrame(rows)


def cluster_ols(
    df: pd.DataFrame, feats: list[str], target: str, cluster: str = "cbsa_code"
) -> pd.DataFrame:
    """OLS with standard errors clustered on metro.

    Ridge is what E5 grades, but a penalised coefficient has no honest standard
    error, so inference is done here instead. Clustering on metro is not
    optional at these horizons: a five-year forward outcome measured at
    consecutive origins overlaps by four years, so residuals within a metro are
    strongly autocorrelated by construction and unclustered t-statistics would
    be inflated several-fold.
    """
    sub = df.dropna(subset=feats + [target, cluster]).copy()
    if len(sub) < 40:
        return pd.DataFrame()
    X = sub[feats].to_numpy(float)
    X = (X - X.mean(0)) / np.where(X.std(0) == 0, 1.0, X.std(0))
    X = np.column_stack([np.ones(len(X)), X])
    y = sub[target].to_numpy(float)
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta

    groups = sub[cluster].to_numpy()
    meat = np.zeros((X.shape[1], X.shape[1]))
    for gval in np.unique(groups):
        m = groups == gval
        xg, ug = X[m], resid[m]
        sg = xg.T @ ug
        meat += np.outer(sg, sg)
    n, k = X.shape
    n_g = len(np.unique(groups))
    if n_g <= 1 or n <= k:
        return pd.DataFrame()
    scale = (n_g / (n_g - 1)) * ((n - 1) / (n - k))
    vcov = xtx_inv @ (scale * meat) @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(vcov), 0.0))

    names = ["const"] + list(feats)
    rows = []
    for i, nm in enumerate(names):
        if nm == "const":
            continue
        t = float(beta[i] / se[i]) if se[i] > 0 else np.nan
        rows.append(
            {
                "feature": nm,
                "coef": round(float(beta[i]), 6),
                "se_clustered": round(float(se[i]), 6),
                "t": round(t, 3),
                "significant_5pct": bool(abs(t) > 1.96) if np.isfinite(t) else False,
                "n": int(n),
                "n_clusters": int(n_g),
            }
        )
    return pd.DataFrame(rows)


def loo_origin_coefficients(
    df: pd.DataFrame, feats: list[str], target: str, origin_col: str = "origin_year"
) -> pd.DataFrame:
    """Ridge coefficients from leave-one-origin-out refits.

    The fixed-effects analogue of E4. A per-origin fit is impossible under a
    metro effect (constraint 2 in the module docstring), so each fit drops one
    origin instead of using only one. Applied identically to every
    specification, including the baseline, so that `share_positive` means the
    same thing in each column.
    """
    from sklearn.linear_model import RidgeCV

    origins = sorted(df[origin_col].dropna().unique())
    rows = []
    for o in origins:
        sub = df[df[origin_col] != o].dropna(subset=feats + [target])
        if len(sub) < 60:
            continue
        X = sub[feats].to_numpy(float)
        X = (X - X.mean(0)) / np.where(X.std(0) == 0, 1.0, X.std(0))
        m = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(X, sub[target].to_numpy(float))
        rows.append({"held_out_origin": int(o), **dict(zip(feats, m.coef_))})
    return pd.DataFrame(rows)


def stability_from_loo(loo: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """Sign agreement across leave-one-origin-out refits.

    Note the asymmetry that matters for grading: `sign_stable` is true whenever a
    coefficient never changes sign, but a coefficient that is stably POSITIVE on
    a shock whose pre-registered sign is negative is stably wrong, not fixed.
    Both columns are reported so that distinction cannot be lost.
    """
    if loo.empty:
        return pd.DataFrame()
    rows = []
    for f in feats:
        if f not in loo:
            continue
        v = loo[f].dropna()
        if v.empty:
            continue
        share_pos = float((v > 0).mean())
        rows.append(
            {
                "feature": f,
                "mean_coef": round(float(v.mean()), 5),
                "min_coef": round(float(v.min()), 5),
                "max_coef": round(float(v.max()), 5),
                "share_positive": round(share_pos, 3),
                "sign_stable": bool(share_pos in (0.0, 1.0)),
                "n_refits": int(len(v)),
            }
        )
    return pd.DataFrame(rows)
