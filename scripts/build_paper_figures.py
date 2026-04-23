from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


CONFIRMATORY_BASELINE = "RandomAgent"


def _parse_args():
    parser = argparse.ArgumentParser(description="Build paper figures from a results bundle.")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--output-dir", default="")
    return parser.parse_args()


def _load_report(results_dir: Path) -> dict:
    return json.loads((results_dir / "report.json").read_text(encoding="utf-8"))


def _load_observations(results_dir: Path) -> pd.DataFrame:
    return pd.read_csv(results_dir / "session_observations.csv")


def _paired_metric_vs_baseline(report: dict, metric_key: str, baseline: str = CONFIRMATORY_BASELINE) -> tuple[str, list[str], list[float], list[float], list[float]]:
    confirmatory = report["confirmatory_assessment"]
    baseline = confirmatory.get("baseline", baseline)
    labels = []
    estimates = []
    lower_errors = []
    upper_errors = []
    for agent in sorted(confirmatory["per_agent"]):
        record = confirmatory["per_agent"][agent].get(metric_key)
        if not record:
            raise KeyError(f"missing confirmatory result for {agent} metric {metric_key}")
        estimate = record["estimate"]
        ci_lower = record["ci_lower"]
        ci_upper = record["ci_upper"]
        labels.append(agent)
        estimates.append(estimate)
        lower_errors.append(estimate - ci_lower)
        upper_errors.append(ci_upper - estimate)
    return baseline, labels, estimates, lower_errors, upper_errors


def _build_profit_ci_figure(report: dict, output_dir: Path) -> str:
    baseline, labels, estimates, lower_errors, upper_errors = _paired_metric_vs_baseline(report, "mean_profit")
    fig, ax = plt.subplots(figsize=(7, 4))
    positions = range(len(labels))
    ax.bar(positions, estimates, color=["#c44e52", "#4c72b0", "#55a868"])
    ax.errorbar(positions, estimates, yerr=[lower_errors, upper_errors], fmt="none", ecolor="black", capsize=5, lw=1.2)
    ax.axhline(0, color="black", lw=1, linestyle="--")
    ax.set_xticks(list(positions), labels, rotation=15)
    ax.set_ylabel(f"Paired mean profit difference vs {baseline}")
    ax.set_title("Figure A1. Profit advantage with 95% bootstrap CI")
    fig.tight_layout()
    path = output_dir / "figure_profit_ci.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def _build_risk_figure(report: dict, output_dir: Path) -> str:
    baseline, agents, cvar_estimates, cvar_low, cvar_high = _paired_metric_vs_baseline(report, "cvar_5")
    _, ruin_agents, ruin_estimates, ruin_low, ruin_high = _paired_metric_vs_baseline(report, "ruin_probability", baseline=baseline)
    if agents != ruin_agents:
        raise ValueError("risk figures require matching paired agent sets")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(range(len(agents)), cvar_estimates, color="#4c72b0")
    axes[0].errorbar(range(len(agents)), cvar_estimates, yerr=[cvar_low, cvar_high], fmt="none", ecolor="black", capsize=5, lw=1.2)
    axes[0].set_xticks(range(len(agents)), agents, rotation=15)
    axes[0].axhline(0, color="black", lw=1, linestyle="--")
    axes[0].set_title(f"Paired ΔCVaR_5 vs {baseline}")
    axes[0].set_ylabel("Paired CVaR_5 difference")
    axes[1].bar(range(len(agents)), ruin_estimates, color="#c44e52")
    axes[1].errorbar(range(len(agents)), ruin_estimates, yerr=[ruin_low, ruin_high], fmt="none", ecolor="black", capsize=5, lw=1.2)
    axes[1].set_xticks(range(len(agents)), agents, rotation=15)
    axes[1].axhline(0, color="black", lw=1, linestyle="--")
    axes[1].set_title(f"Paired Δruin probability vs {baseline}")
    axes[1].set_ylabel("Paired probability difference")
    fig.suptitle("Figure A2. Baseline-relative risk differences")
    fig.tight_layout()
    path = output_dir / "figure_risk_summary.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def _build_seat_figure(observations: pd.DataFrame, output_dir: Path) -> str:
    seat_profit = observations.groupby(["agent", "seat"])["profit"].mean().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4))
    image = ax.imshow(seat_profit.values, cmap="coolwarm", aspect="auto")
    ax.set_yticks(range(len(seat_profit.index)), seat_profit.index)
    ax.set_xticks(range(len(seat_profit.columns)), [f"Seat {seat}" for seat in seat_profit.columns])
    ax.set_title("Figure A3. Mean profit by seat")
    fig.colorbar(image, ax=ax, label="Mean session profit")
    fig.tight_layout()
    path = output_dir / "figure_seat_heatmap.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def _write_summary_table(report: dict, output_dir: Path) -> str:
    fields = [
        "ranking",
        "agent",
        "mean_profit",
        "cvar_5",
        "cvar_5_low_support",
        "cvar_5_tail_size",
        "ruin_probability",
        "win_rate",
        "sample_count",
    ]
    path = output_dir / "table_main_metrics.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, ranked_row in enumerate(report["ranking"], start=1):
            agent = ranked_row["agent"]
            summary = report["agent_performance_table"].get(agent, {})
            row = {
                "ranking": rank,
                "agent": agent,
                "mean_profit": ranked_row.get("mean_profit", 0),
                "cvar_5": ranked_row.get("cvar_5", 0),
                "cvar_5_low_support": ranked_row.get("cvar_5_low_support", False),
                "cvar_5_tail_size": ranked_row.get("cvar_5_tail_size", 0),
                "ruin_probability": ranked_row.get("ruin_probability", 0),
                "win_rate": ranked_row.get("win_rate", 0),
                "sample_count": summary.get("sample_count", 0),
            }
            writer.writerow(row)
    return str(path)


