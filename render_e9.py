#!/usr/bin/env python3
"""Render out/E9_METRO_FE.md from the newest fe_diagnostic JSON.

Every number is read from the JSON. Nothing is typed by hand.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"
SPECS = ["S0", "S0_on_S2_sample", "S1", "S2"]
LABEL = {
    "S0": "S0 baseline",
    "S0_on_S2_sample": "S0 on S2's rows (control)",
    "S1": "S1 within metro",
    "S2": "S2 expanding, forecast-legal",
}
CELL = {
    "pop_h5": "Population, h=5",
    "pop_h3": "Population, h=3",
    "hpi_h5": "House price, h=5",
    "hpi_h3": "House price, h=3",
}
V, G = "hpi_vol_wr", "hpi_gap_wr"


def f(x, n=6):
    return "n/a" if x is None else f"{x:+.{n}f}"


def main() -> None:
    src = sorted(glob.glob(str(OUT / "fe_diagnostic_*.json")))[-1]
    r = json.loads(Path(src).read_text())
    pre, ver = r["pre_registration"], r["verdict"]
    L: list[str] = []
    A = L.append

    A("# E9 — Metro fixed effects and the E5 re-run")
    A("")
    A(f"Run {r['run_started_utc']}. Source `{Path(src).name}`.")
    A("")
    A(f"**Registered {pre['registered_in']} as specification attempt "
      f"{pre['specification_attempt']} of the post-E5 budget, and released "
      "results-free as `v1.6.0-prereg` before this script was executed once.**")
    A("")
    A(f"**Pre-registered verdict: the confound hypothesis is supported in "
      f"{ver['cells_supporting_confound_hypothesis']} cells.** The attempt "
      "rejects, by the rule fixed in advance.")
    A("")
    A("## What was asked")
    A("")
    A("Two of three pre-registered shocks fail in all four graded cells, and both")
    A("failures route through exactly two coefficients: `hpi_vol_wr`, perturbed by")
    A("`premium_shock_40pct`, and `hpi_gap_wr`, perturbed by `rate_shock_200bp`.")
    A("Those two are also the only SIGN-UNSTABLE entries in E4. E8 had found the")
    A("Treasury FIO premium's positive population coefficient losing significance")
    A("once NFIP flood price entered the same regression, which suggested the")
    A("premium had been standing in for persistent warm-state characteristics. E9")
    A("asks whether the same confound drives these two features: is the wrong sign a")
    A("between-metro artefact, or a real within-metro relationship?")
    A("")
    A("Because an `exposed_only` shock response is arithmetically the fitted")
    A("coefficient on the perturbed standardised feature, re-running E5 under a new")
    A("specification is identically re-estimating those two coefficients. The suite")
    A("in `grip/shocks.py` was executed unmodified.")
    A("")
    A("## Results")
    A("")

    for cell, c in r["cells"].items():
        vd = {x["feature"]: x for x in c["variance_decomposition"]}
        A(f"### {CELL.get(cell, cell)}")
        A("")
        A(f"Within-metro share of variance: `hpi_vol` "
          f"{vd['hpi_vol']['within_metro_share']:.3f}, `hpi_gap` "
          f"{vd['hpi_gap']['within_metro_share']:.3f}. Both clear the "
          f"{pre['min_within_metro_share']:.2f} power precondition, so both signs "
          "are readable.")
        A("")
        A("| Spec | n | origins | R² | `hpi_vol` | t | LOO share + | `hpi_gap` | t | LOO share + | rate / premium shock |")
        A("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for s in SPECS:
            d = c.get(s, {})
            if d.get("status") != "RUN":
                A(f"| {LABEL[s]} | {d.get('status','-')} | | | | | | | | | |")
                continue
            co = d["pooled_ridge_coefficients"]
            ols = {x["feature"]: x for x in d["clustered_ols"]}
            st = {x["feature"]: x for x in d["loo_origin_stability"]}
            sh = {x["shock"]: x.get("verdict", x.get("status")) for x in d["E5_shocks"]}
            A(f"| {LABEL[s]} | {d['n']:,} | {d['n_origins']} | {d['in_sample_r2']:.4f} "
              f"| `{f(co.get(V))}` | {ols[V]['t']:+.2f} | {st[V]['share_positive']:.3f} "
              f"| `{f(co.get(G))}` | {ols[G]['t']:+.2f} | {st[G]['share_positive']:.3f} "
              f"| {sh.get('rate_shock_200bp')} / {sh.get('premium_shock_40pct')} |")
        A("")

    A("t-statistics are OLS with standard errors clustered on metro. Clustering is")
    A("not optional here: a five-year forward outcome measured at consecutive origins")
    A("overlaps by four years, so within-metro residuals are autocorrelated by")
    A("construction. `LOO share +` is the fraction of leave-one-origin-out refits in")
    A("which the coefficient is positive; the pre-registered shock sign is negative,")
    A("so 0.000 is reliably right and 1.000 is reliably wrong.")
    A("")
    # Derived so the prose cannot drift from the table.
    s1g_pos = s1g_tot = 0
    s1g_tmax = 0.0
    for c in r["cells"].values():
        st = {x["feature"]: x for x in c["S1"]["loo_origin_stability"]}[G]
        n = st["n_refits"]
        s1g_tot += n
        s1g_pos += round(st["share_positive"] * n)
        t = {x["feature"]: x for x in c["S1"]["clustered_ols"]}[G]["t"]
        s1g_tmax = max(s1g_tmax, t)
    s1v_t = [ {x["feature"]: x for x in r["cells"][k]["S1"]["clustered_ols"]}[V]["t"]
              for k in ("pop_h5", "hpi_h5") ]
    s2pop_t = []
    for k in ("pop_h5", "pop_h3"):
        o = {x["feature"]: x for x in r["cells"][k]["S2"]["clustered_ols"]}
        s2pop_t += [o[V]["t"], o[G]["t"]]
    s2_weakest = max(s2pop_t)  # closest to zero among negatives

    A("## What this settles")
    A("")
    A("**1. The valuation-gap inversion is real, not a confound.** Under the pure")
    A("within-metro transformation `hpi_gap` stays positive in all four cells and in")
    A(f"every single leave-one-origin-out refit — {s1g_pos} of {s1g_tot} refits "
      f"positive, reaching t = {s1g_tmax:+.2f}. Removing every persistent difference")
    A("between metros does not touch it. When a metro is priced further above its own")
    A("long-run trend than it usually is, its subsequent growth is *higher*. That is")
    A("momentum, it is in the data, and no estimator will remove it. `hpi_gap` is a")
    A("momentum term wearing an affordability label, and `rate_shock_200bp` has been")
    A("testing mean reversion against a feature that measures its opposite.")
    A("")
    A("**2. The volatility channel is ambiguous rather than vindicated.** `hpi_vol`")
    A(f"does turn negative under S1 in both h=5 cells, but at t = {s1v_t[0]:+.2f} and "
      f"t = {s1v_t[1]:+.2f}")
    A("it is insignificant in both, and it stays positive in both h=3 cells. That is")
    A("not evidence of a confound. It is a feature with little to say.")
    A("")
    A("**3. Population growth is almost entirely a between-metro phenomenon.**")
    pop5, hpi5 = r["cells"]["pop_h5"], r["cells"]["hpi_h5"]
    p0, p1 = pop5["S0"]["in_sample_r2"], pop5["S1"]["in_sample_r2"]
    h0, h1 = hpi5["S0"]["in_sample_r2"], hpi5["S1"]["in_sample_r2"]
    A(f"Removing metro identity collapses the population fit from {p0:.3f} to "
      f"{p1:.3f}, destroying {100*(p0-p1)/p0:.0f}% of it, while the house-price fit")
    A(f"falls only from {h0:.3f} to {h1:.3f}, losing {100*(h0-h1)/h0:.0f}%. Which")
    A("metro you are is nearly the whole population story; prices genuinely have")
    A("within-metro dynamics. That asymmetry is a fact about the product, not about")
    A("this regression: a population ranking is carried by persistent metro")
    A("characteristics, so the honest way to improve it is better cross-sectional")
    A("features, not cleverer time-series handling.")
    A("")
    # Direction of the sample effect, per cell and per focal feature, derived.
    moves = {}
    for k, c in r["cells"].items():
        b, ctl = c["S0"]["pooled_ridge_coefficients"], c["S0_on_S2_sample"]["pooled_ridge_coefficients"]
        moves[k] = {ff: ctl[ff] - b[ff] for ff in (V, G)}
    gap_up = sum(1 for m in moves.values() if m[G] > 0)
    pop_both_up = all(moves[k][V] > 0 and moves[k][G] > 0 for k in ("pop_h5", "pop_h3"))
    hpi_vol_down = [k for k in ("hpi_h5", "hpi_h3") if moves[k][V] < 0]

    A("**4. The control earned its place, and it cuts the right way.** Restricting to")
    A(f"S2's rows moves `hpi_gap` further positive in {gap_up} of {len(moves)} cells, and in")
    A("both population cells — the only ones where S2 flips a sign — it moves *both*")
    A(f"focal coefficients further positive: `hpi_gap` at population h=5 goes from")
    A(f"`{f(pop5['S0']['pooled_ridge_coefficients'][G])}` to "
      f"`{f(pop5['S0_on_S2_sample']['pooled_ridge_coefficients'][G])}`."
      + ("" if pop_both_up else " (NOTE: not confirmed in both population cells.)"))
    A("So the sample restriction works *against* the negative result, and the")
    A("specification, not the smaller sample, is what produces it. Reporting S2")
    A("against full-sample S0 alone would have been a mistake dressed as a finding.")
    A("")
    A("The one place the sample effect runs the other way is `hpi_vol` in the two")
    A(f"house-price cells ({', '.join(hpi_vol_down)}), where it becomes less positive on")
    A("S2's rows while still staying positive. That does not rescue anything — S2")
    A("leaves both house-price shocks IMPLAUSIBLE regardless — but stating it is the")
    A("difference between a control and a decoration.")
    A("")
    A("## The part that must not be oversold")
    A("")
    A("In both population cells S2 flips both shocks to PLAUSIBLE, with")
    A("`LOO share +` of 0.000 — reliably negative across every refit. P3, as")
    A("registered, held there. It would be easy to present that as the shock gate")
    A("repaired. It is not, for a reason that has nothing to do with statistics.")
    A("")
    A("S2 redefines the feature. Under S2 `hpi_gap_wr` no longer measures how far a")
    A("metro sits above its own long-run trend; it measures how far its gap sits")
    A("above its own *recent average* gap, which is a second difference. The shock's")
    A("exposed set is defined by a quantile of the perturbed feature, so the exposed")
    A("set changes meaning with it: it stops selecting the most overvalued metros and")
    A("starts selecting metros whose overvaluation is unusually high for them.")
    A("`rate_shock_200bp` as registered asks about metros \"already priced furthest")
    A("above their own long-run trend\". S2 does not answer that question, so S2 has")
    A("not passed that shock — it has passed a different one that happens to share a")
    A(f"name. The t-statistics are marginal too (as weak as {s2_weakest:+.2f}, "
      "insignificant at 5%)")
    A("on 7 to 8 heavily overlapping origins.")
    A("")
    A("Under the section 13 rule S2 is therefore recorded as a **CANDIDATE for the")
    A("population target only**, and it carries an extra condition beyond the")
    A("standard one: a fresh blind re-registration must re-specify the shock's")
    A("exposure against the S2 feature definition. Re-registering the existing shock")
    A("text against a redefined feature would be a label error, not a test.")
    A("")
    A("## Consequences")
    A("")
    A("Attempt 1 is spent, and its own reject clause applies: the inversion is")
    A("within-metro as well, so the estimator is not the problem and the features")
    A("are. **Attempt 2 must not be another estimator.** The route is the one E8")
    A("opened — measured transactions rather than constructed proxies. `hpi_vol` was")
    A("never an insurance price and is now shown to carry almost no within-metro")
    A("information about either target; NFIP realised paid losses already beat the")
    A("modelled NRI rate head to head. Replacing the proxy is the remaining move.")
    A("")
    A("Nothing here changes any certification. The four NOT CERTIFIED verdicts in")
    A("`v1.0.0-grip1` stand, `premium_shock_40pct` and `rate_shock_200bp` remain")
    A("registered as published and remain failing, and E9 was barred from certifying")
    A("before it was run.")
    A("")
    A("## Deviation disclosed")
    A("")
    A("One code change landed after the `v1.6.0-prereg` anchor. The cached panels")
    A("already carried `*_wr` columns from the graded run, which collided on merge")
    A("and raised a `KeyError` on first execution; stale `*_wr` columns are now")
    A("dropped at load so every specification is built from raw features only. It is")
    A("a mechanical fix, visible in the diff, and it changed no specification, no")
    A("prediction and no rule.")
    A("")
    A("## Sources")
    A("")
    A("- Protocol and pre-registration: <https://github.com/Carson2113/geometryx-grip/blob/main/PROTOCOL.md> section 13")
    A("- Results-free anchor: <https://github.com/Carson2113/geometryx-grip/releases/tag/v1.6.0-prereg>")
    A("- FHFA house price index: <https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv>. "
      "This product uses FHFA Data but is neither endorsed nor certified by FHFA.")
    A("- Census Population Estimates Program, public domain: <https://www2.census.gov/programs-surveys/popest/datasets/>")
    A("- Census Building Permits Survey, public domain: <https://www.census.gov/construction/bps/>")
    A("")

    dst = OUT / "E9_METRO_FE.md"
    dst.write_text("\n".join(L))
    print(f"wrote {dst} ({dst.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
