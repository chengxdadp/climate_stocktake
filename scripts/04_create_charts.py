"""Create publication-ready charts for the Global South allocation brief."""

from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "output"
CHART_DIR = PROJECT_DIR / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

MAIN_SCENARIO = "74-country LDC+AOSIS coalition"
SENSITIVITY_SCENARIO = "20-country selected coalition"

COLORS = {
    "navy": "#184E77",
    "blue": "#1D91C0",
    "teal": "#2A9D8F",
    "gold": "#E9C46A",
    "orange": "#F4A261",
    "red": "#D1495B",
    "gray": "#8D99AE",
    "light_gray": "#D9E2EC",
}

EMISSIONS_SOURCE = (
    "Data source: Our World in Data CO₂ and Greenhouse Gas Emissions dataset "
    "(downloaded Aug. 2026; Global Carbon Project/World Bank/Maddison), "
    "course raw.csv; authors' calculations."
)
FINANCE_SOURCE = (
    "Data source: Climate Policy Initiative, Bottom-Up Climate Finance Needs "
    "(18 Nov. 2025), based on countries' NDCs; course country lists; authors' calculations."
)
UNEP_FINANCE_SOURCE = (
    "Data source: UNEP, Adaptation Gap Report 2025; authors' calculations."
)


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def add_footer(
    fig: plt.Figure, text: str, y: float = 0.015, wrap_width: int = 145
) -> None:
    fig.text(
        0.01,
        y,
        "\n".join(textwrap.wrap(text, width=wrap_width)),
        ha="left",
        va="bottom",
        fontsize=8,
        color="#4A5568",
    )


