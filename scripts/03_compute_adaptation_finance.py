"""Summarize adaptation needs, an external-support proxy, and loan/grant mix.

The CPI workbook reports needs, not actual finance received.  The script does
not claim a measured funding gap.  It creates a clearly labelled proxy by
applying each country's all-objective conditional-finance share to its reported
adaptation need.  Missing classifications are left missing rather than imputed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "output"

SCENARIO_FLAGS = {
    "74-country LDC+AOSIS coalition": "member_74_country_ldc_aosis_coalition",
    "20-country selected coalition": "member_20_country_selected_coalition",
}

YEARS_2024_TO_2035_INCLUSIVE = 12


def main() -> None:
    detail = pd.read_csv(OUTPUT_DIR / "country_emissions_and_finance.csv")
    need_column = "adaptation_need_2024_2035_usd_bn"
    gap_column = "external_support_gap_proxy_2024_2035_usd_bn"
    cond_share_column = "conditional_share_all_objectives"

    required = {
        "country",
        "loan_eligible",
        "cpi_match_found",
        need_column,
        gap_column,
        cond_share_column,
    } | set(SCENARIO_FLAGS.values())
    missing = required - set(detail.columns)
    if missing:
        raise ValueError(f"Run script 01 first; missing columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    country_outputs: list[pd.DataFrame] = []

    for scenario, flag in SCENARIO_FLAGS.items():
        members = detail.loc[detail[flag].fillna(False).astype(bool)].copy()
        members["scenario"] = scenario
        members["finance_instrument_group"] = np.where(
            members["loan_eligible"].fillna(False).astype(bool),
            "Loan-eligible",
            "Grant-priority",
        )
        members["adaptation_need_annual_average_usd_bn"] = (
            members[need_column] / YEARS_2024_TO_2035_INCLUSIVE
        )
        members["external_support_gap_proxy_annual_average_usd_bn"] = (
            members[gap_column] / YEARS_2024_TO_2035_INCLUSIVE
        )
        country_outputs.append(members)

        quantified = members[need_column].notna()
        classified = quantified & members[cond_share_column].notna()
        reported_need = members.loc[quantified, need_column].sum()
        classified_need = members.loc[classified, need_column].sum()
        external_proxy = members.loc[classified, gap_column].sum()

        loan_need = members.loc[
            quantified & members["loan_eligible"].fillna(False).astype(bool), need_column
        ].sum()
        grant_need = members.loc[
            quantified & ~members["loan_eligible"].fillna(False).astype(bool), need_column
        ].sum()

        loan_gap_proxy = members.loc[
            classified & members["loan_eligible"].fillna(False).astype(bool), gap_column
        ].sum()
        grant_gap_proxy = members.loc[
            classified & ~members["loan_eligible"].fillna(False).astype(bool), gap_column
        ].sum()

        rows.append(
            {
                "scenario": scenario,
                "member_countries": members["country"].nunique(),
                "countries_matched_to_cpi": int(members["cpi_match_found"].sum()),
                "countries_with_reported_adaptation_need": int(quantified.sum()),
                "countries_with_conditionality_classification": int(classified.sum()),
                "reported_adaptation_need_2024_2035_usd_bn": reported_need,
                "reported_adaptation_need_annual_average_usd_bn": (
                    reported_need / YEARS_2024_TO_2035_INCLUSIVE
                ),
                "adaptation_need_with_gap_proxy_coverage_usd_bn": classified_need,
                "gap_proxy_value_coverage_share": (
                    classified_need / reported_need if reported_need else np.nan
                ),
                "external_support_gap_proxy_2024_2035_usd_bn": external_proxy,
                "external_support_gap_proxy_annual_average_usd_bn": (
                    external_proxy / YEARS_2024_TO_2035_INCLUSIVE
                ),
                "grant_priority_reported_need_usd_bn": grant_need,
                "loan_eligible_reported_need_usd_bn": loan_need,
                "grant_priority_share_of_reported_need": (
                    grant_need / reported_need if reported_need else np.nan
                ),
                "loan_eligible_share_of_reported_need": (
                    loan_need / reported_need if reported_need else np.nan
                ),
                "grant_priority_gap_proxy_usd_bn": grant_gap_proxy,
                "loan_eligible_gap_proxy_usd_bn": loan_gap_proxy,
            }
        )

    summary = pd.DataFrame(rows)
    by_country = pd.concat(country_outputs, ignore_index=True)
    by_country = by_country.sort_values(
        ["scenario", need_column], ascending=[True, False], na_position="last"
    )

    summary.to_csv(
        OUTPUT_DIR / "adaptation_finance_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    by_country.to_csv(
        OUTPUT_DIR / "adaptation_finance_by_country.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print(
        summary[
            [
                "scenario",
                "member_countries",
                "countries_with_reported_adaptation_need",
                "reported_adaptation_need_2024_2035_usd_bn",
                "external_support_gap_proxy_2024_2035_usd_bn",
                "gap_proxy_value_coverage_share",
                "grant_priority_share_of_reported_need",
            ]
        ].round(3).to_string(index=False)
    )


if __name__ == "__main__":
    main()
