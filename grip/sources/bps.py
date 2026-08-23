"""Census Building Permits Survey (BPS), metro annual totals.

Permits are the strongest documented free leading indicator for metro housing:
a 2026 Dallas Fed nowcast built on permits and starts correlates 0.86 with
observed FHFA HPI. They are also public domain and unlimited-access, which is
exactly the class of input GRIP is built around.

Endpoint layout (verified live):
  legacy, 1999-2023, pre-2024 OMB delineation:
    https://www2.census.gov/econ/bps/Metro%20(ending%202023)/ma{YY}{MM}y.txt
  current, Jan 2024 onward, 2023 delineation:
    https://www2.census.gov/econ/bps/CBSA%20(beginning%20Jan%202024)/cbsa{YY}{MM}y.txt

The `...y.txt` files are year-to-date cumulative, so month 12 is the full-year
total. Files are fixed-layout text with a two-line header.

PROTOCOL DEVIATION (declared): BPS has no revision-vintage archive -- each file
is overwritten in place as revisions land, so a true point-in-time reconstruction
is impossible from the public endpoint. GRIP therefore uses only annual permit
COUNTS at least one full year before the origin, and reports this deviation on
every scorecard rather than burying it. AIMIP precedent: DLESyM's checkpoint
contained 1.5 years of holdout and the deviation was named publicly.
"""
from __future__ import annotations

import functools
import io

import pandas as pd

from ..fetch import try_get

LEGACY = "https://www2.census.gov/econ/bps/Metro%20(ending%202023)/ma{yy}12y.txt"
CURRENT = "https://www2.census.gov/econ/bps/CBSA%20(beginning%20Jan%202024)/cbsa{yy}12y.txt"

DEVIATION = (
    "Census BPS publishes no revision-vintage archive; annual permit totals are "
    "the current revision, not the as-of-origin revision. Mitigated by using "
    "counts lagged at least one full year before the origin."
)


def _parse(text: str, year: int) -> pd.DataFrame:
    """Extract CBSA code and total units from a BPS annual metro file."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    rows = []
    for ln in lines:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 8:
            continue
        # Layout: Survey, CSA, CBSA, HHEADER(name pieces...), then numeric blocks
        # of (Bldgs, Units, Value) for 1-unit, 2-unit, 3-4 unit, 5+ unit.
        if not parts[0].isdigit():
            continue
        cbsa = parts[2] if parts[2].isdigit() else None
        if cbsa is None or len(cbsa) != 5:
            continue
        nums = []
        for p in parts[3:]:
            try:
                nums.append(float(p))
            except ValueError:
                continue
        if len(nums) < 12:
            continue
        # The four structure blocks are the first 12 numeric fields, in
        # (Bldgs, Units, Value) triples. Total units = the three Units slots.
        units = nums[1] + nums[4] + nums[7] + nums[10]
        rows.append({"cbsa_code": int(cbsa), "year": year, "permit_units": units})
    if not rows:
        return pd.DataFrame(columns=["cbsa_code", "year", "permit_units"])
    df = pd.DataFrame(rows)
    return df.groupby(["cbsa_code", "year"], as_index=False)["permit_units"].sum()


@functools.lru_cache(maxsize=None)
def annual_permits(year: int) -> pd.DataFrame:
    """Full-year permitted units by CBSA for a calendar year."""
    yy = f"{year % 100:02d}"
    url = CURRENT.format(yy=yy) if year >= 2024 else LEGACY.format(yy=yy)
    path = try_get(url, name=f"bps_metro_{year}.txt")
    if path is None:
        return pd.DataFrame(columns=["cbsa_code", "year", "permit_units"])
    text = path.read_text(encoding="latin-1", errors="replace")
    return _parse(text, year)


def permit_history(through_year: int, back: int = 6) -> pd.DataFrame:
    """Annual permit units for the years a forecaster could hold at `through_year`."""
    frames = [annual_permits(y) for y in range(through_year - back + 1, through_year + 1)]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=["cbsa_code", "year", "permit_units"])
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    for y in (2009, 2014, 2019, 2023):
        d = annual_permits(y)
        print(y, "metros:", len(d), "median units:", None if d.empty else d.permit_units.median())
        print(io.StringIO(d.head(3).to_string()).getvalue())