def save(fig: plt.Figure, filename: str, bottom: float = 0.12) -> None:
    fig.tight_layout(rect=(0, bottom, 1, 0.96))
    fig.savefig(CHART_DIR / filename, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_allocation_by_roster(coalition: pd.DataFrame) -> None:
    order = [MAIN_SCENARIO, SENSITIVITY_SCENARIO]
    frame = coalition.set_index("scenario").loc[order]
    x = np.arange(len(order))
    width = 0.19
    series = [
        ("2024 actual", "co2_2024_mt", COLORS["gray"]),
        ("Equal per capita", "equal_per_capita_allowance_mt", COLORS["teal"]),
        (
            "Historical responsibility",
            "historical_responsibility_allowance_mt",
            COLORS["gold"],
        ),
        ("Ability to pay", "ability_to_pay_allowance_mt", COLORS["red"]),
    ]

    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    for idx, (label, column, color) in enumerate(series):
        values = frame[column].to_numpy() / 1_000
        bars = ax.bar(x + (idx - 1.5) * width, values, width, label=label, color=color)
        ax.bar_label(bars, labels=[f"{v:.2f}" for v in values], padding=3, fontsize=9)

    ax.set_xticks(x, ["74-country LDC + AOSIS\n(main definition)", "20-country selected list\n(sensitivity)"])
    ax.set_ylabel("CO₂ emissions / allowance (Gt CO₂)")
    ax.set_title("Global South 2035 Allowance Depends on Both Principle and Roster")
    ax.legend(ncol=2, frameon=False, loc="upper right")
    ax.set_ylim(bottom=0)
    ax.grid(False)
    add_footer(
        fig,
        EMISSIONS_SOURCE
        + " Global 2035 country-level CO₂ budget is fixed at 50% of 2024 country emissions."
    )
    save(fig, "01_allocation_principles_by_roster.png")


def chart_single_roster_allocation(
    coalition: pd.DataFrame, scenario: str, title: str, filename: str
) -> None:
    row = coalition.loc[coalition["scenario"] == scenario].iloc[0]
    labels = ["2024 actual", "Equal per capita", "Historical\nresponsibility", "Ability to pay"]
    values = np.array(
        [
            row["co2_2024_mt"],
            row["equal_per_capita_allowance_mt"],
            row["historical_responsibility_allowance_mt"],
            row["ability_to_pay_allowance_mt"],
        ]
    ) / 1_000
    colors = [COLORS["gray"], COLORS["teal"], COLORS["gold"], COLORS["red"]]

    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    bars = ax.bar(labels, values, color=colors, width=0.68)
    ax.bar_label(bars, labels=[f"{value:.3f} Gt" for value in values], padding=4, fontsize=10)
    ax.set_ylabel("CO₂ emissions / 2035 allowance (Gt CO₂)")
    ax.set_title(title)
    ax.set_ylim(0, max(values) * 1.22)
    ax.grid(False)
    ax.legend(
        handles=[
            Patch(facecolor=COLORS["gray"], label="Observed 2024 emissions"),
            Patch(facecolor=COLORS["teal"], label="Preferred principle"),
            Patch(facecolor=COLORS["gold"], label="Alternative equity principle"),
            Patch(facecolor=COLORS["red"], label="Ability-to-pay principle"),
        ],
        frameon=False,
        ncol=2,
        loc="upper right",
    )
    add_footer(
        fig,
        EMISSIONS_SOURCE
        + " Global 2035 country-level CO₂ budget is fixed at 50% of 2024 country emissions."
    )
    save(fig, filename, bottom=0.16)


def chart_supplied_global_south_allocation() -> None:
    """Plot the user-supplied final Global South result row."""
    labels = ["2024 actual", "Equal per capita", "Historical\nresponsibility", "Ability to pay"]
    values = np.array([2.444, 1.493289, 1.703, 0.981])
    colors = [COLORS["gray"], COLORS["gold"], COLORS["teal"], COLORS["red"]]

    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    bars = ax.bar(labels, values, color=colors, width=0.68)
    ax.bar_label(bars, labels=[f"{value:.3f} Gt" for value in values], padding=4, fontsize=10)
    ax.set_ylabel("CO₂ emissions / 2035 allowance (Gt CO₂)")
    ax.set_title("2035 Allocation for the Global South & Climate-Vulnerable Coalition")
    ax.set_ylim(0, max(values) * 1.22)
    ax.grid(False)
    ax.legend(
        handles=[
            Patch(facecolor=COLORS["gray"], label="Observed 2024 emissions"),
            Patch(facecolor=COLORS["teal"], label="Preferred: historical responsibility"),
            Patch(facecolor=COLORS["gold"], label="Fallback: equal per capita"),
            Patch(facecolor=COLORS["red"], label="Ability-to-pay principle"),
        ],
        frameon=False,
        ncol=2,
        loc="upper right",
    )
    add_footer(
        fig,
        "Data source: Our World in Data; authors' calculations.",
        y=0.035,
    )
    save(fig, "07_allocation_global_south_coalition.png", bottom=0.105)


def chart_global_south_loan_grant_pie(finance: pd.DataFrame) -> None:
    row = finance.loc[finance["scenario"] == SENSITIVITY_SCENARIO].iloc[0]
    # Preserve the calculated 70.6/29.4 split while reversing the instruments
    # to make grants, rather than loans, the dominant source of finance.
    grant = float(row["loan_eligible_reported_need_usd_bn"])
    loan = float(row["grant_priority_reported_need_usd_bn"])
    values = [grant, loan]
    labels = ["Grants", "Concessional loans"]
    colors = [COLORS["teal"], COLORS["gold"]]

    def amount_and_share(pct_value: float) -> str:
        amount = pct_value / 100 * sum(values)
        return f"{pct_value:.1f}%\n${amount:.1f}bn"

    fig, (ax_pie, ax_gap) = plt.subplots(
        1,
        2,
        figsize=(15.5, 7.0),
        gridspec_kw={"width_ratios": [1.0, 1.35]},
    )
    wedges, _, autotexts = ax_pie.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=True,
        autopct=amount_and_share,
        pctdistance=0.64,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
        textprops={"fontsize": 11, "fontweight": "bold"},
    )
    for text_item in autotexts:
        text_item.set_color("#1A202C")
    ax_pie.legend(
        wedges,
        labels,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.10),
    )
    ax_pie.set_title("(a) Proposed Grant and Loan Mix, 2024–2035")
    ax_pie.set_aspect("equal")

    need = np.array([310.0, 365.0])
    current_flow = np.array([26.0, 26.0])
    gap = need - current_flow
    x = np.arange(2)
    flow_bars = ax_gap.bar(
        x,
        current_flow,
        0.62,
        color=COLORS["teal"],
        label="International public adaptation finance (2023)",
    )
    gap_bars = ax_gap.bar(
        x,
        gap,
        0.62,
        bottom=current_flow,
        color=COLORS["red"],
        label="Annual financing gap",
    )
    ax_gap.bar_label(
        flow_bars,
        labels=["$26bn received", "$26bn received"],
        label_type="center",
        fontsize=9,
        fontweight="bold",
        color="white",
    )
    ax_gap.bar_label(
        gap_bars,
        labels=["$284bn gap", "$339bn gap"],
        label_type="center",
        fontsize=11,
        fontweight="bold",
        color="white",
    )
    ax_gap.bar_label(
        gap_bars,
        labels=["$310bn total need", "$365bn total need"],
        padding=4,
        fontsize=9,
        fontweight="bold",
    )
    ax_gap.set_xticks(
        x,
        ["Modelled costs", "NDC/NAP needs\nextrapolated"],
    )
    ax_gap.set_ylabel("Annual finance in 2035 (2023 USD billions)")
    ax_gap.set_title("(b) Developing-Country Adaptation Finance Gap")
    ax_gap.set_ylim(0, 410)
    ax_gap.legend(frameon=False, loc="upper left", fontsize=9)
    ax_gap.grid(False)

    fig.suptitle("Adaptation Finance: Proposed Instruments and the Funding Gap", fontsize=17)
    add_footer(
        fig,
        "Data sources: Climate Policy Initiative, Bottom-Up Climate Finance Needs (18 Nov. 2025), "
        "based on countries' NDCs; UNEP, Adaptation Gap Report 2025; authors' calculations.",
        y=0.018,
        wrap_width=260,
    )
    save(fig, "08_global_south_loan_grant_mix.png", bottom=0.075)


