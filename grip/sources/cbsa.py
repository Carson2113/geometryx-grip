"""CBSA delineation files -> county->CBSA crosswalk, per OMB vintage.

Boundary-comparable metro sets matter: a metro that gained a county between two
origin years is not the same object, and comparing it across origins silently
mixes a geography change into a growth signal. PROTOCOL.md section 3.
"""
from __future__ import annotations

import pandas as pd

from ..fetch import get

# OMB delineation vintages, oldest first. Each origin year is assigned the most
# recent delineation published on or before Dec 31 of that year.
#
# The December 2003 file is the first CBSA-era delineation and shares the list3
# layout (single combined 5-digit FIPS column). It was located by probing Census
# under v2.0.0-prereg; the 2004-2008 annual updates are not served at any URL we
# could reach, so an origin in 2004-2008 correctly inherits the 2003 vintage,
# which is the most recent delineation available on or before that origin. That is
# G4-legal and is not a relaxation: it uses older geography, never newer.
DELINEATIONS = {
    2003: "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2003/historical-delineation-files/0312cbsas-csas.xls",
    2009: "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2009/historical-delineation-files/list3.xls",
    2013: "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2013/delineation-files/list1.xls",
    2015: "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2015/delineation-files/list1.xls",
    2017: "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2017/delineation-files/list1.xls",
    2018: "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2018/delineation-files/list1_Sep_2018.xls",
    2020: "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2020/delineation-files/list1_2020.xls",
    2023: "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx",
}

# Census has used two layouts. Modern list1 files carry separate state and county
# FIPS columns; the 2009-era list3 file carries one combined 5-digit FIPS column.
_ALIASES = {
    "cbsa_code": ["cbsa code"],
    "cbsa_title": ["cbsa title"],
    "level": ["metropolitan/micropolitan statistical area", "level of cbsa"],
    "state_fips": ["fips state code", "state fips code"],
    "county_fips": ["fips county code", "county fips code"],
    "combined_fips": ["fips"],
}


def _pick(df: pd.DataFrame) -> pd.DataFrame:
    lower = {str(c).strip().lower(): c for c in df.columns}
    out = {}
    for target, aliases in _ALIASES.items():
        for a in aliases:
            if a in lower:
                out[target] = df[lower[a]]
                break
    return pd.DataFrame(out)


def crosswalk(vintage: int) -> pd.DataFrame:
    """County FIPS -> CBSA for an OMB delineation vintage (metropolitan only)."""
    url = DELINEATIONS[vintage]
    ext = ".xlsx" if url.endswith("xlsx") else ".xls"
    path = get(url, name=f"cbsa_list1_{vintage}{ext}")

    raw = None
    for skip in (2, 3, 1, 0, 4):
        try:
            cand = pd.read_excel(path, skiprows=skip)
        except Exception:  # noqa: BLE001
            continue
        if "cbsa code" in [str(c).strip().lower() for c in cand.columns]:
            raw = cand
            break
    if raw is None:
        raise RuntimeError(f"could not parse delineation vintage {vintage}")

    df = _pick(raw)
    df["cbsa_code"] = pd.to_numeric(df["cbsa_code"], errors="coerce")
    df = df.dropna(subset=["cbsa_code"])
    df["cbsa_code"] = df["cbsa_code"].astype(int)

    if "state_fips" in df.columns and "county_fips" in df.columns:
        st = pd.to_numeric(df["state_fips"], errors="coerce").astype("Int64")
        ct = pd.to_numeric(df["county_fips"], errors="coerce").astype("Int64")
        df["fips"] = st.astype(str).str.zfill(2) + ct.astype(str).str.zfill(3)
    elif "combined_fips" in df.columns:
        cf = pd.to_numeric(df["combined_fips"], errors="coerce").astype("Int64")
        df["fips"] = cf.astype(str).str.zfill(5)
    else:
        raise RuntimeError(f"no FIPS columns in delineation vintage {vintage}")

    df = df[df["fips"].str.match(r"^\d{5}$", na=False)]
    if "level" in df.columns:
        df = df[df["level"].astype(str).str.contains("Metropolitan", case=False, na=False)]
    df["delineation_vintage"] = vintage
    return df[["fips", "cbsa_code", "cbsa_title", "delineation_vintage"]].drop_duplicates("fips")


def delineation_for_origin(origin_year: int) -> int:
    """Most recent delineation vintage available on or before Dec 31 of origin_year."""
    usable = [v for v in sorted(DELINEATIONS) if v <= origin_year]
    if not usable:
        raise ValueError(f"no delineation available at origin {origin_year}")
    return usable[-1]


def boundary_comparable(vintages: list[int]) -> set[int]:
    """CBSAs whose exact county set is identical across all given vintages.

    Only these metros are eligible for cross-origin comparison, so that a
    boundary revision can never be mistaken for growth.
    """
    sets: dict[int, dict[int, frozenset]] = {}
    for v in vintages:
        cw = crosswalk(v)
        sets[v] = {int(code): frozenset(grp["fips"]) for code, grp in cw.groupby("cbsa_code")}
    common = set.intersection(*[set(s) for s in sets.values()])
    return {code for code in common if len({sets[v][code] for v in vintages}) == 1}
