"""Rolling-origin evaluation engine implementing GRIP-1 criteria E1-E5."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import RidgeCV

RNG = np.random.default_rng(20260823)


def _prep(df: pd.DataFrame, feats: list[str], target: str) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    sub = df.dropna(subset=feats + [target]).copy()
    X = sub[feats].to_numpy(float)
    y = sub[target].to_numpy(float)
    return X, y, sub


def _standardise(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu, sd = train.mean(0), train.std(0)
    sd = np.where(sd == 0, 1.0, sd)
    return (train - mu) / sd, (test - mu) / sd


def _oos_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(((y_true - y_pred) ** 2).sum())
    ss_tot = float(((y_true - y_true.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan


def _hit_rate(score: np.ndarray, y: np.ndarray) -> float:
    """Share of top-quartile-scored metros that beat their region's mean.

    With within-region demeaning the regional mean is 0, so `y > 0` is the test.
    Matches the definition behind the previously validated 74% result.
    """
    if len(score) < 8:
        return np.nan
    cut = np.quantile(score, 0.75)
    sel = score >= cut
    return float((y[sel] > 0).mean()) if sel.sum() else np.nan


MIN_MEMBERS = 5  # PROTOCOL.md section 9: AIMIP's floor, adopted verbatim.


def _block_bootstrap_ensemble(
    tr: pd.DataFrame,
    te_X: np.ndarray,
    feats: list[str],
    target: str,
    n_members: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit `n_members` ridge models on origin-year blocks drawn with replacement.

    The resampling unit is the whole origin year, not the individual metro. Metros
    within one origin share a national cycle and a single delineation vintage, so
    resampling metros would treat correlated rows as independent and understate
    the spread. Blocks over origins is the analogue of AIMIP's initial-condition
    members: each member is a model that could legitimately have been fitted from
    the same history.

    Returns (predictions [n_members, n_test], coefficients [n_members, n_feats]).
    """
    train_origins = np.array(sorted(tr["origin_year"].unique()))
    preds, coefs = [], []
    for _ in range(n_members):
        draw = rng.choice(train_origins, size=len(train_origins), replace=True)
        sub = pd.concat([tr[tr["origin_year"] == o] for o in draw], ignore_index=True)
        Xm, ym, _ = _prep(sub, feats, target)
        if len(ym) < 40 or np.unique(ym).size < 10:
            continue
        Xm_s, Xte_s = _standardise(Xm, te_X)
        m = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(Xm_s, ym)
        preds.append(m.predict(Xte_s))
        coefs.append(m.coef_)
    if not preds:
        return np.empty((0, len(te_X))), np.empty((0, len(feats)))
    return np.vstack(preds), np.vstack(coefs)