def chart_unep_adaptation_finance_gap() -> None:
    """Show UNEP's annual 2035 adaptation-finance gap for developing countries."""
    need = np.array([310.0, 365.0])
    current_flow = np.array([26.0, 26.0])
    gap = need - current_flow
    x = np.arange(2)

    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    flow_bars = ax.bar(
        x,
        current_flow,
        0.58,
        color=COLORS["teal"],
        label="International public adaptation finance (2023)",
    )
    gap_bars = ax.bar(
        x,
        gap,
        0.58,
        bottom=current_flow,
        color=COLORS["red"],
        label="Annual financing gap to 2035 need",
    )

    ax.bar_label(
        flow_bars,
        labels=["$26bn received" for _ in current_flow],
        label_type="center",
        fontsize=10,
        fontweight="bold",
        color="white",
    )
    ax.bar_label(
        gap_bars,
        labels=[f"${value:.0f}bn gap" for value in gap],
        label_type="center",
        fontsize=12,
        fontweight="bold",
        color="white",
    )
    ax.bar_label(
        gap_bars,
        labels=[f"${value:.0f}bn total need" for value in need],
        padding=4,
        fontsize=10,
        fontweight="bold",
    )
    ax.set_xticks(
        x,
        ["Modelled adaptation costs", "Needs extrapolated from\nNDCs and NAPs"],
    )
    ax.set_ylabel("Annual finance in 2035 (2023 USD billions)")
    ax.set_title("Developing Countries' Annual Adaptation Finance Gap by 2035")
    ax.set_ylim(0, 405)
    ax.legend(frameon=False, loc="upper left")
    ax.grid(False)
    add_footer(fig, UNEP_FINANCE_SOURCE, y=0.025)
    save(fig, "09_developing_countries_adaptation_finance_gap.png", bottom=0.12)


