"""OpenFEMA National Flood Insurance Program adapters.

Two distinct series, with very different vintage properties. Read
``VINTAGE_VERDICT`` before using either as a graded predictor.

``NfipClaims`` v3 -- 2,724,656 paid flood-loss records, ``temporal`` 1970-08-31
onward, carrying a 5-digit county FIPS in ``countyCode`` and a ``yearOfLoss``.
Each row is a settled insurance transaction: a dollar figure fixed at the date
of loss and not restated by later publication. This is the deepest-history
actual-cost series available anywhere in public-domain federal data, and it is
the reason this module exists.

``NfipPolicies`` v3 -- 74,349,525 policy records, ``temporal`` 2009-01-01
onward, carrying ``totalInsurancePremiumOfThePolicy`` and
``fullRiskPremium``. This is a transacted *price*, which claims are not. It has
no county field: geography is ``reportedZipCode``, so it must be routed through
the Census ZCTA-to-county crosswalk. It cannot be paged in full -- see
``PAGING_LIMIT`` -- so it is sampled within (state, year) partitions.

Publication and availability facts recorded 2026-08-23 against
https://www.fema.gov/api/open/v1/DataSets.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from grip import fetch
from grip.sources import cbsa as cbsa_src
from grip.sources import pep as pep_src

API = "https://www.fema.gov/api/open"
CATALOGUE = f"{API}/v1/DataSets"
CLAIMS = f"{API}/v3/NfipClaims"
POLICIES = f"{API}/v3/NfipPolicies"

CACHE = Path(__file__).resolve().parents[2] / "cache" / "nfip"

UA = {"User-Agent": "geometryx-grip/1.5 (+https://github.com/Carson2113/geometryx-grip)"}

# ---------------------------------------------------------------------------
# Provenance, verified 2026-08-23 against the OpenFEMA catalogue endpoint.
# ---------------------------------------------------------------------------

DATASETS = {
    "NfipClaims": {
        "version": 3,
        "record_count": 2_724_656,
        "temporal_start": "1970-08-31",
        "issued": "2019-06-01",
        "last_refresh": "2026-07-27",
        "accrual": "R/P1M",
        "geography": "countyCode (5-digit FIPS) and reportedZipCode",
        "landing": "https://www.fema.gov/openfema-data-page/fima-nfip-redacted-claims-v3",
    },
    "NfipPolicies": {
        "version": 3,
        "record_count": 74_349_525,
        "temporal_start": "2009-01-01",
        "issued": "2019-06-01",
        "last_refresh": "2026-07-27",
        "accrual": "R/P1M",
        "geography": "reportedZipCode only -- no county field",
        "landing": "https://www.fema.gov/openfema-data-page/nfip-redacted-policies-v3",
    },
}

# FimaNfipPolicies v2 / FimaNfipClaims v2 are the superseded names. v2 is
# deprecated: frozen 2026-06-01, removal 2026-10-15. Do not use them.
DEPRECATED = ("FimaNfipPolicies v2", "FimaNfipClaims v2")

PAGING_LIMIT = (
    "The policy endpoint degrades non-linearly in $skip and fails outright deep "
    "in the file: $skip=0 returns in 0.65s, $skip=100000 in 1.77s, "
    "$skip=5000000 in 21.6s, and $skip=40000000 returns HTTP 503. The advertised "
    "bulk CSV and parquet distributions both return HTTP 403 to this network. A "
    "complete 74.3M-row pull is therefore not available by any route, and the "
    "premium series is built by systematic sampling inside (state, year) "
    "partitions where $skip stays small. Claims, at 2.7M rows, are pulled "
    "complete with no sampling."
)

# ---------------------------------------------------------------------------
# The vintage question. This is the load-bearing part of the module.
# ---------------------------------------------------------------------------

VINTAGE_VERDICT = {
    "graded_predictor_eligible": False,
    "class": "B -- contemporaneous fact, later publication, no restatement",
    "grounds": [
        "PUBLICATION. Both datasets carry issued = 2019-06-01. Under the "
        "minimum-history rule as written in PROTOCOL section 4 (published in "
        "v1.4.0-grip1), a feature first published in year P serves no origin "
        "before P+1, so 2019 publication means the first legal origin is 2020. "
        "That is 1 of 11 graded origins at h=5 and 3 of 13 at h=3. Both fail.",
        "COVERAGE, policies only. NfipPolicies temporal coverage begins "
        "2009-01-01, so no premium feature requiring a pre-2009 lag window can "
        "be constructed at all. Claims are unaffected: coverage begins "
        "1970-08-31 and every lag window in the panel is available.",
    ],
    "correction": (
        "This module corrects a claim made in the v1.4.0-grip1 release notes, "
        "which described NfipPolicies as having 'genuine pre-2009 history'. It "
        "does not. The OpenFEMA catalogue reports temporal coverage of "
        "2009-01-01 onward. The claims file, not the policy file, is the "
        "long-history series, and it is a loss cost rather than a price."
    ),
    "why_it_is_not_the_same_failure_as_nri_and_fio": (
        "NRI's expected annual loss is a model output: the 2025 release embeds "
        "2025 hazard science, so its value at any historical date is a "
        "retrospective construct. The FIO workbook is a period aggregate "
        "computed once over 2018-2022. Neither number existed, in any form, at "
        "the origins it would have to serve. An NFIP paid claim is different in "
        "kind: a dollar amount settled on a dated loss and never restated. The "
        "hazard is availability, not hindsight in the value. That distinction is "
        "proposed as a formal source taxonomy in PROTOCOL section 4, and it is "
        "deliberately drawn so that it does NOT rescue NRI or FIO."
    ),
}

DEVIATIONS = [
    "OpenFEMA publishes no as-of-origin vintage archive for either file. Both "
    "are current snapshots refreshed monthly; the retrieval date and asOfDate "
    "are recorded in place of a release hash.",
    "The bulk CSV and parquet distributions return HTTP 403, and the API cannot "
    "be paged past roughly 5 million rows, so the premium series is a "
    "systematic sample within (state, year) partitions rather than a census. "
    "Sample sizes per metro-year are reported alongside every estimate.",
    "NfipPolicies has no county identifier. Metro assignment routes through the "
    "Census 2020 ZCTA-to-county relationship file, which introduces the same "
    "ZIP-to-county ambiguity already declared for the FIO adapter.",
    "Claims are reported at the county of the insured property, but the paid "
    "amount reflects the policy limits in force, so a county-year loss cost is "
    "censored above by coverage limits. It is a lower bound on gross flood loss.",
    "NFIP premiums are federally set, not market-rated, and until the phased "
    "introduction of Risk Rating 2.0 from October 2021 they were substantially "
    "cross-subsidised. The premium series measures a regulated price, and its "
    "level is not comparable to the FIO market homeowners premium.",
    "Flood is a single peril. Neither series speaks to wind, wildfire or the "
    "multi-peril homeowners cost that E6 measured.",
]

CLAIM_FIELDS = (
    "yearOfLoss",
    "state",
    "countyCode",
    "amountPaidOnBuildingClaim",
    "amountPaidOnContentsClaim",
    "amountPaidOnIncreasedCostOfComplianceClaim",
    "totalBuildingInsuranceCoverage",
    "totalContentsInsuranceCoverage",
)

POLICY_FIELDS = (
    "policyEffectiveDate",
    "propertyState",
    "reportedZipCode",
    "totalInsurancePremiumOfThePolicy",
    "totalBuildingInsuranceCoverage",
    "totalContentsInsuranceCoverage",
    "policyCost",
)

STATES = (
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"
).split()


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------


def _url(base: str, params: dict[str, str]) -> str:
    return base + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def _get_json(url: str, timeout: int = 300, tries: int = 4) -> dict:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"OpenFEMA request failed after {tries} tries: {url}") from last


def count(base: str, where: str | None = None) -> int:
    p = {"$top": "1", "$inlinecount": "allpages", "$select": "id"}
    if where:
        p["$filter"] = where
    return int(_get_json(_url(base, p))["metadata"]["count"])


def _entity(base: str) -> str:
    return base.rsplit("/", 1)[-1]


def _page(base: str, fields: tuple[str, ...], top: int, skip: int,
          where: str | None = None) -> list[dict]:
    p = {"$select": ",".join(fields), "$top": str(top), "$skip": str(skip),
         "$orderby": "id"}
    if where:
        p["$filter"] = where
    return _get_json(_url(base, p)).get(_entity(base), [])


# ---------------------------------------------------------------------------
# Claims -- complete census, 1970 onward
# ---------------------------------------------------------------------------


def claims_raw(refresh: bool = False, page: int = 5000, workers: int = 4) -> pd.DataFrame:
    """Every paid NFIP claim, 1970 onward. Cached as parquet."""
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / "nfip_claims.parquet"
    if dest.exists() and not refresh:
        return pd.read_parquet(dest)

    total = count(CLAIMS)
    skips = list(range(0, total, page))
    print(f"[nfip] claims: {total:,} rows in {len(skips)} pages of {page}")

    def one(sk: int) -> list[dict]:
        return _page(CLAIMS, CLAIM_FIELDS, page, sk)

    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, chunk in enumerate(ex.map(one, skips)):
            rows.extend(chunk)
            if i % 50 == 0:
                print(f"[nfip]   page {i}/{len(skips)}  rows={len(rows):,}", flush=True)

    df = pd.DataFrame(rows)
    for c in ("amountPaidOnBuildingClaim", "amountPaidOnContentsClaim",
              "amountPaidOnIncreasedCostOfComplianceClaim",
              "totalBuildingInsuranceCoverage", "totalContentsInsuranceCoverage"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["yearOfLoss"] = pd.to_numeric(df["yearOfLoss"], errors="coerce").astype("Int64")
    df["countyCode"] = df["countyCode"].astype("string").str.zfill(5)
    df.to_parquet(dest, index=False)
    print(f"[nfip] cached {len(df):,} claims -> {dest}")
    return df


def county_loss(refresh: bool = False) -> pd.DataFrame:
    """County-year flood loss experience.

    Columns: fips, year, paid, n_claims, coverage_exposed.
    ``paid`` sums building, contents and ICC payments.
    """
    df = claims_raw(refresh=refresh)
    df = df[df["countyCode"].notna() & df["yearOfLoss"].notna()].copy()
    df["paid"] = (
        df["amountPaidOnBuildingClaim"].fillna(0)
        + df["amountPaidOnContentsClaim"].fillna(0)
        + df["amountPaidOnIncreasedCostOfComplianceClaim"].fillna(0)
    )
    df["coverage"] = (
        df["totalBuildingInsuranceCoverage"].fillna(0)
        + df["totalContentsInsuranceCoverage"].fillna(0)
    )
    g = (
        df.groupby(["countyCode", "yearOfLoss"], as_index=False)
        .agg(paid=("paid", "sum"), n_claims=("paid", "size"),
             coverage_exposed=("coverage", "sum"))
        .rename(columns={"countyCode": "fips", "yearOfLoss": "year"})
    )
    g["year"] = g["year"].astype(int)
    return g


def metro_loss_history(base_year: int, window: int = 20,
                       delineation_vintage: int = 2020,
                       loss_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Metro flood-loss experience over the ``window`` years ending ``base_year``.

    Every value uses only losses dated at or before ``base_year``, so the
    feature is computable at an origin of ``base_year + 1``.

    Columns: cbsa_code, nfip_loss_total, nfip_loss_rate, nfip_loss_rate_log,
    nfip_claim_years, nfip_n_claims, n_counties.
    """
    lo = county_loss() if loss_df is None else loss_df
    lo = lo[(lo["year"] <= base_year) & (lo["year"] > base_year - window)]

    cw = cbsa_src.crosswalk(delineation_vintage)[["fips", "cbsa_code"]]
    m = lo.merge(cw, on="fips", how="inner")
    if m.empty:
        return pd.DataFrame()

    agg = m.groupby("cbsa_code", as_index=False).agg(
        nfip_loss_total=("paid", "sum"),
        nfip_n_claims=("n_claims", "sum"),
        coverage_exposed=("coverage_exposed", "sum"),
        nfip_claim_years=("year", "nunique"),
    )
    counties = (
        m.groupby("cbsa_code")["fips"].nunique().rename("n_counties").reset_index()
    )
    agg = agg.merge(counties, on="cbsa_code", how="left")

    # Severity, conditional on a claim being filed: the share of exposed limits
    # actually paid out. NOT a loss ratio -- the denominator covers only
    # policies that claimed, because the total insured value of the metro is not
    # obtainable without a census of the 74M-row policy file.
    agg["nfip_severity_ratio"] = np.where(
        agg["coverage_exposed"] > 0,
        agg["nfip_loss_total"] / agg["coverage_exposed"],
        np.nan,
    )
    agg["nfip_loss_per_claim"] = np.where(
        agg["nfip_n_claims"] > 0, agg["nfip_loss_total"] / agg["nfip_n_claims"], np.nan
    )

    # Loss burden per resident per year, which combines claim frequency and
    # severity and is comparable across metros of different size. Population is
    # taken at base_year, so nothing after the origin enters.
    pop = pep_src.truth_population()
    pop = pop[pop["year"] == min(base_year, int(pop["year"].max()))]
    pop = pop.merge(cw, on="fips", how="inner")
    mpop = pop.groupby("cbsa_code", as_index=False)["pop"].sum().rename(
        columns={"pop": "metro_pop"}
    )
    agg = agg.merge(mpop, on="cbsa_code", how="left")
    agg["nfip_loss_pc_yr"] = np.where(
        agg["metro_pop"] > 0,
        agg["nfip_loss_total"] / agg["metro_pop"] / window,
        np.nan,
    )
    agg["nfip_loss_pc_log"] = np.log(
        agg["nfip_loss_pc_yr"].where(agg["nfip_loss_pc_yr"] > 0)
    )
    agg["nfip_claims_per_10k_yr"] = np.where(
        agg["metro_pop"] > 0,
        1e4 * agg["nfip_n_claims"] / agg["metro_pop"] / window,
        np.nan,
    )
    agg["base_year"] = base_year
    agg["window_years"] = window
    return agg


