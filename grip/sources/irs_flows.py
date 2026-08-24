"""IRS SOI county-to-county migration flows -> directed CBSA pair edges.

Source: https://www.irs.gov/statistics/soi-tax-stats-migration-data
US Government work, public domain. Class B for as long as IRS is the only source
for the pair cell (GRIP2_REGISTRATION.md section 3a).

Three publication eras, one canonical schema
--------------------------------------------
IRS has published county flows in three incompatible containers. All three carry
the same nine logical fields, so they are normalised to one frame:

    flow_year, y2_state, y2_county, y1_state, y1_county, y1_name, n1, n2, agi

`flow_year` is the *destination* year y2, i.e. the 2003->2004 transition is
flow_year 2004. This convention is fixed here and must not be changed later:
shifting it by one year moves the origin count, which is exactly the kind of
after-the-fact adjustment section 6 forbids.

    flow_year <= 2004   per-state Excel inside <y1>to<y2>countymigration.zip
    flow_year >= 2005   national CSV countyinflow<yy><yy>.csv

The 1990->1991 and 1991->1992 archives hold fixed-width .txt and are NOT
implemented. This costs nothing gradeable: under G4 a crosswalk vintage must not
postdate the origin, the earliest CBSA delineation is December 2003, so the
earliest legal origin is 2003 and the earliest base is 2002. Flow years before
2002 cannot enter any gradeable cell.

What the pseudo-FIPS codes mean
-------------------------------
Neither era's file is a pure edge list. Codes above 56 in the origin position are
aggregates, not places:

    96/000  total migration, US and foreign
    97/000  total migration, US            <- coverage denominator
    97/001  total migration, US, same state       (legacy sub-total)
    97/003  total migration, US, different state  (legacy sub-total)
    98/000  total migration, foreign
    58/000  other flows, same state       (modern; the suppressed residual)
    59/000  other flows, different state  (modern; the suppressed residual)

Summing every row would double count migration several times over. Only rows
with both endpoints in 1..56 and a non-zero county code are directed edges.

Suppression is absence, not a withheld value
-------------------------------------------
A county pair is released only above a returns threshold: 10 returns through the
2010-2011 transition, 20 from 2011-2012 (per the IRS user guides).

Section 3a requires suppressed edges to be 'a modelled state, not a dropped row'.
Checking the files shows that requirement cannot be met as literally written. The
rows carrying n1 = -1 (6,433 in flow_year 2012, 5,818 in 2023) are never named
county pairs: every one is an aggregate, a foreign row, or an 'Other flows'
bucket. A genuinely suppressed county pair is not present in the file at all; its
mass is folded into the regional 58/59 rows.

So there is no per-pair suppression flag to carry, and `edge_suppressed` is a
label that never fires on real data. The censoring is instead:

    for any ordered pair absent from the file, flow lies in [0, threshold - 1],
    and the 58/59 rows give the row-sum of that hidden mass per destination and
    region.

That is interval censoring with an aggregate constraint, which a hurdle model can
represent, but it is a harder object than section 3a implies, and a true zero is
not distinguishable from a small suppressed flow. `suppressed_county_edges` in
`metro_pair_flows` is therefore structurally zero, and is retained only so the
claim can be re-checked, not because it carries information.
"""
from __future__ import annotations

import io
import re
import zipfile
from functools import lru_cache

import pandas as pd

from ..fetch import get, try_get

LANDING = "https://www.irs.gov/statistics/soi-tax-stats-migration-data"
BASE = "https://www.irs.gov/pub/irs-soi"

CSV_FROM = 2005  # first flow_year served as a national CSV
LEGACY_FROM = 1992  # first flow_year served as per-state Excel

COLS = ["y2_state", "y2_county", "y1_state", "y1_county", "y1_name", "n1", "n2", "agi"]

# Returns threshold for releasing a county pair, by flow_year. From the IRS user
# guides: 1112inpublicmigdoc.pdf (10 returns) and 2223inpublicmigdoc.pdf (20).
def suppression_threshold(flow_year: int) -> int:
    return 20 if flow_year >= 2012 else 10


def _yy(y: int) -> str:
    return f"{y % 100:02d}"


def _csv_url(flow_year: int) -> str:
    return f"{BASE}/countyinflow{_yy(flow_year - 1)}{_yy(flow_year)}.csv"


def _zip_url(flow_year: int) -> str:
    return f"{BASE}/{flow_year - 1}to{flow_year}countymigration.zip"