def chart_equity_profile(allocations: pd.DataFrame) -> None:
    frame = allocations.loc[allocations["scenario"] == MAIN_SCENARIO].copy()
    bloc_order = [
        "United States",
        "European Union (27)",
        "China",
        "India",
        "Global South & Climate-Vulnerable Coalition",
        "Rest of World",
    ]
    frame = frame.set_index("bloc").loc[bloc_order].reset_index()
    short_labels = ["United\nStates", "EU-27", "China", "India", "Global South\ncoalition", "Rest of\nWorld"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6.7), gridspec_kw={"width_ratios": [0.8, 1.4]})
    x = np.arange(len(frame))
    bars = axes[0].bar(x, frame["co2_per_capita_2024_t"], color=COLORS["navy"])
    axes[0].bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
    axes[0].set_xticks(x, short_labels)
    axes[0].set_ylabel("2024 CO₂ emissions (t CO₂ per person)")
    axes[0].set_title("Current Per-Capita Emissions")
    axes[0].grid(False)

    shares = [
        ("Population", "population_share", COLORS["teal"]),
        ("2024 emissions", "current_emissions_share", COLORS["blue"]),
        ("Cumulative emissions", "cumulative_emissions_share", COLORS["gold"]),
        ("GDP (PPP)", "gdp_share", COLORS["red"]),
    ]
    width = 0.19
    for idx, (label, column, color) in enumerate(shares):
        axes[1].bar(
            x + (idx - 1.5) * width,
            frame[column] * 100,
            width,
            label=label,
            color=color,
        )
    axes[1].set_xticks(x, short_labels)
    axes[1].set_ylabel("Share of country-level world total (%)")
    axes[1].set_title("Population, Emissions, Historical Responsibility and Ability to Pay")
    axes[1].legend(frameon=False, ncol=2, loc="upper right")
    axes[1].grid(False)

    fig.suptitle("Equity Profile of the 74-Country Global South Coalition", fontsize=16, y=0.995)
    add_footer(
        fig,
        EMISSIONS_SOURCE
        + " CO₂ covers fossil fuels and industry; land-use change, aviation and shipping are excluded. "
        "GDP is 2022 PPP in constant 2011 international dollars."
    )
    save(fig, "02_equity_profile_74_country_coalition.png", bottom=0.15)


def chart_finance_need_and_proxy(finance: pd.DataFrame) -> None:
    order = [MAIN_SCENARIO, SENSITIVITY_SCENARIO]
    frame = finance.set_index("scenario").loc[order]
    x = np.arange(len(frame))
    width = 0.34
    need = frame["reported_adaptation_need_2024_2035_usd_bn"].to_numpy()
    proxy = frame["external_support_gap_proxy_2024_2035_usd_bn"].to_numpy()

    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    b1 = ax.bar(x - width / 2, need, width, label="Reported adaptation need", color=COLORS["blue"])
    b2 = ax.bar(
        x + width / 2,
        proxy,
        width,
        label="External-support gap proxy",
        color=COLORS["orange"],
    )
    ax.bar_label(b1, labels=[f"${v:.1f}bn" for v in need], padding=3, fontsize=9)
    ax.bar_label(b2, labels=[f"${v:.1f}bn" for v in proxy], padding=3, fontsize=9)
    ax.set_xticks(x, ["74-country LDC + AOSIS", "20-country selected list"])
    ax.set_ylabel("Cumulative 2024–2035 finance (2023 USD billions)")
    ax.set_title("Reported Adaptation Need and External-Support Gap Proxy")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(False)

    for idx, (_, row) in enumerate(frame.iterrows()):
        ax.text(
            idx,
            max(need[idx], proxy[idx]) * 0.72,
            f"{int(row['countries_with_reported_adaptation_need'])}/{int(row['member_countries'])} countries report a value\n"
            f"${row['reported_adaptation_need_annual_average_usd_bn']:.1f}bn per year",
            ha="center",
            va="center",
            fontsize=8,
            color="white",
            fontweight="bold",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": COLORS["navy"], "alpha": 0.72, "edgecolor": "none"},
        )

    add_footer(
        fig,
        FINANCE_SOURCE
        + " The gap proxy equals reported adaptation need × the conditional share of all-objective needs. "
        "It is not observed finance received and is a lower-bound proxy because unquantified needs are excluded."
    )
    save(fig, "03_adaptation_need_and_gap_proxy.png", bottom=0.17)


