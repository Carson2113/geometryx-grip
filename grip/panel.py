"""Vintage-locked panel construction.

Rule (PROTOCOL.md section 4): for an origin year Y, every predictor must be
derivable from files published on or before Dec 31 of Y. We enforce this by
defining an information base year B = Y - 1 and building all features from data
through B, using the PEP vintage V = Y - 1.

Targets are measured from B forward, using the latest available revision.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .sources import bps as bps_src
from .sources import cbsa as cbsa_src
from .sources import fhfa as fhfa_src
from .sources import pep as pep_src

TREND_WINDOW = 15  # years used to fit the long-run log-price trend


def _log_trend_gap(years: np.ndarray, logh: np.ndarray) -> float:
    """Deviation of the final observation from its own fitted log-linear trend.

    Positive = priced above own long-run trend (mean-reversion headwind).
    Deliberately computed per-metro from that metro's own history, so it carries
    no cross-sectional reference distribution and therefore cannot leak a future
    percentile (see leakage.py).
    """
    if len(years) < 8:
        return np.nan
    x = years - years.mean()
    slope, intercept = np.polyfit(x, logh, 1)
    fitted = intercept + slope * x
    return float(logh[-1] - fitted[-1])


def features_at_origin(origin_year: int, eligible: set[int] | None = None) -> pd.DataFrame:
    """All GRIP-1 predictors for one origin year, vintage-locked."""
    base = origin_year - 1
    delin = cbsa_src.delineation_for_origin(origin_year)
    cw = cbsa_src.crosswalk(delin)
    pop = pep_src.cbsa_population(max_vintage=base, crosswalk=cw)

    hpi = fhfa_src.annual_hpi()
    hpi = hpi[hpi["year"] <= base]

    # Permits: lagged one full year past the base year, because BPS has no
    # revision-vintage archive and the base-year file would still be revising
    # when a forecaster stood at the origin. See bps.DEVIATION.
    permit_base = base - 1
    perm = bps_src.permit_history(permit_base, back=7)
    perm_wide = (
        perm.pivot(index="cbsa_code", columns="year", values="permit_units")
        if not perm.empty
        else pd.DataFrame()
    )

    rows = []
    for code, grp in pop.groupby("cbsa_code"):
        if eligible is not None and code not in eligible:
            continue
        g = grp.set_index("year")["pop"].sort_index()
        if base not in g.index or (base - 3) not in g.index:
            continue
        pop_g1 = g[base] / g[base - 1] - 1 if (base - 1) in g.index else np.nan
        pop_g3 = (g[base] / g[base - 3]) ** (1 / 3) - 1

        h = hpi[hpi["cbsa_code"] == code].set_index("year")["hpi"].sort_index()
        hpi_g1 = hpi_g5 = hpi_gap = hpi_vol = np.nan
        if base in h.index:
            if (base - 1) in h.index:
                hpi_g1 = h[base] / h[base - 1] - 1
            if (base - 5) in h.index:
                hpi_g5 = (h[base] / h[base - 5]) ** (1 / 5) - 1
            win = h[(h.index >= base - TREND_WINDOW) & (h.index <= base)]
            if len(win) >= 8:
                hpi_gap = _log_trend_gap(win.index.values.astype(float), np.log(win.values))
            g5 = h.pct_change().dropna()
            g5 = g5[(g5.index > base - 6) & (g5.index <= base)]
            if len(g5) >= 4:
                hpi_vol = float(np.std(g5.values, ddof=1))

        # Permits per 1,000 residents, and the 3-year change in permitting
        # intensity. A rate, not a percentile, so no cross-sectional reference
        # distribution is baked in.
        permits_pc = permits_g3 = np.nan
        if not perm_wide.empty and code in perm_wide.index:
            pr = perm_wide.loc[code]
            if permit_base in pr.index and pd.notna(pr.get(permit_base)):
                permits_pc = float(pr[permit_base]) / g[base] * 1000.0
                recent = [pr.get(y) for y in range(permit_base - 2, permit_base + 1)]
                prior = [pr.get(y) for y in range(permit_base - 5, permit_base - 2)]
                recent = [v for v in recent if pd.notna(v)]
                prior = [v for v in prior if pd.notna(v)]
                if len(recent) == 3 and len(prior) == 3 and sum(prior) > 0:
                    permits_g3 = float(np.log(max(sum(recent), 1.0) / sum(prior)))

        rows.append(
            {
                "origin_year": origin_year,
                "base_year": base,
                "cbsa_code": code,
                "cbsa_title": grp["cbsa_title"].iat[0],
                "division": grp["division"].iat[0],
                "pop_base": g[base],
                "pop_g1": pop_g1,
                "pop_g3": pop_g3,
                "pop_accel": pop_g1 - pop_g3,
                "hpi_g1": hpi_g1,
                "hpi_g5": hpi_g5,
                "hpi_gap": hpi_gap,
                "hpi_vol": hpi_vol,
                "permits_pc": permits_pc,
                "permits_g3": permits_g3,
                "permit_base_year": permit_base,
                "max_pep_vintage": base,
                "delineation_vintage": delin,
            }
        )
    return pd.DataFrame(rows)


def targets_from_base(base_year: int, horizon: int, truth_cw: pd.DataFrame) -> pd.DataFrame:
    """Realised outcomes over base_year -> base_year + horizon."""
    truth = pep_src.truth_population()
    merged = truth.merge(truth_cw[["fips", "cbsa_code"]], on="fips", how="inner")
    agg = merged.groupby(["cbsa_code", "year"], as_index=False)["pop"].sum()
    wide = agg.pivot(index="cbsa_code", columns="year", values="pop")

    end = base_year + horizon
    out = pd.DataFrame(index=wide.index)
    if base_year in wide.columns and end in wide.columns:
        out["y_pop"] = (wide[end] / wide[base_year]) ** (1 / horizon) - 1
    else:
        out["y_pop"] = np.nan

    hpi = fhfa_src.annual_hpi().pivot(index="cbsa_code", columns="year", values="hpi")
    if base_year in hpi.columns and end in hpi.columns:
        hp = (hpi[end] / hpi[base_year]) ** (1 / horizon) - 1
        out = out.join(hp.rename("y_hpi"), how="left")
    else:
        out["y_hpi"] = np.nan

    out = out.reset_index()
    out["horizon"] = horizon
    return out


def demean_within(
    df: pd.DataFrame,
    cols: list[str],
    by: tuple[str, ...] = ("origin_year", "division"),
    min_group: int = 5,
) -> pd.DataFrame:
    """Within-region, within-origin demeaning -- the AMIP move (PROTOCOL section 5).

    Prescribing the forcing means removing BOTH components we do not claim to
    forecast: the regional level (division) and the era (origin_year). Demeaning
    by division alone leaves the national cycle in the residual, and that
    residual is itself a clock -- which is how the first run of this harness
    flagged every price feature as CLOCK_LEAK.
    """
    out = df.copy()
    keys = list(by)
    sizes = out.groupby(keys)[cols[0]].transform("size")
    out = out[sizes >= min_group].copy()
    for c in cols:
        if c in out:
            out[c + "_wr"] = out[c] - out.groupby(keys)[c].transform("mean")
    return out
