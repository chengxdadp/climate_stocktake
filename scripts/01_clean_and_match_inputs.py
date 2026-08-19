"""Clean the course data and match coalition countries to the CPI workbook.

Inputs are never modified.  All machine-readable derivatives are written to
``group project/output`` so later scripts can be rerun independently.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
ASSET_DIR = PROJECT_DIR / "asset"
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILE = ASSET_DIR / "raw.csv"
CPI_FILE = ASSET_DIR / "2025_CPI_Bottom-up_Needs_Download.xlsx"

SCENARIOS = {
    "74-country LDC+AOSIS coalition": ASSET_DIR / "country list 2.txt",
    "20-country selected coalition": ASSET_DIR / "list of country.txt",
}

# Course/raw.csv names on the left; CPI NDC compilation names on the right.
CPI_NAME_ALIASES = {
    "Cape Verde": "Cabo Verde",
    "Democratic Republic of Congo": "Congo, Democratic Republic",
    "East Timor": "Timor-Leste",
    "Laos": "Lao People's Democratic Republic",
    "Micronesia (country)": "Micronesia (Federated States of)",
    "Tanzania": "United Republic of Tanzania",
}

LOAN_NAME_ALIASES = {
    "St. Lucia": "Saint Lucia",
    "St. Vincent and the Grenadines": "Saint Vincent and the Grenadines",
}


def read_name_list(path: Path) -> list[str]:
    """Read a one-country-per-line UTF-8 text file, preserving order."""
    names = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()]
    names = [name for name in names if name]
    if len(names) != len(set(names)):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise ValueError(f"Duplicate names in {path.name}: {duplicates}")
    return names


def parse_numeric(series: pd.Series) -> pd.Series:
    """Convert comma-formatted numeric text to floats without changing blanks."""
    return pd.to_numeric(
        series.astype("string").str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def safe_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def main() -> None:
    raw = pd.read_csv(RAW_FILE, dtype="string")
    required = {
        "Country",
        "ISO",
        "Bloc",
        "Population 2024",
        "GDP 2022 (int'l $)",
        "CO2 2024 (Mt)",
        "Cumulative CO2 (Mt)",
    }
    missing_columns = required - set(raw.columns)
    if missing_columns:
        raise ValueError(f"raw.csv is missing required columns: {sorted(missing_columns)}")

    numeric_columns = [
        "Population 2024",
        "GDP 2022 (int'l $)",
        "CO2 2024 (Mt)",
        "Cumulative CO2 (Mt)",
    ]
    for column in numeric_columns:
        raw[column] = parse_numeric(raw[column])

    if raw["Country"].duplicated().any():
        duplicates = raw.loc[raw["Country"].duplicated(), "Country"].tolist()
        raise ValueError(f"Duplicate country rows in raw.csv: {duplicates}")

    raw_country_set = set(raw["Country"])
    membership_rows: list[dict[str, object]] = []
    for scenario, path in SCENARIOS.items():
        names = read_name_list(path)
        missing = sorted(set(names) - raw_country_set)
        if missing:
            raise ValueError(f"{path.name} contains countries absent from raw.csv: {missing}")
        for country in names:
            membership_rows.append(
                {
                    "scenario": scenario,
                    "country": country,
                    "scenario_slug": safe_slug(scenario),
                }
            )

    membership = pd.DataFrame(membership_rows)
    roster_counts = membership.groupby("scenario")["country"].nunique().to_dict()
    expected_counts = {
        "74-country LDC+AOSIS coalition": 74,
        "20-country selected coalition": 20,
    }
    if roster_counts != expected_counts:
        raise ValueError(f"Unexpected coalition sizes: {roster_counts}")

    loan_names_raw = read_name_list(ASSET_DIR / "loan country.txt")
    loan_names = {LOAN_NAME_ALIASES.get(name, name) for name in loan_names_raw}
    missing_loan = sorted(loan_names - raw_country_set)
    if missing_loan:
        raise ValueError(f"Loan-country aliases still unmatched in raw.csv: {missing_loan}")

    raw["loan_eligible"] = raw["Country"].isin(loan_names)
    for scenario in SCENARIOS:
        members = set(membership.loc[membership["scenario"] == scenario, "country"])
        raw[f"member_{safe_slug(scenario)}"] = raw["Country"].isin(members)

    raw = raw.rename(
        columns={
            "Country": "country",
            "ISO": "iso3",
            "Bloc": "original_bloc",
            "Population 2024": "population_2024",
            "GDP 2022 (int'l $)": "gdp_2022_ppp_2011_intl_usd",
            "CO2 2024 (Mt)": "co2_2024_mt",
            "Cumulative CO2 (Mt)": "cumulative_co2_through_2024_mt",
        }
    )
    raw["co2_per_capita_2024_t"] = (
        raw["co2_2024_mt"] * 1_000_000 / raw["population_2024"]
    )
    raw["cumulative_co2_per_capita_t"] = (
        raw["cumulative_co2_through_2024_mt"] * 1_000_000 / raw["population_2024"]
    )
    raw["gdp_per_capita_2022_ppp_2011_intl_usd"] = (
        raw["gdp_2022_ppp_2011_intl_usd"] / raw["population_2024"]
    )

    scope = pd.read_excel(CPI_FILE, sheet_name="1-Bottom-up-needs-scope")
    theme = pd.read_excel(CPI_FILE, sheet_name="2-Bottom-up-needs-theme")
    conditionality = pd.read_excel(CPI_FILE, sheet_name="4-Bottom-up-needs-conditionalit")

    # Use the 2024-2035 column because the simulated stocktake concerns 2035.
    adaptation = theme.loc[
        (theme["Theme"] == "Adaptation")
        & (theme["Temporality"] == "Needs-24-35"),
        ["Country", "Value"],
    ].rename(
        columns={
            "Country": "cpi_country",
            "Value": "adaptation_need_2024_2035_usd_bn",
        }
    )
    adaptation["adaptation_need_2024_2035_usd_bn"] = pd.to_numeric(
        adaptation["adaptation_need_2024_2035_usd_bn"], errors="coerce"
    )

    cond = conditionality.loc[
        conditionality["Temporality"] == "Needs-24-35",
        ["Country", "Conditionality", "Cumulative needs (USD bn)"],
    ].copy()
    cond["Cumulative needs (USD bn)"] = pd.to_numeric(
        cond["Cumulative needs (USD bn)"], errors="coerce"
    )
    cond_pivot = cond.pivot_table(
        index="Country",
        columns="Conditionality",
        values="Cumulative needs (USD bn)",
        aggfunc="sum",
        dropna=False,
    ).reset_index()
    cond_pivot = cond_pivot.rename(
        columns={
            "Country": "cpi_country",
            "Conditional": "conditional_need_all_objectives_usd_bn",
            "Unconditional": "unconditional_need_all_objectives_usd_bn",
            "Unspecified": "unspecified_need_all_objectives_usd_bn",
        }
    )
    for column in [
        "conditional_need_all_objectives_usd_bn",
        "unconditional_need_all_objectives_usd_bn",
        "unspecified_need_all_objectives_usd_bn",
    ]:
        if column not in cond_pivot:
            cond_pivot[column] = np.nan

    scope_columns = scope[
        [
            "Country",
            "Needs quantified (yes/no)",
            "Data coverage",
            "Thematic Coverage",
            "NDC publication year",
            "Hyperlink",
        ]
    ].rename(
        columns={
            "Country": "cpi_country",
            "Needs quantified (yes/no)": "cpi_needs_quantified",
            "Data coverage": "cpi_data_coverage",
            "Thematic Coverage": "cpi_thematic_coverage",
            "NDC publication year": "ndc_publication_year",
            "Hyperlink": "ndc_source_url",
        }
    )

    cpi = scope_columns.merge(adaptation, on="cpi_country", how="left").merge(
        cond_pivot, on="cpi_country", how="left"
    )
    cond_cols = [
        "conditional_need_all_objectives_usd_bn",
        "unconditional_need_all_objectives_usd_bn",
        "unspecified_need_all_objectives_usd_bn",
    ]
    cpi["classified_total_need_all_objectives_usd_bn"] = cpi[cond_cols].sum(
        axis=1, min_count=1
    )
    cpi["conditional_share_all_objectives"] = (
        cpi["conditional_need_all_objectives_usd_bn"]
        / cpi["classified_total_need_all_objectives_usd_bn"]
    )
    # CPI does not cross-tab objective and conditionality.  This proportional
    # allocation is therefore a transparent proxy, not an observed finance gap.
    cpi["external_support_gap_proxy_2024_2035_usd_bn"] = (
        cpi["adaptation_need_2024_2035_usd_bn"]
        * cpi["conditional_share_all_objectives"]
    )

    match_rows: list[dict[str, object]] = []
    cpi_country_set = set(cpi["cpi_country"])
    for country in raw["country"]:
        cpi_country = CPI_NAME_ALIASES.get(country, country)
        match_rows.append(
            {
                "country": country,
                "cpi_country": cpi_country,
                "cpi_match_found": cpi_country in cpi_country_set,
                "alias_applied": country != cpi_country,
            }
        )
    matches = pd.DataFrame(match_rows)

    combined = raw.merge(matches, on="country", how="left").merge(
        cpi, on="cpi_country", how="left"
    )

    # Preserve blanks rather than turning missing needs into zeros.
    raw.to_csv(OUTPUT_DIR / "cleaned_country_panel.csv", index=False, encoding="utf-8-sig")
    membership.to_csv(
        OUTPUT_DIR / "coalition_membership.csv", index=False, encoding="utf-8-sig"
    )
    matches.to_csv(
        OUTPUT_DIR / "cpi_country_matches.csv", index=False, encoding="utf-8-sig"
    )
    combined.to_csv(
        OUTPUT_DIR / "country_emissions_and_finance.csv",
        index=False,
        encoding="utf-8-sig",
    )

    selected = combined[
        combined[
            [column for column in combined if column.startswith("member_")]
        ].any(axis=1)
    ].copy()
    selected.to_csv(
        OUTPUT_DIR / "selected_country_finance_detail.csv",
        index=False,
        encoding="utf-8-sig",
    )

    selected_unmatched = selected.loc[~selected["cpi_match_found"], "country"].tolist()
    print(f"Cleaned {len(raw)} country rows.")
    print(f"Coalition sizes: {roster_counts}")
    print(f"Loan-eligible countries after aliasing: {sorted(loan_names)}")
    print(f"Selected countries absent from CPI scope: {selected_unmatched or 'None'}")


if __name__ == "__main__":
    main()
