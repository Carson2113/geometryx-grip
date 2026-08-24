"""Probe which OMB delineation vintages are publicly fetchable.

This determines the earliest origin at which hpi_income_gap is legal under G4
(delineation vintage <= origin year), because that feature needs a county->CBSA
crosswalk to aggregate BEA county income to metros.

Reads no outcome. Fits nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from grip.fetch import try_get

# Candidate vintages Census may serve. The harness currently knows only 2009+.
CANDIDATES: dict[int, list[str]] = {
    2003: [
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2003/historical-delineation-files/0312cbsas-csas.xls",
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2003/historical-delineation-files/030606omb-cbsa-csa.xls",
    ],
    2004: [
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2004/historical-delineation-files/list1.xls",
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2004/historical-delineation-files/0411cbsas-csas.xls",
    ],
    2005: [
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2005/historical-delineation-files/list1.xls",
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2005/historical-delineation-files/0512cbsas-csas.xls",
    ],
    2006: [
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2006/historical-delineation-files/list1.xls",
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2006/historical-delineation-files/0612cbsas-csas.xls",
    ],
    2007: [
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2007/historical-delineation-files/list1.xls",
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2007/historical-delineation-files/List4.txt",
    ],
    2008: [
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2008/historical-delineation-files/list1.xls",
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2008/historical-delineation-files/List4.txt",
    ],
    2009: [
        "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2009/historical-delineation-files/list3.xls",
    ],
}


def main() -> None:
    found: dict[str, dict] = {}
    for vintage, urls in CANDIDATES.items():
        rec = {"fetched": None, "url": None, "readable": False, "n_rows": 0, "note": ""}
        for url in urls:
            p = try_get(url, name=f"probe_cbsa_{vintage}{Path(url).suffix}")
            if p is None:
                continue
            rec["fetched"] = True
            rec["url"] = url
            try:
                if url.endswith(".txt"):
                    df = pd.read_csv(p, sep=None, engine="python", dtype=str)
                else:
                    df = None
                    for skip in (2, 3, 1, 0, 4):
                        try:
                            cand = pd.read_excel(p, skiprows=skip)
                        except Exception:  # noqa: BLE001
                            continue
                        cols = [str(c).strip().lower() for c in cand.columns]
                        if any("cbsa code" in c for c in cols):
                            df = cand
                            break
                if df is not None and len(df):
                    rec["readable"] = True
                    rec["n_rows"] = int(len(df))
                    rec["columns"] = [str(c).strip() for c in df.columns][:12]
                else:
                    rec["note"] = "fetched but no CBSA-code header found"
            except Exception as e:  # noqa: BLE001
                rec["note"] = f"parse failed: {type(e).__name__}: {e}"
            break
        else:
            rec["fetched"] = False
            rec["note"] = "all candidate URLs unreachable"
        found[str(vintage)] = rec
        print(f"{vintage}: fetched={rec['fetched']} readable={rec['readable']} "
              f"rows={rec['n_rows']} {rec['note']}")

    Path("out").mkdir(exist_ok=True)
    Path("out/probe_delineations.json").write_text(json.dumps(found, indent=2))
    usable = sorted(int(v) for v, r in found.items() if r["readable"])
    print("\nusable vintages:", usable)
    print("earliest legal origin for a crosswalk-dependent feature:",
          min(usable) if usable else None)


if __name__ == "__main__":
    main()
