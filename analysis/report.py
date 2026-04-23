from __future__ import annotations

from analysis.statistics import (
    CONFIRMATORY_BASELINE,
    build_factorial_statistical_summary,
    build_statistical_summary,
)


def _lineup_report_entry(payload: dict) -> dict:
    summary = dict(payload["summary"])
    logs = payload["session"].get("logs", [])
    first_log = logs[0] if logs else {}
    summary["session_id"] = first_log.get("session_id")
    summary["layout_id"] = first_log.get("layout_id")
    summary["layout_repeat"] = first_log.get("layout_repeat")
    summary["base_seed"] = first_log.get("base_seed")
    summary["seed"] = first_log.get("seed")
    return summary


def build_report(cross_play_result: dict, confirmatory_baseline: str = CONFIRMATORY_BASELINE) -> dict:
    lineups = cross_play_result.get("lineups", {})
    agent_summary = cross_play_result.get("agent_summary", {})
    statistical_summary = build_statistical_summary(
        cross_play_result,
        confirmatory_baseline=confirmatory_baseline,
    )
    ranking = sorted(
        (
            {
                "agent": agent,
                "mean_profit": summary["mean_profit"],
                "cvar_5": summary["cvar_5"],
                "cvar_5_tail_size": summary.get("cvar_5_tail_size", 0),
                "cvar_5_is_fallback": summary.get("cvar_5_is_fallback", False),
                "cvar_5_low_support": summary.get("cvar_5_low_support", False) or summary.get("cvar_5_is_fallback", False),
                "ruin_probability": summary["ruin_probability"],
                "variance": summary["variance"],
                "win_rate": summary["win_rate"],
            }
            for agent, summary in agent_summary.items()
        ),
        key=lambda row: (
            row["cvar_5_low_support"],
            -row["mean_profit"],
            -row["cvar_5"],
            row["ruin_probability"],
            -row["cvar_5_tail_size"],
            row["agent"],
        ),
    )
    return {
        "agent_performance_table": agent_summary,
        "ranking": ranking,
        "ranking_policy": {
            "type": "descriptive_screening",
            "rank_keys": [
                "cvar_5_low_support_asc",
                "mean_profit_desc",
                "cvar_5_desc",
                "ruin_probability_asc",
                "cvar_5_tail_size_desc",
                "agent_asc",
            ],
            "notes": [
                "Ranking is a descriptive screening order for report presentation.",
                "Rows with low-support CVaR estimates are sorted behind adequately supported rows.",
                "Inferential claims must use the report's confirmatory_assessment section, not the ranking order.",
                "The inferential_statistics section provides the supporting two-sided diagnostics plus exploratory layout analysis.",
                "Variance is reported but does not affect ranking.",
            ],
        },
        "cross_play_results": {str(layout): _lineup_report_entry(payload) for layout, payload in lineups.items()},
        "profit_distribution_stats": {
            agent: {
                "mean_profit": summary["mean_profit"],
                "variance": summary["variance"],
                "cvar_5": summary["cvar_5"],
                "cvar_5_method": summary.get("cvar_5_method"),
                "cvar_5_effective_sample_size": summary.get("cvar_5_effective_sample_size", 0),
                "sample_count": summary.get("sample_count", 0),
                "profit_per_hand": summary["profit_per_hand"],
            }
            for agent, summary in agent_summary.items()
        },
        "ruin_risk_comparison": {
            agent: {
                "ruin_probability": summary["ruin_probability"],
                "ruin_event_count": summary.get("ruin_event_count", 0),
                "sample_count": summary.get("sample_count", 0),
                "session_completed_rate": summary["session_completed_rate"],
                "early_exit_rate": summary["early_exit_rate"],
            }
            for agent, summary in agent_summary.items()
        },
        "design_diagnostics": statistical_summary["design_diagnostics"],
        "inferential_statistics": statistical_summary["inferential_statistics"],
        "confirmatory_assessment": statistical_summary["confirmatory_assessment"],
        "confirmatory_baseline": confirmatory_baseline,
    }


def build_factorial_report(cross_play_result: dict, *, model_panel, strategy_panel) -> dict:
    lineups = cross_play_result.get("lineups", {})
    statistical_summary = build_factorial_statistical_summary(cross_play_result)
    mean_profit_by_model = statistical_summary["mean_profit"]["by_model"]
    cvar_by_model = statistical_summary["secondary_metrics"]["cvar_5"]["by_model"]
    ruin_by_model = statistical_summary["secondary_metrics"]["ruin_probability"]["by_model"]
    agent_summary = {}
    for model_id in mean_profit_by_model:
        agent_summary[model_id] = {
            "mean_profit": mean_profit_by_model[model_id]["estimate"],
            "cvar_5": cvar_by_model.get(model_id, {}).get("estimate", 0.0),
            "ruin_probability": ruin_by_model.get(model_id, {}).get("estimate", 0.0),
            "sample_count": mean_profit_by_model[model_id].get("sample_count", 0),
            "block_count": mean_profit_by_model[model_id].get("block_count", 0),
        }
    ranking = sorted(
        (
            {
                "agent": model_id,
                "mean_profit": summary["mean_profit"],
                "cvar_5": summary["cvar_5"],
                "ruin_probability": summary["ruin_probability"],
            }
            for model_id, summary in agent_summary.items()
        ),
        key=lambda row: (-row["mean_profit"], -row["cvar_5"], row["ruin_probability"], row["agent"]),
    )
    return {
        "study_type": "blocked_factorial_llm",
        "model_panel": [
            {
                "model_id": entry["model_id"] if isinstance(entry, dict) else str(entry),
                "parameter_size_b": entry.get("parameter_size_b", 0.0) if isinstance(entry, dict) else 0.0,
            }
            for entry in model_panel
        ],
        "strategy_panel": [
            {
                "strategy_id": entry["strategy_id"] if isinstance(entry, dict) else entry.strategy_id,
                "label": entry["label"] if isinstance(entry, dict) else entry.label,
            }
            for entry in strategy_panel
        ],
        "agent_performance_table": agent_summary,
        "ranking": ranking,
        "ranking_policy": {
            "type": "model_marginal_mean_profit",
            "notes": [
                "Ranking is computed over model-marginal mean profit across all prompt strategies.",
                "The primary factorial claim must use rq_model_vs_strategy.effect_decomposition rather than this ranking.",
            ],
        },
        "cross_play_results": {str(layout): _lineup_report_entry(payload) for layout, payload in lineups.items()},
        "rq_model_vs_strategy": statistical_summary,
    }
