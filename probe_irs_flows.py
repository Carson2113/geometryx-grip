"""Probe which IRS SOI county-to-county transitions are machine-readable.

This is the binding question for the section 3a pair cell. The modern national
CSV layout is documented from 2011-2012 onward. If nothing earlier parses, the
flow panel has at most 12 flow years, which yields ~8 origins at h=5 and fails
the section 6 precondition of >= 15 origins. So the pre-2011 archive decides
whether the pair cell can be graded at all.

Reads file structure only. No target, no estimation.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd

from grip.fetch import try_get

BASE = "https://www.irs.gov/pub/irs-soi"


def yy(y: int) -> str:
    return f"{y % 100:02d}"


def candidates(y1: int) -> list[str]:
    """Candidate URLs for the y1 -> y1+1 transition, most likely first."""
    y2 = y1 + 1
    a, b = yy(y1), yy(y2)
    return [
        f"{BASE}/countyinflow{a}{b}.csv",
        f"{BASE}/countyinflow{a}{b}.zip",
        f"{BASE}/county{a}{b}.zip",
        f"{BASE}/{a}{b}migrationdata.zip",
        f"{BASE}/{a}{b}countymigration.zip",
        f"{BASE}/co{a}{b}us.zip",
        f"{BASE}/co{a}{b}.zip",
    ]


def sniff(path: Path) -> dict:
    """Identify the payload without assuming a layout."""
    info: dict = {"kind": None, "n_rows": 0, "columns": None, "members": None}
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
        info["kind"] = "zip"
        info["members"] = names[:25]
        info["n_members"] = len(names)
        return info
    # try CSV
    try:
        df = pd.read_csv(path, dtype=str, nrows=5000, low_memory=False)
        info["kind"] = "csv"
        info["n_rows"] = int(sum(1 for _ in open(path, errors="ignore")) - 1)
        info["columns"] = [str(c) for c in df.columns]
    except Exception as e:  # noqa: BLE001
        info["kind"] = f"unparsed: {type(e).__name__}"
    return info


def main() -> None:
    found: dict[str, dict] = {}
    for y1 in range(1990, 2023):
        rec: dict = {"transition": f"{y1}-{y1 + 1}", "url": None}
        for url in candidates(y1):
            p = try_get(url, name=f"irs_probe_{yy(y1)}{yy(y1 + 1)}{Path(url).suffix}")
            if p is None:
                continue
            rec["url"] = url
            rec.update(sniff(p))
            break
        found[str(y1)] = rec
        tag = rec.get("kind") or "MISSING"
        extra = ""
        if rec.get("kind") == "csv":
            extra = f" rows={rec['n_rows']} cols={len(rec['columns'] or [])}"
        elif rec.get("kind") == "zip":
            extra = f" members={rec.get('n_members')}"
        print(f"{y1}->{y1 + 1}: {tag}{extra}  {rec['url'] or ''}")

    Path("out").mkdir(exist_ok=True)
    Path("out/probe_irs_flows.json").write_text(json.dumps(found, indent=2))

    csvs = sorted(int(k) for k, v in found.items() if v.get("kind") == "csv")
    zips = sorted(int(k) for k, v in found.items() if v.get("kind") == "zip")
    print(f"\nCSV transitions: {len(csvs)}", csvs)
    print(f"ZIP transitions: {len(zips)}", zips)
    missing = sorted(int(k) for k, v in found.items() if v.get("url") is None)
    print(f"unreachable: {len(missing)}", missing)


if __name__ == "__main__":
    main()