def _factor_display_maps(report: dict) -> tuple[dict[str, str], dict[str, str]]:
    model_map = {}
    for entry in report.get("model_panel", []):
        model_map[str(entry["model_id"])] = str(entry["model_id"])
    strategy_map = {}
    for entry in report.get("strategy_panel", []):
        strategy_map[str(entry["strategy_id"])] = str(entry.get("label", entry["strategy_id"]))
    return model_map, strategy_map


def _build_factorial_interaction_figure(report: dict, output_dir: Path) -> str:
    rq = report["rq_model_vs_strategy"]
    cell_means = rq["mean_profit"]["cell_means"]
    model_map, strategy_map = _factor_display_maps(report)
    strategy_ids = sorted(cell_means)
    model_ids = sorted({model_id for model_values in cell_means.values() for model_id in model_values})
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for strategy_id in strategy_ids:
        y_values = [cell_means[strategy_id].get(model_id, 0.0) for model_id in model_ids]
        ax.plot(range(len(model_ids)), y_values, marker="o", linewidth=2, label=strategy_map.get(strategy_id, strategy_id))
    ax.set_xticks(range(len(model_ids)), [model_map.get(model_id, model_id) for model_id in model_ids], rotation=15, ha="right")
    ax.set_ylabel("Mean session profit")
    ax.set_title("Figure 1. Model-by-strategy interaction on mean profit")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    path = output_dir / "figure_factorial_interaction.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def _build_factorial_effect_size_figure(report: dict, output_dir: Path) -> str:
    terms = report["rq_model_vs_strategy"]["effect_decomposition"]["terms"]
    order = ["model", "strategy", "interaction"]
    labels = ["Model", "Strategy", "Model x Strategy"]
    values = [terms[key]["partial_eta_squared"] for key in order]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(range(len(labels)), values, color=["#4c72b0", "#55a868", "#c44e52"])
    ax.set_xticks(range(len(labels)), labels, rotation=10)
    ax.set_ylabel("Partial eta-squared")
    ax.set_ylim(0, max(values + [0.05]) * 1.2)
    ax.set_title("Figure 2. Effect-size comparison on mean profit")
    fig.tight_layout()
    path = output_dir / "figure_factorial_effect_sizes.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def _bar_with_ci(ax, labels: list[str], values: list[float], lower: list[float], upper: list[float], title: str, ylabel: str) -> None:
    ax.bar(range(len(labels)), values, color="#4c72b0")
    ax.errorbar(range(len(labels)), values, yerr=[lower, upper], fmt="none", ecolor="black", capsize=4, lw=1.0)
    ax.set_xticks(range(len(labels)), labels, rotation=15, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)