# ---------------------------------------------------------------------------
# Policies -- sampled premium, 2009 onward
# ---------------------------------------------------------------------------


def _policy_where(state: str, year: int, month: int | None = None) -> str:
    if month is None:
        lo, hi = f"{year}-01-01", f"{year + 1}-01-01"
    else:
        lo = f"{year}-{month:02d}-01"
        hi = f"{year}-{month + 1:02d}-01" if month < 12 else f"{year + 1}-01-01"
    return (
        f"propertyState eq '{state}' and "
        f"policyEffectiveDate ge '{lo}' and policyEffectiveDate lt '{hi}'"
    )


# Skip offsets drawn inside each (state, month) partition. Counting a large
# filtered partition times out on the API -- FL, LA, NC and OH all return HTTP
# 503 to a filtered $inlinecount for a full year -- so the sample is drawn
# blind at fixed geometric offsets and offsets past the end of a partition
# simply return nothing. Offsets stay under 25,000, well inside the range where
# $skip is cheap.
SKIPS = (0, 2_500, 7_500, 20_000)


def policies_sample(year: int, page: int = 1000, workers: int = 8,
                    refresh: bool = False) -> pd.DataFrame:
    """Stratified sample of policies effective in ``year``.

    Strata are (state, calendar month), 612 of them, with ``SKIPS`` offsets
    drawn inside each. Stratifying by month matters: the API returns a
    partition ordered by effective date, so drawing only the head of a
    state-year would return almost nothing but policies effective on 1 January.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f"nfip_policies_{year}_stratified.parquet"
    if dest.exists() and not refresh:
        return pd.read_parquet(dest)

    jobs = [(st, mo, sk) for st in STATES for mo in range(1, 13) for sk in SKIPS]
    print(f"[nfip] policies {year}: drawing {len(jobs)} pages of {page} "
          f"across {len(STATES)}x12 strata")

    def one(job: tuple[str, int, int]) -> list[dict]:
        st, mo, sk = job
        try:
            return _page(POLICIES, POLICY_FIELDS, page, sk, _policy_where(st, year, mo))
        except RuntimeError:
            return []

    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, chunk in enumerate(ex.map(one, jobs)):
            rows.extend(chunk)
            if i % 200 == 0:
                print(f"[nfip]   page {i}/{len(jobs)}  rows={len(rows):,}", flush=True)

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(f"no policy rows retrieved for {year}")
    df = df.drop_duplicates()
    for c in ("totalInsurancePremiumOfThePolicy", "totalBuildingInsuranceCoverage",
              "totalContentsInsuranceCoverage", "policyCost"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["reportedZipCode"] = df["reportedZipCode"].astype("string").str.zfill(5)
    df.to_parquet(dest, index=False)
    print(f"[nfip] cached {len(df):,} sampled policies -> {dest}")
    return df


def _zcta_county() -> pd.DataFrame:
    """Census 2020 ZCTA-to-county relationship file, as used by the FIO adapter."""
    url = ("https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
           "tab20_zcta520_county20_natl.txt")
    raw = fetch.get(url, name="tab20_zcta520_county20_natl.txt")
    df = pd.read_csv(raw, sep="|", dtype=str, encoding="utf-8-sig")
    zc = next(c for c in df.columns if c.startswith("GEOID_ZCTA5"))
    ct = next(c for c in df.columns if c.startswith("GEOID_COUNTY"))
    land = next((c for c in df.columns if c.startswith("AREALAND_PART")), None)
    out = df[[zc, ct] + ([land] if land else [])].copy()
    out.columns = ["zip", "fips"] + (["area"] if land else [])
    out["area"] = pd.to_numeric(out["area"], errors="coerce") if land else 1.0
    # Assign each ZCTA to the county holding most of its land area.
    out = out.sort_values("area", ascending=False).drop_duplicates("zip")
    return out[["zip", "fips"]]


def metro_premium(year: int, delineation_vintage: int = 2020,
                  min_policies: int = 100, **kw) -> pd.DataFrame:
    """Metro average NFIP premium for policies effective in ``year``.

    Columns: cbsa_code, nfip_premium, nfip_premium_log, nfip_rate_per_1k,
    nfip_n_policies, n_counties.
    """
    pol = policies_sample(year, **kw)
    pol = pol[pol["totalInsurancePremiumOfThePolicy"].notna()]
    pol = pol[pol["totalInsurancePremiumOfThePolicy"] > 0]

    z = _zcta_county()
    cw = cbsa_src.crosswalk(delineation_vintage)[["fips", "cbsa_code"]]
    m = pol.merge(z, left_on="reportedZipCode", right_on="zip", how="inner")
    m = m.merge(cw, on="fips", how="inner")
    if m.empty:
        return pd.DataFrame()

    agg = m.groupby("cbsa_code", as_index=False).agg(
        nfip_premium=("totalInsurancePremiumOfThePolicy", "mean"),
        nfip_premium_median=("totalInsurancePremiumOfThePolicy", "median"),
        nfip_coverage=("totalBuildingInsuranceCoverage", "mean"),
        nfip_n_policies=("totalInsurancePremiumOfThePolicy", "size"),
    )
    counties = m.groupby("cbsa_code")["fips"].nunique().rename("n_counties").reset_index()
    agg = agg.merge(counties, on="cbsa_code", how="left")
    agg = agg[agg["nfip_n_policies"] >= min_policies].copy()

    # Rate per $1,000 of building coverage: removes the coverage-amount
    # composition effect that dominates raw average premium.
    agg["nfip_rate_per_1k"] = np.where(
        agg["nfip_coverage"] > 0, 1000 * agg["nfip_premium"] / agg["nfip_coverage"], np.nan
    )
    agg["nfip_premium_log"] = np.log(agg["nfip_premium"])
    agg["nfip_rate_log"] = np.log(agg["nfip_rate_per_1k"].where(agg["nfip_rate_per_1k"] > 0))
    agg["policy_year"] = year
    return agg


def coverage_report() -> dict:
    """Availability and provenance summary for the scorecard."""
    return {
        "datasets": DATASETS,
        "deprecated": list(DEPRECATED),
        "paging_limit": PAGING_LIMIT,
        "vintage_verdict": VINTAGE_VERDICT,
        "declared_deviations": DEVIATIONS,
        "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
