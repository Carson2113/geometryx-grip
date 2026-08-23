"""Render GRIP scorecard JSON as the published markdown scorecard.

The scoreboard is the product. AIMIP's leverage did not come from any single
model; it came from being the place where models are graded in public, with
deviations named. This renderer exists so that every run produces an artifact
that can be published without editing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * float(x):.1f}%"


def _num(x, nd=3) -> str:
    return "n/a" if x is None else f"{float(x):.{nd}f}"


def render(cards: list[dict]) -> str:
    L: list[str] = []
    L.append("# GRIP-1 Scorecard")
    L.append("")
    L.append(
        "Geometryx Relocation Intercomparison Protocol, reference run. "
        "Every number below was produced by `run_backtest.py` against public-domain "
        "federal files under the vintage lock in `PROTOCOL.md`. No licensed data was used."
    )
    L.append("")

    for c in cards:
        s = c.get("summary", {})
        h = c["horizon_years"]
        L.append(f"## Horizon {h} years")
        L.append("")
        L.append(f"- Run started: `{c['run_started_utc']}`")
        L.append(f"- Target: `{c['target']}` (within-division, within-origin demeaned population growth)")
        L.append(f"- Origins in panel: {c['origins_in_panel']}")
        L.append(f"- Panel rows: {c['n_panel_rows']}; median metros per origin: {c['n_metros_median_per_origin']}")
        L.append(f"- Mandatory baseline: `{c['baseline']}`")
        L.append("")

        L.append("### Headline")
        L.append("")
        L.append("| Metric | Model | Baseline |")
        L.append("|---|---|---|")
        L.append(f"| Median Spearman rho | {_num(s.get('median_model_spearman'))} | {_num(s.get('median_baseline_spearman'))} |")
        L.append(f"| Median out-of-sample R2 | {_num(s.get('median_model_oos_r2'))} | {_num(s.get('median_baseline_oos_r2'))} |")
        L.append(f"| Median top-quartile hit rate | {_pct(s.get('median_model_hit_rate'))} | {_pct(s.get('median_baseline_hit_rate'))} |")
        L.append("")
        L.append("Paired, per-origin differences (model minus baseline). Unpaired medians")
        L.append("can flatter a model that loses on almost every origin, so these govern.")
        L.append("")
        L.append("| Paired gain | Value |")
        L.append("|---|---|")
        L.append(f"| Median Spearman gain | {_num(s.get('median_paired_rho_gain'), 4)} |")
        L.append(f"| Median out-of-sample R2 gain | {_num(s.get('median_paired_r2_gain'), 4)} |")
        L.append(f"| Median hit-rate gain | {_num(s.get('median_paired_hit_rate_gain'), 4)} |")
        L.append("")
        beat = s.get("origins_beating_baseline", "n/a")
        L.append(f"**Origins where the model beat the baseline: {beat}.**")
        L.append("")
        n_scored = s.get("n_origins_scored") or 0
        try:
            won, tot = (int(x) for x in str(beat).split("/"))
        except Exception:  # noqa: BLE001
            won = tot = 0
        if tot and won <= tot / 2:
            L.append(
                "> Verdict: **NOT CERTIFIED for forward-looking claims.** The multi-feature "
                "model does not reliably beat prior one-year population growth. Under GRIP "
                "rule 8 this model may ship as a descriptive index only. Publishing it as a "
                "forecast would be the failure AIMIP was built to catch."
            )
        elif tot:
            L.append(
                f"> Verdict: **CERTIFIED at horizon {h}** on {won}/{tot} origins. Report the "
                "baseline alongside every forward-looking figure regardless."
            )
        L.append("")

        L.append("### E2/E3 Rolling-origin skill")
        L.append("")
        L.append("Each row is a strictly causal test: fit on origins before the test origin, predict the test origin, never the reverse.")
        L.append("")
        L.append("| Test origin | Metros | Model rho | 90% interval | Baseline rho | Model hit | Baseline hit | Beat baseline |")
        L.append("|---|---|---|---|---|---|---|---|")
        for r in c.get("E2_E3_rolling_origin", []):
            L.append(
                f"| {r['test_origin']} | {r['n_test_metros']} | {_num(r['model_spearman'])} | "
                f"[{_num(r['model_spearman_p05'])}, {_num(r['model_spearman_p95'])}] | "
                f"{_num(r['baseline_spearman'])} | {_pct(r['model_hit_rate'])} | "
                f"{_pct(r['baseline_hit_rate'])} | {'yes' if r['beats_baseline'] else 'no'} |"
            )
        L.append("")

        L.append("### Ensemble and intervals")
        L.append("")
        L.append(
            f"Every origin is scored from a block-bootstrap ensemble over origin years "
            f"(minimum {s.get('ensemble_members_min')} members against a protocol floor of "
            f"{s.get('ensemble_protocol_floor')}). The graded prediction is the ensemble mean."
        )
        L.append("")
        L.append("| Ensemble metric | Value |")
        L.append("|---|---|")
        L.append(f"| Conforms to the member floor | {'yes' if s.get('ensemble_conforms') else 'NO'} |")
        L.append(f"| Share of individual members beating the baseline | {_pct(s.get('member_share_beating_baseline'))} |")
        L.append(f"| Median single-fit Spearman rho, for comparison | {_num(s.get('median_single_fit_spearman'))} |")
        L.append(f"| Median member spread as a share of forecast error | {_num(s.get('median_parameter_spread_to_error_ratio'))} |")
        L.append(f"| Median 90% predictive interval width | {_num(s.get('median_predictive_interval_width_90'), 5)} |")
        L.append(f"| Median realised coverage of that interval | {_pct(s.get('median_predictive_interval_coverage_90'))} |")
        L.append("")
        cov = s.get("median_predictive_interval_coverage_90")
        if cov is not None and 0.85 <= cov <= 0.95:
            L.append(
                f"> The 90% predictive interval is **conforming**: realised coverage "
                f"{_pct(cov)} against a nominal 90%. This interval may be attached to "
                "published figures. Note that it is *wider* than the member spread by "
                "roughly an order of magnitude \u2014 member spread alone captures which model "
                "might have been fitted, not how wrong that model is about a given metro, "
                "and publishing it as a forecast interval would be narrow and wrong."
            )
        elif cov is not None:
            L.append(
                f"> The 90% predictive interval is **non-conforming**: realised coverage "
                f"{_pct(cov)} falls outside [85%, 95%]. It may not be attached to published figures."
            )
        L.append("")
        L.append("| Test origin | Members | Members beating baseline | Member rho range | 90% PI coverage |")
        L.append("|---|---|---|---|---|")
        for r in c.get("E2_E3_rolling_origin", []):
            cvg = r.get("predictive_interval_coverage_90")
            L.append(
                f"| {r['test_origin']} | {r.get('n_members')} | {r.get('members_beating_baseline')} | "
                f"[{_num(r.get('member_spearman_min'))}, {_num(r.get('member_spearman_max'))}] | "
                f"{_pct(cvg) if cvg is not None else 'n/a (first scored origin)'} |"
            )
        L.append("")

        L.append("### CLOCK_LEAK audit")
        L.append("")
        L.append(
            "AIMIP banned CO2 as an input because its steady rise \"could become a proxy for "
            "a clock.\" This is the housing analogue: any feature whose cross-sectional mean "
            "drifts monotonically across origins is dating the sample rather than ranking metros."
        )
        L.append("")
        L.append("| Feature | Drift rho across origins | p | Sign flips | Verdict |")
        L.append("|---|---|---|---|---|")
        for r in c.get("CLOCK_LEAK_audit", []):
            L.append(
                f"| `{r['feature']}` | {_num(r['drift_spearman'])} | {_num(r['p_value'])} | "
                f"{r['sign_flips']} | {r['verdict']} |"
            )
        banned = c.get("features_banned_by_clock_leak") or []
        L.append("")
        shown = ", ".join("`"+b+"`" for b in banned) if banned else "none"
        L.append(f"Features excluded by the audit: {shown}.")
        L.append("")

        L.append("### E4 Coefficient stability")
        L.append("")
        L.append("A feature whose sign flips across origins is not a mechanism, it is a fit artifact.")
        L.append("")
        L.append("| Feature | Mean coef | Min | Max | Share positive | Verdict |")
        L.append("|---|---|---|---|---|---|")
        for r in c.get("E4_coefficient_stability", []):
            L.append(
                f"| `{r['feature']}` | {_num(r['mean_coef'], 5)} | {_num(r['min_coef'], 5)} | "
                f"{_num(r['max_coef'], 5)} | {_pct(r['share_positive'])} | {r['verdict']} |"
            )
        L.append("")

        L.append("### E5 Shock plausibility")
        L.append("")
        L.append(
            "There is no ground truth for a rate or premium shock, so these are graded on "
            "pre-registered sign, exactly as AIMIP grades the +2K/+4K sea-surface experiments. "
            "Wrong sign bars a model from forward-looking claims regardless of its R2."
        )
        L.append("")
        L.append("| Shock | Graded on | Relative response | Expected sign | Observed | Verdict |")
        L.append("|---|---|---|---|---|---|")
        for r in c.get("E5_shocks", []):
            if r.get("status") != "RUN":
                L.append(f"| `{r['shock']}` | - | - | - | - | {r.get('status')} |")
                continue
            L.append(
                f"| `{r['shock']}` | {r.get('graded_on','')} | {_num(r.get('relative_response'), 6)} | "
                f"{r.get('expected_sign')} | {r.get('observed_sign')} | {r.get('verdict')} |"
            )
        L.append("")
        for r in c.get("E5_shocks", []):
            if r.get("verdict") == "IMPLAUSIBLE":
                L.append(f"- **`{r['shock']}` failed.** {r.get('failure_signature','')}")
        L.append("")

        L.append("### Declared deviations")
        L.append("")
        for d in c.get("declared_deviations", []):
            L.append(f"- {d}")
        L.append("")
        L.append("### Vintage-lock checks")
        L.append("")
        for k, v in (c.get("vintage_lock_checks") or {}).items():
            L.append(f"- `{k}`: {'PASS' if v.get('pass') else 'FAIL'} ({v.get('violations')} violations)")
        L.append("")

    L.append("## Attribution")
    L.append("")
    for a in cards[0].get("attribution", []):
        L.append(f"- {a}")
    L.append("")
    L.append(
        "Sources: [FHFA House Price Index](https://www.fhfa.gov/data/hpi), "
        "[Census Population Estimates](https://www.census.gov/programs-surveys/popest.html), "
        "[Census Building Permits Survey](https://www.census.gov/construction/bps/), "
        "[OMB/Census metro delineation files](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html). "
        "Protocol modelled on [AIMIP](https://allenai.org/blog/aimip) "
        "([code](https://github.com/ai2cm/AIMIP), [PCMDI hub](https://github.com/PCMDI/AI-MIP))."
    )
    return "\n".join(L)


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "out"
    paths = [Path(p) for p in sys.argv[1:]] or sorted(out.glob("scorecard_h*.json"))
    seen: dict[int, dict] = {}
    for p in paths:
        c = json.loads(p.read_text())
        h = c["horizon_years"]
        if h not in seen or c["run_started_utc"] > seen[h]["run_started_utc"]:
            seen[h] = c
    cards = [seen[h] for h in sorted(seen)]
    if not cards:
        raise SystemExit("no scorecards found in out/")
    md = render(cards)
    dest = out / "SCORECARD.md"
    dest.write_text(md)
    print(f"wrote {dest} ({len(md)} chars, horizons {[c['horizon_years'] for c in cards]})")


if __name__ == "__main__":
    main()