def _norm(df: pd.DataFrame, flow_year: int) -> pd.DataFrame:
    """Coerce to the canonical schema and classify every row."""
    df = df.copy()
    df.columns = COLS
    for c in ("y2_state", "y2_county", "y1_state", "y1_county", "n1", "n2", "agi"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["y2_state", "y2_county", "y1_state", "y1_county"])
    for c in ("y2_state", "y2_county", "y1_state", "y1_county"):
        df[c] = df[c].astype(int)
    df["flow_year"] = flow_year

    real_o = df["y1_state"].between(1, 56) & (df["y1_county"] > 0)
    real_d = df["y2_state"].between(1, 56) & (df["y2_county"] > 0)
    df["kind"] = "aggregate"
    df.loc[(df["y1_state"] == 97) & (df["y1_county"] == 0), "kind"] = "total_us"
    df.loc[df["y1_state"] == 98, "kind"] = "foreign"
    df.loc[df["y1_state"].isin([58, 59]), "kind"] = "other_flows"
    df.loc[real_o & real_d, "kind"] = "edge"
    # Each county file carries a self-referential row, 'X County Non-Migrants',
    # counting filers who did NOT move. Both endpoints are real counties, so it
    # passes the endpoint test and must be excluded explicitly. In flow_year 2004
    # these rows are the twelve largest 'edges' in the file and inflate released
    # mass roughly fifteenfold.
    df.loc[
        (df["kind"] == "edge")
        & (df["y1_state"] == df["y2_state"])
        & (df["y1_county"] == df["y2_county"]),
        "kind",
    ] = "non_migrant"
    # A released edge whose value was withheld. Kept, labelled, never dropped.
    df.loc[(df["kind"] == "edge") & (df["n1"].fillna(-1) < 0), "kind"] = "edge_suppressed"

    df["o_fips"] = (
        df["y1_state"].astype(str).str.zfill(2) + df["y1_county"].astype(str).str.zfill(3)
    )
    df["d_fips"] = (
        df["y2_state"].astype(str).str.zfill(2) + df["y2_county"].astype(str).str.zfill(3)
    )
    return df


def _read_legacy(flow_year: int) -> pd.DataFrame:
    """Per-state inflow workbooks inside one transition ZIP."""
    path = get(_zip_url(flow_year), name=f"irs_{flow_year - 1}to{flow_year}_county.zip")
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(path) as z:
        members = [
            m
            for m in z.namelist()
            if "inflow" in m.lower() and m.lower().endswith((".xls", ".xlsx"))
        ]
        if not members:
            raise RuntimeError(f"no inflow workbooks in {_zip_url(flow_year)}")
        for m in members:
            raw = z.read(m)
            try:
                wb = pd.read_excel(io.BytesIO(raw), header=None, dtype=object)
            except Exception:  # noqa: BLE001
                continue
            if wb.shape[1] < 9:
                continue
            wb = wb.iloc[:, :9]
            # Data begins at the first row whose first cell is a 1-2 digit state
            # FIPS. Header depth varies between vintages, so it is found, not
            # assumed.
            first = wb[0].astype(str).str.strip().str.match(r"^\d{1,2}$", na=False)
            if not first.any():
                continue
            wb = wb.loc[first.idxmax():]
            wb = wb.drop(columns=[4])  # legacy state-abbrev column
            frames.append(wb)
    if not frames:
        raise RuntimeError(f"parsed no rows for flow_year {flow_year}")
    out = pd.concat(frames, ignore_index=True)
    return _norm(out, flow_year)


def _read_csv(flow_year: int) -> pd.DataFrame:
    path = get(_csv_url(flow_year), name=f"irs_countyinflow_{_yy(flow_year - 1)}{_yy(flow_year)}.csv")
    # Not UTF-8: county names carry Latin-1 bytes (e.g. Spanish tildes in PR).
    df = pd.read_csv(path, dtype=str, low_memory=False, encoding="latin-1")

    # IRS has used two header dialects for the same nine columns in the same
    # order: State_Code_Dest.. for flow years 2005-2011, y2_statefips.. from 2012.
    # Columns are taken positionally, but the dialect is asserted first so a third
    # layout fails loudly instead of being silently mis-mapped.
    head = [str(c).strip().strip('"').lower() for c in df.columns[:9]]
    dialects = {
        "modern": ["y2_statefips", "y2_countyfips", "y1_statefips", "y1_countyfips",
                   "y1_state", "y1_countyname", "n1", "n2", "agi"],
        "mid": ["state_code_dest", "county_code_dest", "state_code_origin",
                "county_code_origin", "state_abbrv", "county_name", "return_num",
                "exmpt_num", "aggr_agi"],
    }
    if head not in dialects.values():
        raise RuntimeError(
            f"unrecognised IRS county CSV header for flow_year {flow_year}: {head}"
        )

    out = df.iloc[:, :9].drop(columns=df.columns[4])  # drop the state-abbrev text column
    return _norm(out, flow_year)


