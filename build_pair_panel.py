"""Build the section 3a directed metro-pair flow panel and check its section 6 preconditions.

Fits NOTHING. No coefficient, no standard error, no baseline, no feature-outcome
relationship. This runs under the v2.0.0-prereg anchor and its only outputs are
counts of available data. The censored PPML estimator, the persistence baseline
and the gravity baseline are deliberately absent: computing any of them before
the scheduled grading run would spend the blindness the anchor exists to protect.

Geography rule (G4). A cell's geography is fixed at its ORIGIN year and that one
delineation vintage is applied to every flow year in the cell, including target
years that fall after it. Using a later vintage for later target years would let
a boundary revision leak into the outcome; using the origin's vintage throughout
means the metro is the same object at base and at target.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from grip.sources import cbsa
from grip.sources import irs_flows as F

OUT = Path("out")
PANEL = Path("panel")

FLOW_LO, FLOW_HI = 2002, 2023  # flow years usable under the G4 delineation floor
MIN_ORIGINS = 15
MIN_PAIRS = 20_000
MIN_COVERAGE = 0.70


def coverage_table() -> pd.DataFrame:
    rows = []
    for y in range(FLOW_LO, FLOW_HI + 1):
        try:
            rows.append(F.coverage(y))
        except Exception as e:  # noqa: BLE001
            rows.append({"flow_year": y, "named_share": None, "error": repr(e)})
        print(f"  coverage {y}: {rows[-1].get('named_share')}")
    return pd.DataFrame(rows)


def build(vintages: set[int]) -> dict[tuple[int, int], dict]:
    """Materialise pair frames for every (vintage, flow_year) a cell may need."""
    PANEL.mkdir(exist_ok=True)
    stats: dict[tuple[int, int], dict] = {}
    for v in sorted(vintages):
        frames = []
        for y in range(FLOW_LO, FLOW_HI + 1):
            p = F.metro_pair_flows(y, v)
            frames.append(p)
            stats[(v, y)] = {
                "pairs": int(len(p)),
                "origin_metros": int(p["o_cbsa"].nunique()),
                "dest_metros": int(p["d_cbsa"].nunique()),
                "returns": int(p["n1"].sum()),
            }
            print(f"  vintage {v} flow_year {y}: {len(p):,} pairs")
        out = pd.concat(frames, ignore_index=True)
        out.to_parquet(PANEL / f"pair_flows_v{v}.parquet", index=False)
    return stats


def main() -> None:
    OUT.mkdir(exist_ok=True)

    print("Named-edge coverage per flow year")
    cov = coverage_table()
    cov.to_json(OUT / "flow_coverage.json", orient="records", indent=2)
    ok_cov = cov.dropna(subset=["named_share"])
    print(
        f"  coverage range {ok_cov['named_share'].min():.4f}-{ok_cov['named_share'].max():.4f}, "
        f"years below {MIN_COVERAGE}: "
        f"{sorted(ok_cov.loc[ok_cov['named_share'] < MIN_COVERAGE, 'flow_year'])}"
    )

    # Which bases are arithmetically legal, before looking at any counts.
    cells = []
    for h in (5, 3):
        for base in range(FLOW_LO, FLOW_HI + 1):
            origin = base + 1
            if base + h > FLOW_HI:
                continue  # target year not published
            try:
                v = cbsa.delineation_for_origin(origin)
            except ValueError:
                continue  # no G4-legal crosswalk at this origin
            cells.append({"h": h, "base": base, "origin": origin, "vintage": v})
    cell_df = pd.DataFrame(cells)
    print(f"\nG4-legal (h, base) combinations: {len(cell_df)}")

    print("\nBuilding pair panels")
    stats = build(set(cell_df["vintage"]))

    # Precondition evaluation, per horizon.
    results = {}
    for h in (5, 3):
        sub = cell_df[cell_df["h"] == h].copy()
        sub["pairs_at_base"] = [stats[(r.vintage, r.base)]["pairs"] for r in sub.itertuples()]
        sub["origin_metros"] = [
            stats[(r.vintage, r.base)]["origin_metros"] for r in sub.itertuples()
        ]
        sub["dest_metros"] = [stats[(r.vintage, r.base)]["dest_metros"] for r in sub.itertuples()]
        cov_ok = all(
            float(cov.loc[cov["flow_year"] == y, "named_share"].iloc[0]) >= MIN_COVERAGE
            for r in sub.itertuples()
            for y in range(r.base, r.base + h + 1)
        )
        n_orig = int(len(sub))
        med = float(sub["pairs_at_base"].median())
        min_clusters = int(min(sub["origin_metros"].min(), sub["dest_metros"].min()))
        checks = {
            "origins_ge_15": n_orig >= MIN_ORIGINS,
            "median_pairs_ge_20000": med >= MIN_PAIRS,
            "coverage_ge_70pct_all_years": bool(cov_ok),
            "clusters_ge_10_two_way": min_clusters >= 10,
        }
        results[f"FLOW_PAIR_h{h}"] = {
            "origins": n_orig,
            "origin_range": [int(sub["origin"].min()), int(sub["origin"].max())],
            "median_pairs_at_base": med,
            "min_pairs_at_base": int(sub["pairs_at_base"].min()),
            "max_pairs_at_base": int(sub["pairs_at_base"].max()),
            "min_cluster_count": min_clusters,
            "vintages_used": sorted(set(int(x) for x in sub["vintage"])),
            "checks": checks,
            "verdict": "PRECONDITIONS MET" if all(checks.values()) else "UNINFORMATIVE",
            "failed": [k for k, ok in checks.items() if not ok],
        }

    payload = {
        "anchor": "v2.0.0-prereg",
        "estimated_anything": False,
        "flow_years_used": [FLOW_LO, FLOW_HI],
        "cells": results,
    }
    (OUT / "flow_preconditions.json").write_text(json.dumps(payload, indent=2))

    print("\n=== section 6 preconditions, y_flow_pair ===")
    for name, r in results.items():
        print(
            f"{name}: origins={r['origins']} {r['origin_range']} "
            f"median_pairs={r['median_pairs_at_base']:,.0f} "
            f"clusters>={r['min_cluster_count']} -> {r['verdict']} {r['failed']}"
        )


if __name__ == "__main__":
    main()
