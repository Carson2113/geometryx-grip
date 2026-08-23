"""FHFA House Price Index, metro (CBSA) quarterly, 1975-present.

Public domain with a required disclaimer:
    "This product uses FHFA Data but is neither endorsed nor certified by FHFA."

KNOWN PROTOCOL LIMITATION: FHFA does not archive per-release vintages of the
metro file, so the HPI series is revision-contaminated relative to a true
point-in-time feed. We therefore (a) use only lagged growth rates, which are far
less revision-sensitive than levels, and (b) declare this deviation explicitly
in the scorecard, in the same way AIMIP names DLESyM's non-conforming training
window rather than hiding it.
"""
from __future__ import annotations

import functools

import pandas as pd

from ..fetch import get

URL = "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv"
DISCLAIMER = "This product uses FHFA Data but is neither endorsed nor certified by FHFA."


@functools.lru_cache(maxsize=1)
def metro_hpi() -> pd.DataFrame:
    """Columns: cbsa_code, year, quarter, hpi (NSA), t (fractional year)."""
    path = get(URL, name="hpi_at_metro.csv")
    df = pd.read_csv(
        path,
        header=None,
        names=["cbsa_title", "cbsa_code", "year", "quarter", "hpi_nsa", "hpi_sa"],
        dtype=str,
    )
    for c in ("cbsa_code", "year", "quarter"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["hpi"] = pd.to_numeric(df["hpi_nsa"].replace("-", pd.NA), errors="coerce")
    df = df.dropna(subset=["cbsa_code", "year", "quarter", "hpi"])
    df["cbsa_code"] = df["cbsa_code"].astype(int)
    df["year"] = df["year"].astype(int)
    df["quarter"] = df["quarter"].astype(int)
    df["t"] = df["year"] + (df["quarter"] - 1) / 4.0
    return df[["cbsa_code", "year", "quarter", "t", "hpi"]].sort_values(["cbsa_code", "t"])


def annual_hpi() -> pd.DataFrame:
    """Calendar-year mean HPI per CBSA."""
    q = metro_hpi()
    return (
        q.groupby(["cbsa_code", "year"], as_index=False)
        .agg(hpi=("hpi", "mean"), n_q=("hpi", "size"))
        .query("n_q == 4")
        .drop(columns="n_q")
    )

VINTAGE_DEVIATION = (
    "FHFA does not archive per-release vintages of the metro HPI, so index values "
    "are the current revision rather than the as-of-origin revision. Mitigated by "
    "using only lagged growth rates and own-history trend deviations, never levels "
    "compared across metros."
)
