"""Compute 2035 CO2 allowances under the three assignment principles."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "output"

GLOBAL_2035_BUDGET_FRACTION_OF_2024 = 0.50

SCENARIO_FLAGS = {
    "74-country LDC+AOSIS coalition": "member_74_country_ldc_aosis_coalition",
    "20-country selected coalition": "member_20_country_selected_coalition",
}

PRINCIPLES = {
    "Equal per capita": "equal_per_capita_allowance_mt",
    "Historical responsibility": "historical_responsibility_allowance_mt",
    "Ability to pay": "ability_to_pay_allowance_mt",
}


def assign_bloc(row: pd.Series, member_flag: str) -> str:
    if row["country"] == "United States":
        return "United States"
    if row["original_bloc"] == "European Union (27)":
        return "European Union (27)"
    if row["country"] == "China":
        return "China"
    if row["country"] == "India":
        return "India"
    if bool(row[member_flag]):
        return "Global South & Climate-Vulnerable Coalition"
    return "Rest of World"


def weighted_or_nan_sum(series: pd.Series) -> float:
    return float(series.sum(min_count=1))


def main() -> None:
    countries = pd.read_csv(OUTPUT_DIR / "cleaned_country_panel.csv")
    required = {
        "country",
        "original_bloc",
        "population_2024",
        "gdp_2022_ppp_2011_intl_usd",
        "co2_2024_mt",
        "cumulative_co2_through_2024_mt",
    } | set(SCENARIO_FLAGS.values())
    missing = required - set(countries.columns)
    if missing:
        raise ValueError(f"Run 01_clean_and_match_inputs.py first; missing: {sorted(missing)}")

    world = {
        "population": weighted_or_nan_sum(countries["population_2024"]),
        "gdp": weighted_or_nan_sum(countries["gdp_2022_ppp_2011_intl_usd"]),
        "co2": weighted_or_nan_sum(countries["co2_2024_mt"]),
        "cumulative": weighted_or_nan_sum(countries["cumulative_co2_through_2024_mt"]),
    }
    world_budget_mt = world["co2"] * GLOBAL_2035_BUDGET_FRACTION_OF_2024
    global_reduction_mt = world["co2"] - world_budget_mt

    all_scenarios: list[pd.DataFrame] = []
    coalition_summaries: list[pd.Series] = []

    for scenario, member_flag in SCENARIO_FLAGS.items():
        frame = countries.copy()
        frame["analysis_bloc"] = frame.apply(assign_bloc, axis=1, member_flag=member_flag)
        grouped = (
            frame.groupby("analysis_bloc", sort=False)
            .agg(
                population_2024=("population_2024", "sum"),
                gdp_2022_ppp_2011_intl_usd=("gdp_2022_ppp_2011_intl_usd", "sum"),
                co2_2024_mt=("co2_2024_mt", "sum"),
                cumulative_co2_through_2024_mt=(
                    "cumulative_co2_through_2024_mt",
                    "sum",
                ),
                country_count=("country", "nunique"),
                gdp_observed_country_count=(
                    "gdp_2022_ppp_2011_intl_usd",
                    "count",
                ),
            )
            .reset_index()
            .rename(columns={"analysis_bloc": "bloc"})
        )
        grouped["scenario"] = scenario
        grouped["population_share"] = grouped["population_2024"] / world["population"]
        grouped["gdp_share"] = grouped["gdp_2022_ppp_2011_intl_usd"] / world["gdp"]
        grouped["current_emissions_share"] = grouped["co2_2024_mt"] / world["co2"]
        grouped["cumulative_emissions_share"] = (
            grouped["cumulative_co2_through_2024_mt"] / world["cumulative"]
        )
        grouped["co2_per_capita_2024_t"] = (
            grouped["co2_2024_mt"] * 1_000_000 / grouped["population_2024"]
        )
        grouped["cumulative_co2_per_capita_t"] = (
            grouped["cumulative_co2_through_2024_mt"]
            * 1_000_000
            / grouped["population_2024"]
        )
        grouped["gdp_per_capita_2022_ppp_2011_intl_usd"] = (
            grouped["gdp_2022_ppp_2011_intl_usd"] / grouped["population_2024"]
        )

        grouped["equal_per_capita_allowance_mt"] = (
            world_budget_mt * grouped["population_share"]
        )
        grouped["historical_responsibility_allowance_mt"] = (
            grouped["co2_2024_mt"]
            - global_reduction_mt * grouped["cumulative_emissions_share"]
        )
        grouped["ability_to_pay_allowance_mt"] = (
            grouped["co2_2024_mt"] - global_reduction_mt * grouped["gdp_share"]
        )

        for label, allowance_column in PRINCIPLES.items():
            cut_column = label.lower().replace(" ", "_") + "_change_from_2024"
            grouped[cut_column] = grouped[allowance_column] / grouped["co2_2024_mt"] - 1

        grouped["world_co2_2024_mt"] = world["co2"]
        grouped["world_2035_budget_mt"] = world_budget_mt
        grouped["global_reduction_mt"] = global_reduction_mt
        all_scenarios.append(grouped)

        coalition = grouped.loc[
            grouped["bloc"] == "Global South & Climate-Vulnerable Coalition"
        ].iloc[0]
        coalition_summaries.append(coalition)

        # Conservation check: every allocation principle must sum to one budget.
        for principle, allowance_column in PRINCIPLES.items():
            difference = grouped[allowance_column].sum() - world_budget_mt
            if not np.isclose(difference, 0.0, atol=1e-6):
                raise AssertionError(
                    f"{scenario}/{principle} does not conserve the budget: {difference} Mt"
                )

    allocations = pd.concat(all_scenarios, ignore_index=True)
    coalition_summary = pd.DataFrame(coalition_summaries).reset_index(drop=True)

    allocations.to_csv(
        OUTPUT_DIR / "allocation_by_bloc_and_scenario.csv",
        index=False,
        encoding="utf-8-sig",
    )
    coalition_summary.to_csv(
        OUTPUT_DIR / "global_south_allocation_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    display_columns = [
        "scenario",
        "co2_2024_mt",
        "equal_per_capita_allowance_mt",
        "historical_responsibility_allowance_mt",
        "ability_to_pay_allowance_mt",
    ]
    print(coalition_summary[display_columns].round(3).to_string(index=False))
    print(f"World 2024 country CO2: {world['co2']:.3f} Mt")
    print(f"World 2035 budget (50%): {world_budget_mt:.3f} Mt")


if __name__ == "__main__":
    main()