def _build_factorial_risk_figure(report: dict, output_dir: Path) -> str:
    rq = report["rq_model_vs_strategy"]
    model_map, strategy_map = _factor_display_maps(report)
    by_model_cvar = rq["secondary_metrics"]["cvar_5"]["by_model"]
    by_model_ruin = rq["secondary_metrics"]["ruin_probability"]["by_model"]
    by_strategy_cvar = rq["secondary_metrics"]["cvar_5"]["by_strategy"]
    by_strategy_ruin = rq["secondary_metrics"]["ruin_probability"]["by_strategy"]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    model_ids = sorted(by_model_cvar)
    _bar_with_ci(
        axes[0][0],
        [model_map.get(model_id, model_id) for model_id in model_ids],
        [by_model_cvar[model_id]["estimate"] for model_id in model_ids],
        [by_model_cvar[model_id]["estimate"] - by_model_cvar[model_id]["ci_lower"] for model_id in model_ids],
        [by_model_cvar[model_id]["ci_upper"] - by_model_cvar[model_id]["estimate"] for model_id in model_ids],
        "Model-marginal CVaR_5",
        "CVaR_5",
    )
    _bar_with_ci(
        axes[0][1],
        [model_map.get(model_id, model_id) for model_id in model_ids],
        [by_model_ruin[model_id]["estimate"] for model_id in model_ids],
        [by_model_ruin[model_id]["estimate"] - by_model_ruin[model_id]["ci_lower"] for model_id in model_ids],
        [by_model_ruin[model_id]["ci_upper"] - by_model_ruin[model_id]["estimate"] for model_id in model_ids],
        "Model-marginal ruin probability",
        "Ruin probability",
    )

    strategy_ids = sorted(by_strategy_cvar)
    _bar_with_ci(
        axes[1][0],
        [strategy_map.get(strategy_id, strategy_id) for strategy_id in strategy_ids],
        [by_strategy_cvar[strategy_id]["estimate"] for strategy_id in strategy_ids],
        [by_strategy_cvar[strategy_id]["estimate"] - by_strategy_cvar[strategy_id]["ci_lower"] for strategy_id in strategy_ids],
        [by_strategy_cvar[strategy_id]["ci_upper"] - by_strategy_cvar[strategy_id]["estimate"] for strategy_id in strategy_ids],
        "Strategy-marginal CVaR_5",
        "CVaR_5",
    )
    _bar_with_ci(
        axes[1][1],
        [strategy_map.get(strategy_id, strategy_id) for strategy_id in strategy_ids],
        [by_strategy_ruin[strategy_id]["estimate"] for strategy_id in strategy_ids],
        [by_strategy_ruin[strategy_id]["estimate"] - by_strategy_ruin[strategy_id]["ci_lower"] for strategy_id in strategy_ids],
        [by_strategy_ruin[strategy_id]["ci_upper"] - by_strategy_ruin[strategy_id]["estimate"] for strategy_id in strategy_ids],
        "Strategy-marginal ruin probability",
        "Ruin probability",
    )
    fig.suptitle("Figure 3. Secondary risk summaries by model and strategy")
    fig.tight_layout()
    path = output_dir / "figure_factorial_risk.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return str(path)


def _write_factorial_effect_table(report: dict, output_dir: Path) -> str:
    fields = ["term", "df", "sum_squares", "mean_square", "f_statistic", "partial_eta_squared"]
    path = output_dir / "table_main_effects.csv"
    terms = report["rq_model_vs_strategy"]["effect_decomposition"]["terms"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key in ("model", "strategy", "interaction"):
            row = dict(terms[key])
            row["term"] = key
            writer.writerow({field: row.get(field, "") for field in fields})
    return str(path)


def _build_factorial_assets(report: dict, observations: pd.DataFrame, output_dir: Path, results_dir: Path) -> dict:
    return {
        "source_results_dir": str(results_dir),
        "generator": "python3 scripts/build_paper_figures.py",
        "figure_factorial_interaction": _build_factorial_interaction_figure(report, output_dir),
        "figure_factorial_effect_sizes": _build_factorial_effect_size_figure(report, output_dir),
        "figure_factorial_risk": _build_factorial_risk_figure(report, output_dir),
        "table_main_effects": _write_factorial_effect_table(report, output_dir),
        "sources": {
            "report": str(results_dir / "report.json"),
            "session_observations": str(results_dir / "session_observations.csv"),
        },
    }


def _build_baseline_assets(report: dict, observations: pd.DataFrame, output_dir: Path, results_dir: Path) -> dict:
    return {
        "source_results_dir": str(results_dir),
        "generator": "python3 scripts/build_paper_figures.py",
        "confirmatory_baseline": CONFIRMATORY_BASELINE,
        "figure_profit_ci": _build_profit_ci_figure(report, output_dir),
        "figure_risk_summary": _build_risk_figure(report, output_dir),
        "figure_seat_heatmap": _build_seat_figure(observations, output_dir),
        "table_main_metrics": _write_summary_table(report, output_dir),
        "sources": {
            "report": str(results_dir / "report.json"),
            "session_observations": str(results_dir / "session_observations.csv"),
        },
    }


def main() -> None:
    args = _parse_args()
    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir) if args.output_dir else results_dir / "paper_assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    report = _load_report(results_dir)
    observations = _load_observations(results_dir)
    if "rq_model_vs_strategy" in report:
        payload = _build_factorial_assets(report, observations, output_dir, results_dir)
    else:
        payload = _build_baseline_assets(report, observations, output_dir, results_dir)
    (output_dir / "paper_assets_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