@lru_cache(maxsize=64)
def county_flows(flow_year: int) -> pd.DataFrame:
    """All rows for one transition, classified. flow_year is the destination year."""
    if flow_year >= CSV_FROM:
        return _read_csv(flow_year)
    if flow_year >= LEGACY_FROM:
        return _read_legacy(flow_year)
    raise NotImplementedError(
        f"flow_year {flow_year} is fixed-width .txt and is not implemented; "
        "no gradeable cell can reach a flow year before 2002 (G4 delineation floor)"
    )


def available_years(lo: int = 1992, hi: int = 2023) -> list[int]:
    """Flow years whose container is actually served, checked by HTTP."""
    out = []
    for y in range(lo, hi + 1):
        url = _csv_url(y) if y >= CSV_FROM else _zip_url(y)
        if try_get(url, name=f"irs_avail_{y}{'.csv' if y >= CSV_FROM else '.zip'}") is not None:
            out.append(y)
    return out


def coverage(flow_year: int) -> dict:
    """Share of domestic migration mass assignable to a named county pair.

    Denominator is the sum of the 97/000 'Total Mig - US' rows over destination
    counties, which is the file's own statement of domestic in-migration.
    Numerator is released named edges. The gap is mass whose partner county was
    withheld. Section 6 requires this to be at least 70% for the cell to run.
    """
    df = county_flows(flow_year)
    denom = df.loc[(df["kind"] == "total_us") & (df["y2_county"] > 0), "n1"].clip(lower=0).sum()
    edges = df[df["kind"] == "edge"]
    named = edges["n1"].clip(lower=0).sum()
    return {
        "flow_year": flow_year,
        "threshold_returns": suppression_threshold(flow_year),
        "total_us_returns": int(denom),
        "named_edge_returns": int(named),
        "named_edges": int(len(edges)),
        "suppressed_edge_rows": int((df["kind"] == "edge_suppressed").sum()),
        "other_flows_returns": int(
            df.loc[df["kind"] == "other_flows", "n1"].clip(lower=0).sum()
        ),
        "named_share": float(named / denom) if denom else None,
    }


def metro_pair_flows(flow_year: int, delineation_vintage: int) -> pd.DataFrame:
    """Directed CBSA-pair flows for one flow year, under one delineation vintage.

    The vintage is passed in rather than derived here so the caller must satisfy
    G4 (vintage <= origin year) explicitly and visibly.

    Returns one row per ordered (o_cbsa, d_cbsa) pair with o != d, carrying both
    the released mass and the count of suppressed constituent county edges, so
    the estimator can condition on how much of a pair was withheld.
    """
    from . import cbsa

    cw = cbsa.crosswalk(delineation_vintage)[["fips", "cbsa_code"]]
    df = county_flows(flow_year)
    df = df[df["kind"].isin(["edge", "edge_suppressed"])]

    df = df.merge(cw.rename(columns={"fips": "o_fips", "cbsa_code": "o_cbsa"}), on="o_fips")
    df = df.merge(cw.rename(columns={"fips": "d_fips", "cbsa_code": "d_cbsa"}), on="d_fips")
    df = df[df["o_cbsa"] != df["d_cbsa"]]

    df["released_n1"] = df["n1"].where(df["kind"] == "edge").clip(lower=0)
    df["is_supp"] = (df["kind"] == "edge_suppressed").astype(int)

    out = (
        df.groupby(["o_cbsa", "d_cbsa"], as_index=False)
        .agg(
            n1=("released_n1", "sum"),
            n2=("n2", lambda s: s.clip(lower=0).sum()),
            agi=("agi", lambda s: s.clip(lower=0).sum()),
            county_edges=("released_n1", "size"),
            suppressed_county_edges=("is_supp", "sum"),
        )
    )
    out["flow_year"] = flow_year
    out["delineation_vintage"] = delineation_vintage
    return out