def expanding_origin_eval(
    panel: pd.DataFrame,
    feats: list[str],
    target: str,
    baseline: str,
    min_train_origins: int = 3,
    n_boot: int = 400,
    n_members: int = 20,
    seed: int = 20260823,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Strictly causal evaluation: train on origins < Y, test on origin Y.

    This is the GRIP analogue of AIMIP's held-out 2015-2024 decade, except it is
    repeated at every origin so the result is a skill *curve* rather than a
    single number. Two origin years cannot distinguish skill from luck.

    Every origin is scored from a block-bootstrap ensemble of at least
    `MIN_MEMBERS` members, per PROTOCOL.md section 9. The graded prediction is the
    ensemble mean; the spread across members is reported beside it. The
    single-fit result is retained as `single_fit_spearman` purely so that the
    effect of ensembling on the verdict is visible rather than silently absorbed.

    Returns (results, predictions) where `predictions` is the protocol submission
    format: origin_year, cbsa_code, member, y_pred.
    """
    if n_members < MIN_MEMBERS:
        raise ValueError(f"n_members={n_members} violates the protocol floor of {MIN_MEMBERS}")

    rng = np.random.default_rng(seed)
    origins = sorted(panel["origin_year"].unique())
    rows, pred_rows = [], []
    # Out-of-sample residuals from origins already scored. Used to widen the
    # member spread into an honest predictive interval. Only residuals from
    # strictly earlier origins are ever consulted, so this stays causal.
    past_residuals: list[np.ndarray] = []
    for i, test_origin in enumerate(origins):
        train_origins = origins[:i]
        if len(train_origins) < min_train_origins:
            continue
        tr = panel[panel["origin_year"].isin(train_origins)]
        te = panel[panel["origin_year"] == test_origin]

        Xtr, ytr, _ = _prep(tr, feats, target)
        Xte, yte, te_sub = _prep(te, feats, target)
        if len(ytr) < 60 or len(yte) < 25:
            continue

        # Single fit, retained only as a reference point for the ensemble.
        Xtr_s, Xte_s = _standardise(Xtr, Xte)
        single = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(Xtr_s, ytr)
        single_pred = single.predict(Xte_s)

        members, mcoefs = _block_bootstrap_ensemble(
            tr, Xte, feats, target, n_members, rng
        )
        if members.shape[0] < MIN_MEMBERS:
            print(f"[skip] origin {test_origin}: only {members.shape[0]} viable members")
            continue
        pred = members.mean(0)

        # Baseline gets the identical ensemble treatment so the comparison stays
        # even-handed: a bootstrapped model against an un-bootstrapped reference
        # would be crediting the model for the averaging alone.
        bte, by, _ = _prep(te, [baseline], target)
        bmembers, _ = _block_bootstrap_ensemble(
            tr, bte, [baseline], target, n_members, rng
        )
        if bmembers.shape[0] < MIN_MEMBERS:
            print(f"[skip] origin {test_origin}: baseline ensemble too small")
            continue
        bpred = bmembers.mean(0)

        rho_m = stats.spearmanr(pred, yte).statistic
        rho_b = stats.spearmanr(bpred, by).statistic

        # Per-member skill. This is the diagnostic that matters for the verdict:
        # if only a small minority of members beats the baseline, NOT CERTIFIED
        # is robust to which member happened to be shipped.
        member_rhos = np.array([stats.spearmanr(m, yte).statistic for m in members])
        members_beating = int((member_rhos > rho_b).sum())

        # Spread across members, per metro. This is parameter uncertainty only --
        # it does not include irreducible outcome noise, so it is necessarily
        # smaller than the forecast error and is NOT a calibrated predictive
        # interval. Reported under a name that says so.
        spread = members.std(0, ddof=1)
        rmse = float(np.sqrt(((yte - pred) ** 2).mean()))
        ratio = float(spread.mean() / rmse) if rmse > 0 else np.nan

        # Predictive interval. Member spread alone captures only which model you
        # might have fitted, not how wrong that model is about a given metro, and
        # at this horizon it is roughly a tenth of the actual error. Publishing it
        # as an interval would be worse than publishing none. So widen it with the
        # empirical residual distribution from previously scored origins and then
        # report the realised coverage, which is the only number that settles
        # whether the interval means anything.
        if past_residuals:
            pool = np.concatenate(past_residuals)
            q_lo, q_hi = np.percentile(pool, [5, 95])
            pi_lo, pi_hi = pred + q_lo, pred + q_hi
            coverage = float(((yte >= pi_lo) & (yte <= pi_hi)).mean())
            pi_width = float((pi_hi - pi_lo).mean())
        else:
            coverage, pi_width = np.nan, np.nan
        past_residuals.append(yte - pred)

        # Sampling interval on the *statistic*, by resampling metros. Distinct
        # from member spread above; conflating the two is the usual error.
        boot = []
        n = len(yte)
        for _ in range(n_boot):
            idx = rng.integers(0, n, n)
            if len(np.unique(yte[idx])) < 3:
                continue
            boot.append(stats.spearmanr(pred[idx], yte[idx]).statistic)
        lo, hi = (np.nanpercentile(boot, [5, 95]) if boot else (np.nan, np.nan))

        codes = te_sub["cbsa_code"].to_numpy()
        for mi in range(members.shape[0]):
            for ci, code in enumerate(codes):
                pred_rows.append(
                    {
                        "origin_year": int(test_origin),
                        "cbsa_code": code,
                        "member": mi,
                        "y_pred": round(float(members[mi, ci]), 6),
                    }
                )

        rows.append(
            {
                "test_origin": int(test_origin),
                "n_train_origins": len(train_origins),
                "n_test_metros": int(n),
                "n_members": int(members.shape[0]),
                "model_spearman": round(float(rho_m), 4),
                "model_spearman_p05": round(float(lo), 4),
                "model_spearman_p95": round(float(hi), 4),
                "member_spearman_min": round(float(np.nanmin(member_rhos)), 4),
                "member_spearman_max": round(float(np.nanmax(member_rhos)), 4),
                "members_beating_baseline": f"{members_beating}/{members.shape[0]}",
                "mean_member_spread": round(float(spread.mean()), 6),
                "ensemble_rmse": round(rmse, 6),
                "parameter_spread_to_error_ratio": round(ratio, 4),
                "predictive_interval_width_90": (
                    round(pi_width, 6) if np.isfinite(pi_width) else None
                ),
                "predictive_interval_coverage_90": (
                    round(coverage, 4) if np.isfinite(coverage) else None
                ),
                "single_fit_spearman": round(float(stats.spearmanr(single_pred, yte).statistic), 4),
                "baseline_spearman": round(float(rho_b), 4),
                "model_oos_r2": round(_oos_r2(yte, pred), 4),
                "baseline_oos_r2": round(_oos_r2(by, bpred), 4),
                "model_hit_rate": round(_hit_rate(pred, yte), 4),
                "baseline_hit_rate": round(_hit_rate(bpred, by), 4),
                "beats_baseline": bool(rho_m > rho_b),
                "coefficients": {
                    f: round(float(c), 4) for f, c in zip(feats, mcoefs.mean(0))
                },
                "coefficient_member_sd": {
                    f: round(float(s), 4) for f, s in zip(feats, mcoefs.std(0, ddof=1))
                },
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(pred_rows)


def coefficient_stability(results: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """E4: does each weight keep its sign across origins/regimes?

    A coefficient that flips sign across regimes is the same pathology as
    `appreciationYoY` inverting across the 2009/2010 crash. Unstable weights may
    not be published as if they were structural.
    """
    if results.empty:
        return pd.DataFrame()
    coefs = pd.DataFrame(list(results["coefficients"]), index=results["test_origin"])
    rows = []
    for f in feats:
        if f not in coefs:
            continue
        v = coefs[f].dropna()
        if v.empty:
            continue
        share_pos = float((v > 0).mean())
        rows.append(
            {
                "feature": f,
                "mean_coef": round(float(v.mean()), 4),
                "min_coef": round(float(v.min()), 4),
                "max_coef": round(float(v.max()), 4),
                "share_positive": round(share_pos, 3),
                "sign_stable": bool(share_pos in (0.0, 1.0)),
                "verdict": "STABLE" if share_pos in (0.0, 1.0) else "SIGN-UNSTABLE",
            }
        )
    return pd.DataFrame(rows)


def descriptive_skill(panel: pd.DataFrame, feats: list[str], target: str) -> dict:
    """E1: contemporaneous descriptive association, pooled across origins.

    Reported separately from predictive skill precisely because AIMIP found that
    every architecture does well on time-mean climate and diverges on trends.
    Describing a state and predicting its derivative are different problems.
    """
    X, y, _ = _prep(panel, feats, target)
    if len(y) < 50:
        return {}
    Xs = (X - X.mean(0)) / np.where(X.std(0) == 0, 1, X.std(0))
    m = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(Xs, y)
    pred = m.predict(Xs)
    return {
        "n": int(len(y)),
        "in_sample_r2": round(float(m.score(Xs, y)), 4),
        "spearman": round(float(stats.spearmanr(pred, y).statistic), 4),
    }