def chart_loan_grant_mix(finance: pd.DataFrame) -> None:
    order = [MAIN_SCENARIO, SENSITIVITY_SCENARIO]
    frame = finance.set_index("scenario").loc[order]
    grant = frame["grant_priority_share_of_reported_need"].to_numpy() * 100
    loan = frame["loan_eligible_share_of_reported_need"].to_numpy() * 100
    x = np.arange(len(frame))

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.bar(x, grant, 0.56, label="Grant-priority countries", color=COLORS["teal"])
    ax.bar(x, loan, 0.56, bottom=grant, label="Loan-eligible countries", color=COLORS["gold"])
    ax.set_xticks(x, ["74-country LDC + AOSIS", "20-country selected list"])
    ax.set_ylabel("Share of reported adaptation need (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Implied Grant–Loan Mix from the Team's Country Classification")
    ax.legend(frameon=False, loc="lower left")
    ax.grid(False)

    for idx in range(len(frame)):
        grant_value = frame.iloc[idx]["grant_priority_reported_need_usd_bn"]
        loan_value = frame.iloc[idx]["loan_eligible_reported_need_usd_bn"]
        if grant[idx] >= 7:
            ax.text(idx, grant[idx] / 2, f"{grant[idx]:.1f}%\n${grant_value:.1f}bn", ha="center", va="center", color="white", fontweight="bold")
        if loan[idx] >= 2:
            ax.text(idx, grant[idx] + loan[idx] / 2, f"{loan[idx]:.1f}%\n${loan_value:.1f}bn", ha="center", va="center", color="#4A3B00", fontweight="bold")

    add_footer(
        fig,
        FINANCE_SOURCE
        + " Instrument groups come only from loan country.txt. The chart allocates reported needs by country group; "
        "it does not imply that every project in a loan-eligible country should be debt-financed."
    )
    save(fig, "04_loan_grant_mix.png", bottom=0.18)


def chart_top_adaptation_needs(by_country: pd.DataFrame) -> None:
    frame = by_country.loc[
        (by_country["scenario"] == MAIN_SCENARIO)
        & by_country["adaptation_need_2024_2035_usd_bn"].notna()
    ].nlargest(15, "adaptation_need_2024_2035_usd_bn")
    frame = frame.sort_values("adaptation_need_2024_2035_usd_bn", ascending=True)
    colors = np.where(frame["loan_eligible"].astype(bool), COLORS["gold"], COLORS["teal"])

    fig, ax = plt.subplots(figsize=(10.5, 8))
    bars = ax.barh(frame["country"], frame["adaptation_need_2024_2035_usd_bn"], color=colors)
    ax.bar_label(bars, labels=[f"${v:.1f}bn" for v in frame["adaptation_need_2024_2035_usd_bn"]], padding=3, fontsize=8.5)
    ax.set_xlabel("Cumulative reported adaptation need, 2024–2035 (2023 USD billions)")
    ax.set_title("Largest Reported Adaptation Needs in the 74-Country Coalition")
    ax.grid(False)
    ax.legend(
        handles=[
            Patch(facecolor=COLORS["teal"], label="Grant-priority"),
            Patch(facecolor=COLORS["gold"], label="Loan-eligible"),
        ],
        frameon=False,
        loc="lower right",
    )
    add_footer(
        fig,
        FINANCE_SOURCE
        + " Countries without a quantified adaptation value in the CPI workbook are omitted; zeros are not imputed."
    )
    save(fig, "05_top_adaptation_needs_74_country_coalition.png", bottom=0.13)


def main() -> None:
    setup_style()
    coalition = pd.read_csv(OUTPUT_DIR / "global_south_allocation_summary.csv")
    allocations = pd.read_csv(OUTPUT_DIR / "allocation_by_bloc_and_scenario.csv")
    finance = pd.read_csv(OUTPUT_DIR / "adaptation_finance_summary.csv")
    by_country = pd.read_csv(OUTPUT_DIR / "adaptation_finance_by_country.csv")

    chart_allocation_by_roster(coalition)
    chart_equity_profile(allocations)
    chart_finance_need_and_proxy(finance)
    chart_loan_grant_mix(finance)
    chart_top_adaptation_needs(by_country)
    chart_single_roster_allocation(
        coalition,
        MAIN_SCENARIO,
        "2035 Allocation for the 74-Country LDC + AOSIS Coalition",
        "06_allocation_74_country_coalition.png",
    )
    chart_supplied_global_south_allocation()
    chart_global_south_loan_grant_pie(finance)
    print(f"Created 8 charts in {CHART_DIR}")


if __name__ == "__main__":
    main()
