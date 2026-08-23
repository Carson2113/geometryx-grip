"""E5: shock plausibility.

AIMIP cannot validate a +4 K world against observations, so it grades models on
whether the SIGN and STRUCTURE of the response are physically plausible, using a
reference physics model for the expected pattern. Three AIMIP entrants -- ACE2.1,
cBottle1.3 and MD-1.5 v0.9 -- failed by "implausibly predicting cooling over
land" even though their historical means looked fine.

Geometryx has the identical class of failure already on record: the high
climate-risk quartile grew FASTER than the low-risk quartile (+1.10% vs +0.78%)
and the worst insurance-nonrenewal decile grew fastest (+1.57% vs +0.51%). Under
GRIP those become published diagnostics with pre-registered expected signs, not
private embarrassments.

Rule: expected signs are declared BEFORE the shock is run. A model that returns
the wrong sign is barred from forward-looking claims regardless of its R².
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Shock:
    name: str
    description: str
    # Feature -> additive perturbation applied to the standardised feature.
    perturbation: dict[str, float]
    # Metro subset the shock is expected to hurt, as a predicate on the panel.
    exposed: str
    expected_sign: int  # -1 = exposed metros should fall relative to peers
    rationale: str
    failure_signature: str
    # "exposed_only": the perturbation lands only on exposed metros, which is how
    #   a real hazard or affordability shock is distributed. Graded on the SIGN of
    #   the relative response, i.e. on the fitted coefficient's sign.
    # "uniform": the perturbation lands on every metro. A linear model cannot
    #   produce a differential response to a uniform shock, so this variant is
    #   graded on rank stability (compression, not reordering) instead of sign.
    scope: str = "exposed_only"
    notes: str = ""
    tags: list[str] = field(default_factory=list)


SUITE: list[Shock] = [
    Shock(
        name="rate_shock_200bp",
        description="Mortgage rates +200 bp; proxied by a uniform valuation-gap increase.",
        perturbation={"hpi_gap_wr": +1.0},
        exposed="hpi_gap_wr > hpi_gap_wr.quantile(0.75)",
        expected_sign=-1,
        rationale="Metros already priced furthest above their own long-run trend are the most affordability-constrained and should decline relative to peers.",
        failure_signature="A uniform or positive response means the model carries no rate sensitivity at all.",
    ),
    Shock(
        name="premium_shock_40pct",
        description="Homeowners premium +40% concentrated in high-hazard metros.",
        perturbation={"hpi_vol_wr": +1.0},
        exposed="hpi_vol_wr > hpi_vol_wr.quantile(0.75)",
        expected_sign=-1,
        rationale="Insurance cost is a housing-cost shock; exposed metros should lose relative attractiveness.",
        failure_signature="Wrong sign means the climate/insurance pillar is acting as a proxy for Sun Belt growth rather than for risk -- the exact inversion already measured (+1.57% vs +0.51%).",
        notes="Replace hpi_vol_wr with the Treasury FIO premium-level feature once the FIO adapter lands; hpi_vol is a stand-in.",
        tags=["climate", "insurance"],
    ),
    Shock(
        name="momentum_reversal",
        description="Prior growth momentum halved everywhere.",
        perturbation={"pop_g3_wr": -1.0},
        exposed="pop_g3_wr > pop_g3_wr.quantile(0.75)",
        expected_sign=-1,
        rationale="If momentum is the dominant real signal, removing it must compress the ranking.",
        failure_signature="Wholesale reordering rather than compression indicates a scale artifact.",
        scope="uniform",
    ),
]


def run_shock(model, panel: pd.DataFrame, feats: list[str], shock: Shock) -> dict:
    """Apply a shock to standardised features and measure the ranking response."""
    active = [f for f in shock.perturbation if f in feats]
    if not active:
        return {
            "shock": shock.name,
            "status": "NOT_APPLICABLE",
            "reason": (
                "perturbed feature(s) "
                f"{sorted(shock.perturbation)} are not in the fitted model "
                "(excluded by the CLOCK_LEAK audit or unavailable)"
            ),
            "description": shock.description,
        }
    sub = panel.dropna(subset=feats).copy()
    if len(sub) < 40:
        return {"shock": shock.name, "status": "INSUFFICIENT_DATA"}

    X = sub[feats].to_numpy(float)
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd == 0, 1.0, sd)
    Xs = (X - mu) / sd

    base_pred = model.predict(Xs)

    try:
        exposed = sub.eval(shock.exposed).to_numpy(bool)
    except Exception:  # noqa: BLE001
        return {"shock": shock.name, "status": "PREDICATE_ERROR"}
    if exposed.sum() < 5 or (~exposed).sum() < 5:
        return {"shock": shock.name, "status": "INSUFFICIENT_EXPOSURE"}

    Xp = Xs.copy()
    rows = slice(None) if shock.scope == "uniform" else exposed
    for f, d in shock.perturbation.items():
        if f in feats:
            Xp[rows, feats.index(f)] += d
    shocked_pred = model.predict(Xp)

    delta = shocked_pred - base_pred
    rel = float(delta[exposed].mean() - delta[~exposed].mean())
    base_rank = pd.Series(base_pred).rank()
    shock_rank = pd.Series(shocked_pred).rank()
    rank_corr = float(base_rank.corr(shock_rank, method="spearman"))

    if shock.scope == "uniform":
        # Graded on rank stability: a uniform cost shock should compress the
        # spread, not reshuffle which metros lead.
        observed_sign = int(np.sign(rel)) if abs(rel) > 1e-9 else 0
        passed = rank_corr > 0.95
    else:
        observed_sign = int(np.sign(rel)) if abs(rel) > 1e-9 else 0
        passed = observed_sign == shock.expected_sign

    return {
        "shock": shock.name,
        "status": "RUN",
        "scope": shock.scope,
        "description": shock.description,
        "n_metros": int(len(sub)),
        "n_exposed": int(exposed.sum()),
        "graded_on": "rank_stability" if shock.scope == "uniform" else "response_sign",
        "relative_response": round(rel, 6),
        "expected_sign": shock.expected_sign,
        "observed_sign": observed_sign,
        "rank_correlation_after_shock": round(rank_corr, 4),
        "verdict": "PLAUSIBLE" if passed else "IMPLAUSIBLE",
        "rationale": shock.rationale,
        "failure_signature": shock.failure_signature,
        "notes": shock.notes,
    }


def run_suite(model, panel: pd.DataFrame, feats: list[str]) -> list[dict]:
    return [run_shock(model, panel, feats, s) for s in SUITE]
