"""Run the data/chart scripts and validate the manually authored memoranda.

Usage from the ``group project`` directory or its parent:

    python scripts/06_run_pipeline_and_validate.py

On this machine, the system ``python`` environment is required for plotting
because it contains Matplotlib as well as pandas/openpyxl.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_DIR / "scripts"
OUTPUT_DIR = PROJECT_DIR / "output"
CHART_DIR = PROJECT_DIR / "charts"

PIPELINE = [
    "01_clean_and_match_inputs.py",
    "02_compute_2035_allocations.py",
    "03_compute_adaptation_finance.py",
    "04_create_charts.py",
]

EXPECTED_OUTPUTS = [
    OUTPUT_DIR / "cleaned_country_panel.csv",
    OUTPUT_DIR / "coalition_membership.csv",
    OUTPUT_DIR / "cpi_country_matches.csv",
    OUTPUT_DIR / "country_emissions_and_finance.csv",
    OUTPUT_DIR / "selected_country_finance_detail.csv",
    OUTPUT_DIR / "allocation_by_bloc_and_scenario.csv",
    OUTPUT_DIR / "global_south_allocation_summary.csv",
    OUTPUT_DIR / "adaptation_finance_summary.csv",
    OUTPUT_DIR / "adaptation_finance_by_country.csv",
    OUTPUT_DIR / "74_country_2035_allocation_position.md",
    OUTPUT_DIR / "20_country_2035_allocation_position.md",
    OUTPUT_DIR / "global_south_2035_allocation_reports.md",
]

EXPECTED_CHARTS = [
    CHART_DIR / "01_allocation_principles_by_roster.png",
    CHART_DIR / "02_equity_profile_74_country_coalition.png",
    CHART_DIR / "03_adaptation_need_and_gap_proxy.png",
    CHART_DIR / "04_loan_grant_mix.png",
    CHART_DIR / "05_top_adaptation_needs_74_country_coalition.png",
    CHART_DIR / "06_allocation_74_country_coalition.png",
    CHART_DIR / "07_allocation_global_south_coalition.png",
    CHART_DIR / "08_global_south_loan_grant_mix.png",
]


def check(condition: bool, message: str, results: list[tuple[str, str]]) -> None:
    if not condition:
        raise AssertionError(message)
    results.append(("PASS", message))


def main() -> None:
    if importlib.util.find_spec("matplotlib") is None:
        raise RuntimeError(
            "Matplotlib is unavailable in this Python environment. Run the pipeline with "
            "the system `python` command used for this project."
        )

    for script in PIPELINE:
        print(f"Running {script} ...")
        subprocess.run([sys.executable, str(SCRIPT_DIR / script)], check=True)

    results: list[tuple[str, str]] = []
    for path in EXPECTED_OUTPUTS + EXPECTED_CHARTS:
        check(path.exists() and path.stat().st_size > 0, f"Created non-empty {path.name}", results)

    membership = pd.read_csv(OUTPUT_DIR / "coalition_membership.csv")
    counts = membership.groupby("scenario")["country"].nunique().to_dict()
    check(counts.get("74-country LDC+AOSIS coalition") == 74, "Main roster contains 74 unique countries", results)
    check(counts.get("20-country selected coalition") == 20, "Sensitivity roster contains 20 unique countries", results)

    allocations = pd.read_csv(OUTPUT_DIR / "allocation_by_bloc_and_scenario.csv")
    allowance_columns = [
        "equal_per_capita_allowance_mt",
        "historical_responsibility_allowance_mt",
        "ability_to_pay_allowance_mt",
    ]
    for scenario, group in allocations.groupby("scenario"):
        budget = group["world_2035_budget_mt"].iloc[0]
        for column in allowance_columns:
            check(
                np.isclose(group[column].sum(), budget, atol=1e-5),
                f"{scenario}: {column} conserves the world budget",
                results,
            )

    coalition = pd.read_csv(OUTPUT_DIR / "global_south_allocation_summary.csv")
    for _, row in coalition.iterrows():
        values = row[allowance_columns].astype(float)
        check(
            values.idxmax() == "equal_per_capita_allowance_mt",
            f"{row['scenario']}: equal per capita is the coalition's largest current-list allowance",
            results,
        )

    main = coalition.loc[
        coalition["scenario"] == "74-country LDC+AOSIS coalition"
    ].iloc[0]
    check(
        np.isclose(main["world_2035_budget_mt"], 18_699.0, atol=0.01),
        "World 2035 budget reconciles to 18.699 Gt CO2 from raw.csv",
        results,
    )
    check(
        np.isclose(main["equal_per_capita_allowance_mt"], 2_826.771, atol=0.01),
        "Main equal-per-capita result reconciles to 2.827 Gt CO2",
        results,
    )

    finance = pd.read_csv(OUTPUT_DIR / "adaptation_finance_summary.csv")
    check(
        (finance["countries_with_reported_adaptation_need"] <= finance["member_countries"]).all(),
        "Reported-need country counts do not exceed roster sizes",
        results,
    )
    check(
        (finance["reported_adaptation_need_2024_2035_usd_bn"] > 0).all(),
        "Both rosters have positive reported adaptation needs",
        results,
    )
    shares = finance[
        ["grant_priority_share_of_reported_need", "loan_eligible_share_of_reported_need"]
    ].sum(axis=1)
    check(np.allclose(shares, 1.0, atol=1e-10), "Grant and loan shares sum to 100%", results)

    for chart in EXPECTED_CHARTS:
        with Image.open(chart) as image:
            width, height = image.size
        check(width >= 1_500 and height >= 900, f"{chart.name} has presentation-quality dimensions ({width}×{height})", results)

    report_74 = (OUTPUT_DIR / "74_country_2035_allocation_position.md").read_text(
        encoding="utf-8"
    )
    report_20 = (OUTPUT_DIR / "20_country_2035_allocation_position.md").read_text(
        encoding="utf-8"
    )
    for label, report, number, chart_name in [
        ("74-country", report_74, "2.827 Gt CO₂", "06_allocation_74_country_coalition.png"),
        ("Global South", report_20, "1.703 Gt CO₂", "07_allocation_global_south_coalition.png"),
    ]:
        for phrase in [
            number,
            "equal-per-capita",
            "historical responsibility",
            "ability to pay",
            "negotiating number",
        ]:
            check(phrase.lower() in report.lower(), f"{label} report includes: {phrase}", results)
        check(
            f"../charts/{chart_name}" in report,
            f"{label} report embeds {chart_name}",
            results,
        )
    check("20-country" not in report_20.lower(), "Global South memorandum contains no 20-country label", results)
    for number in ["1.493 Gt CO₂", "1.703 Gt CO₂", "0.981 Gt CO₂"]:
        check(number in report_20, f"Global South memorandum includes supplied result: {number}", results)
    for finance_value in ["$161.8 billion", "$114.2 billion", "70.6%", "$47.6 billion", "29.4%"]:
        check(finance_value in report_20, f"Global South memorandum includes finance result: {finance_value}", results)
    check(
        "../charts/08_global_south_loan_grant_mix.png" in report_20,
        "Global South memorandum embeds the grant/loan pie chart",
        results,
    )
    for finance_value in ["$284 billion", "$339 billion", "$26 billion"]:
        check(finance_value in report_20, f"Global South memorandum includes UNEP gap result: {finance_value}", results)

    validation_lines = [
        "# Pipeline Validation Report",
        "",
        f"Python executable: `{sys.executable}`",
        "",
        "| Status | Check |",
        "| --- | --- |",
    ]
    validation_lines.extend(f"| {status} | {message} |" for status, message in results)
    validation_lines.extend(
        [
            "",
            f"**Result: {len(results)} checks passed; 0 failed.**",
            "",
            "The 20-country line in the supplied `result.csv` remains an input audit warning: it does not reconcile to the current 20-country text list and `raw.csv`. Both position reports use reproducible current-list results.",
        ]
    )
    validation_path = OUTPUT_DIR / "validation_report.md"
    validation_path.write_text("\n".join(validation_lines) + "\n", encoding="utf-8")
    print(f"Validated pipeline: {len(results)} checks passed.")
    print(f"Wrote {validation_path}")


if __name__ == "__main__":
    main()
