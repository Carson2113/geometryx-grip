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


def expanding_origin_eval(
    panel: pd.DataFrame,
    feats: list[str],
    target: str,
    baseline: str,
    min_train_origins: int = 3,
    n_boot: int = 400,
) -> pd.DataFrame:
    """Strictly causal evaluation: train on origins < Y, test on origin Y.

    This is the GRIP analogue of AIMIP's held-out 2015-2024 decade, except it is
    repeated at every origin so the result is a skill *curve* rather than a
    single number. Two origin years cannot distinguish skill from luck.
    """
    origins = sorted(panel["origin_year"].unique())
    rows = []
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

        Xtr_s, Xte_s = _standardise(Xtr, Xte)
        model = RidgeCV(alphas=np.logspace(-3, 3, 25))
        model.fit(Xtr_s, ytr)
        pred = model.predict(Xte_s)

        # Baseline: the single strongest naive predictor, fitted identically.
        # AIMIP always reports against a reference model (GFDL-CM4); GRIP always
        # reports against prior population growth, which beat the shipped
        # Geometryx composite in 8 of 8 cells.
        btr, bytr, _ = _prep(tr, [baseline], target)
        bte, by, _ = _prep(te, [baseline], target)
        btr_s, bte_s = _standardise(btr, bte)
        bmodel = RidgeCV(alphas=np.logspace(-3, 3, 25)).fit(btr_s, bytr)
        bpred = bmodel.predict(bte_s)

        rho_m = stats.spearmanr(pred, yte).statistic
        rho_b = stats.spearmanr(bpred, by).statistic

        # Ensemble spread: bootstrap over metros within the test origin.
        boot = []
        n = len(yte)
        for _ in range(n_boot):
            idx = RNG.integers(0, n, n)
            if len(np.unique(yte[idx])) < 3:
                continue
            boot.append(stats.spearmanr(pred[idx], yte[idx]).statistic)
        lo, hi = (np.nanpercentile(boot, [5, 95]) if boot else (np.nan, np.nan))

        rows.append(
            {
                "test_origin": int(test_origin),
                "n_train_origins": len(train_origins),
                "n_test_metros": int(n),
                "model_spearman": round(float(rho_m), 4),
                "model_spearman_p05": round(float(lo), 4),
                "model_spearman_p95": round(float(hi), 4),
                "baseline_spearman": round(float(rho_b), 4),
                "model_oos_r2": round(_oos_r2(yte, pred), 4),
                "baseline_oos_r2": round(_oos_r2(by, bpred), 4),
                "model_hit_rate": round(_hit_rate(pred, yte), 4),
                "baseline_hit_rate": round(_hit_rate(bpred, by), 4),
                "beats_baseline": bool(rho_m > rho_b),
                "coefficients": {
                    f: round(float(c), 4) for f, c in zip(feats, model.coef_)
                },
            }
        )
    return pd.DataFrame(rows)


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
