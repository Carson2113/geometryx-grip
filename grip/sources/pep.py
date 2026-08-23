"""Census Population Estimates (PEP), retrieved per VINTAGE.

This is the backbone of the vintage lock. Census publishes a separate
`co-est<YYYY>-alldata.csv` for every estimate vintage, and each vintage revises
prior years. Using today's file to build a 2012 feature is look-ahead bias; the
2011 vintage is what a forecaster could actually have held on 2011-12-31.

Vintage V is released in the first quarter of year V+1, so for origin year Y the
newest legally-available vintage is V = Y - 1.

PEP re-bases at each decennial census, so a single vintage covers only its own
decade. A forecaster standing in 2022 legitimately holds BOTH the 2020s vintage
and the older 2010s files, so `vintage_stack` merges every vintage with a
reference year <= the base year, preferring the newest published value for each
year. There is no V2010 file (census year), which the stack absorbs.
"""
from __future__ import annotations

import functools

import pandas as pd

from ..fetch import try_get

# Vintages Census actually serves, by decade directory template.
_DECADE_DIRS = {
    **{v: f"2000-{v}" for v in range(2001, 2010)},
    **{v: f"2010-{v}" for v in range(2011, 2020)},
    2019: "2010-2019",
    **{v: f"2020-{v}" for v in range(2021, 2025)},
    2024: "2020-2024",
}

AVAILABLE_VINTAGES = sorted(_DECADE_DIRS)


def _url(vintage: int) -> str:
    d = _DECADE_DIRS[vintage]
    return (
        "https://www2.census.gov/programs-surveys/popest/datasets/"
        f"{d}/counties/totals/co-est{vintage}-alldata.csv"
    )


@functools.lru_cache(maxsize=None)
def county_population(vintage: int) -> pd.DataFrame:
    """County population by year, exactly as published in `vintage`.

    Columns: fips, region, division, state_name, county_name, year, pop, pep_vintage
    """
    if vintage not in _DECADE_DIRS:
        raise ValueError(f"no PEP vintage published for {vintage}")
    path = try_get(_url(vintage), name=f"co-est{vintage}-alldata.csv")
    if path is None:
        raise RuntimeError(f"PEP vintage {vintage} unavailable")

    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    df.columns = [str(c).upper() for c in df.columns]
    df = df[pd.to_numeric(df["SUMLEV"], errors="coerce") == 50].copy()

    df["fips"] = (
        pd.to_numeric(df["STATE"], errors="coerce").astype("Int64").astype(str).str.zfill(2)
        + pd.to_numeric(df["COUNTY"], errors="coerce").astype("Int64").astype(str).str.zfill(3)
    )
    popcols = [c for c in df.columns if c.startswith("POPESTIMATE") and c[-4:].isdigit()]
    keep = ["fips", "REGION", "DIVISION", "STNAME", "CTYNAME"] + popcols
    long = df[keep].melt(
        id_vars=["fips", "REGION", "DIVISION", "STNAME", "CTYNAME"],
        value_vars=popcols,
        var_name="var",
        value_name="pop",
    )
    long["year"] = long["var"].str[-4:].astype(int)
    long = long.drop(columns=["var"])
    long["pop"] = pd.to_numeric(long["pop"], errors="coerce")
    long["division"] = pd.to_numeric(long["DIVISION"], errors="coerce")
    long["region"] = pd.to_numeric(long["REGION"], errors="coerce")
    long = long.rename(columns={"STNAME": "state_name", "CTYNAME": "county_name"})
    long["pep_vintage"] = vintage
    # A vintage never contains estimates past its own reference year.
    return long[long["year"] <= vintage].dropna(subset=["pop"])


@functools.lru_cache(maxsize=None)
def vintage_stack(max_vintage: int) -> pd.DataFrame:
    """All population years knowable to a forecaster holding vintages <= max_vintage.

    For each (county, year) the newest published estimate wins, which is what a
    real forecaster would use. Nothing published after `max_vintage` can enter.
    """
    usable = [v for v in AVAILABLE_VINTAGES if v <= max_vintage]
    if not usable:
        raise ValueError(f"no PEP vintage at or before {max_vintage}")
    frames = []
    for v in usable:
        try:
            frames.append(county_population(v))
        except Exception:  # noqa: BLE001
            continue
    if not frames:
        raise RuntimeError(f"no PEP vintages loadable at or before {max_vintage}")
    allrows = pd.concat(frames, ignore_index=True)
    allrows = allrows.sort_values("pep_vintage").drop_duplicates(["fips", "year"], keep="last")
    return allrows


def cbsa_population(max_vintage: int, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the legal vintage stack to CBSA using a county->CBSA crosswalk."""
    cty = vintage_stack(max_vintage)
    merged = cty.merge(crosswalk[["fips", "cbsa_code", "cbsa_title"]], on="fips", how="inner")
    grp = (
        merged.groupby(["cbsa_code", "cbsa_title", "year"], as_index=False)
        .agg(pop=("pop", "sum"), n_counties=("fips", "nunique"))
    )
    # Each CBSA inherits the modal Census division of its counties, for the
    # within-region demeaning in PROTOCOL.md section 5.
    div = (
        merged.groupby("cbsa_code")["division"]
        .agg(lambda s: s.mode().iat[0] if not s.mode().empty else float("nan"))
        .rename("division")
    )
    grp = grp.merge(div, on="cbsa_code", how="left")
    grp["max_pep_vintage"] = max_vintage
    return grp


def truth_population() -> pd.DataFrame:
    """Final (most-revised) county population, used ONLY for outcomes.

    Analogous to grading a climate model against ERA5: the target may use the
    best available revision, because the forecaster is not asked to predict the
    revision -- only the outcome.
    """
    return vintage_stack(max(AVAILABLE_VINTAGES))
