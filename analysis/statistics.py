from __future__ import annotations

import math
from collections import defaultdict
from itertools import combinations
from random import Random
from statistics import fmean


CVaR_ALPHA = 0.05
BOOTSTRAP_ITERATIONS = 1000
PERMUTATION_ITERATIONS = 1000
MIN_CVAR_SESSION_COUNT = 100
MIN_RUIN_SESSION_COUNT = 30
WILSON_Z_95 = 1.959963984540054
CONFIRMATORY_BASELINE = "RandomAgent"
CONFIRMATORY_ALPHA = 0.05
CONFIRMATORY_METRIC_COUNT = 3


def _mean(values) -> float:
    return fmean(values) if values else 0.0


def bootstrap_ci(data, metric_func, iterations: int = BOOTSTRAP_ITERATIONS, alpha: float = 0.05, seed: int = 42) -> tuple[float, float, float]:
    if not data:
        return 0.0, 0.0, 0.0
    rng = Random(seed)
    sample_count = len(data)
    estimates = []
    for _ in range(iterations):
        sample = [data[rng.randrange(sample_count)] for _ in range(sample_count)]
        estimates.append(metric_func(sample))
    estimates.sort()
    lower_index = max(0, int(math.floor((iterations - 1) * (alpha / 2))))
    upper_index = min(iterations - 1, int(math.ceil((iterations - 1) * (1 - (alpha / 2)))))
    return metric_func(data), estimates[lower_index], estimates[upper_index]


def empirical_expected_shortfall(values: list[float], alpha: float = CVaR_ALPHA) -> tuple[float, float, int]:
    if not values:
        return 0.0, 0.0, 0
    sorted_values = sorted(values)
    tail_mass = len(sorted_values) * alpha
    if tail_mass <= 0:
        return 0.0, 0.0, 0
    base_count = int(math.floor(tail_mass))
    fractional = tail_mass - base_count
    weighted_total = sum(sorted_values[:base_count])
    support_count = base_count
    if fractional > 0 and base_count < len(sorted_values):
        weighted_total += sorted_values[base_count] * fractional
        support_count += 1
    elif base_count == 0:
        weighted_total += sorted_values[0] * tail_mass
        support_count = 1
    return weighted_total / tail_mass, tail_mass, support_count


def build_session_observations(cross_play_result: dict) -> list[dict]:
    observations = []
    for lineup_index, (lineup_key, payload) in enumerate(cross_play_result.get("lineups", {}).items()):
        session = payload["session"]
        summary = payload["summary"]
        logs = session.get("logs", [])
        first_log = logs[0] if logs else {}
        layout = tuple(summary.get("layout", ()))
        layout_label = " > ".join(layout)
        layout_repeat = first_log.get("layout_repeat")
        base_seed = first_log.get("base_seed")
        if layout_repeat is None and isinstance(lineup_key, tuple) and len(lineup_key) == 2 and isinstance(lineup_key[1], int):
            layout_repeat = lineup_key[1]
        layout_repeat = int(layout_repeat or 0)
        session_id = int(first_log.get("session_id", lineup_index))
        layout_id = int(first_log.get("layout_id", session_id))
        seed = first_log.get("seed")
        cluster_id = f"{base_seed}|{layout_label}" if base_seed is not None else layout_label
        strategy_id = summary.get("strategy_id", first_log.get("strategy_id", ""))
        strategy_label = summary.get("strategy_label", first_log.get("strategy_label", ""))
        prompt_sha256 = summary.get("prompt_sha256", first_log.get("prompt_sha256", ""))
        seat_to_model_id = summary.get("seat_to_model_id", {})
        factorial_block_id = summary.get("factorial_block_id") or first_log.get("factorial_block_id") or ""
        total_hands = max(1, len(session.get("hand_outcomes", [])))
        showdown_success_count = summary.get("showdown_success_count", 0)
        for seat, agent in summary["seat_to_name"].items():
            survived = total_hands - summary["early_exits"][seat]
            observations.append(
                {
                    "base_seed": base_seed,
                    "cluster_id": cluster_id,
                    "session_id": session_id,
                    "layout_id": layout_id,
                    "layout_repeat": layout_repeat,
                    "layout": layout_label,
                    "seed": seed,
                    "seat": int(seat),
                    "agent": agent,
                    "model_id": str(seat_to_model_id.get(seat, agent)),
                    "strategy_id": str(strategy_id),
                    "strategy_label": str(strategy_label),
                    "prompt_sha256": str(prompt_sha256),
                    "factorial_block_id": str(factorial_block_id),
                    "profit": float(summary["profit_by_seat"][seat]),
                    "ruin": 1 if session["seats"][seat].bankroll <= 0 else 0,
                    "win_rate": float(summary["win_by_seat"][seat]) / total_hands,
                    "total_hands": total_hands,
                    "hands_survived": float(survived),
                    "session_completed": 1 if survived == total_hands else 0,
                    "early_exit_rate": float(summary["early_exits"][seat]) / total_hands,
                    "showdown_frequency": float(showdown_success_count) / total_hands,
                }
            )
    return observations


def _clustered_values(observations: list[dict], metric: str) -> dict[str, dict[int, dict[str, float]]]:
    paired = defaultdict(lambda: defaultdict(dict))
    for observation in observations:
        paired[str(observation["cluster_id"])][int(observation["session_id"])][str(observation["agent"])] = float(observation[metric])
    return paired


def _sign_flip_p_value(differences: list[float], iterations: int = PERMUTATION_ITERATIONS, seed: int = 0) -> float:
    if not differences:
        return 1.0
    observed = abs(_mean(differences))
    if observed == 0:
        return 1.0
    rng = Random(seed)
    exceed_count = 0
    for _ in range(iterations):
        permuted = [value if rng.random() < 0.5 else -value for value in differences]
        if abs(_mean(permuted)) >= observed:
            exceed_count += 1
    return (exceed_count + 1) / (iterations + 1)


def _wilson_interval(successes: int, sample_count: int, z: float = WILSON_Z_95) -> tuple[float, float]:
    if sample_count <= 0:
        return 0.0, 0.0
    proportion = successes / sample_count
    denominator = 1 + ((z * z) / sample_count)
    center = (proportion + ((z * z) / (2 * sample_count))) / denominator
    margin = (z / denominator) * math.sqrt((proportion * (1 - proportion) / sample_count) + ((z * z) / (4 * sample_count * sample_count)))
    return max(0.0, center - margin), min(1.0, center + margin)


def _paired_cvar_difference(sample_pairs: list[tuple[float, float]], alpha: float = CVaR_ALPHA) -> float:
    left = [left_value for left_value, _ in sample_pairs]
    right = [right_value for _, right_value in sample_pairs]
    left_estimate, _, _ = empirical_expected_shortfall(left, alpha=alpha)
    right_estimate, _, _ = empirical_expected_shortfall(right, alpha=alpha)
    return left_estimate - right_estimate


def _paired_mean_difference(sample_pairs: list[tuple[float, float]]) -> float:
    return _mean([left_value - right_value for left_value, right_value in sample_pairs])


def _paired_probability_difference(sample_pairs: list[tuple[int, int]]) -> float:
    return _mean([left_value - right_value for left_value, right_value in sample_pairs])


def _flatten_cluster_samples(cluster_samples: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    return [pair for cluster in cluster_samples for pair in cluster]


def _cluster_bootstrap_ci(cluster_samples, metric_func, iterations: int = BOOTSTRAP_ITERATIONS, alpha: float = 0.05, seed: int = 42) -> tuple[float, float, float]:
    if not cluster_samples:
        return 0.0, 0.0, 0.0
    rng = Random(seed)
    cluster_count = len(cluster_samples)
    estimates = []
    for _ in range(iterations):
        sampled_clusters = [cluster_samples[rng.randrange(cluster_count)] for _ in range(cluster_count)]
        estimates.append(metric_func(_flatten_cluster_samples(sampled_clusters)))
    estimates.sort()
    lower_index = max(0, int(math.floor((iterations - 1) * (alpha / 2))))
    upper_index = min(iterations - 1, int(math.ceil((iterations - 1) * (1 - (alpha / 2)))))
    estimate = metric_func(_flatten_cluster_samples(cluster_samples))
    return estimate, estimates[lower_index], estimates[upper_index]


def _anova_components(groups: dict[str, list[float]]) -> tuple[float | None, float | None]:
    if len(groups) < 2:
        return None, None
    all_values = [value for values in groups.values() for value in values]
    total_count = len(all_values)
    if total_count <= len(groups):
        return None, None
    grand_mean = _mean(all_values)
    between_sum = 0.0
    within_sum = 0.0
    for values in groups.values():
        group_mean = _mean(values)
        between_sum += len(values) * ((group_mean - grand_mean) ** 2)
        within_sum += sum((value - group_mean) ** 2 for value in values)
    if within_sum <= 0:
        return None, None
    degrees_between = len(groups) - 1
    degrees_within = total_count - len(groups)
    if degrees_within <= 0:
        return None, None
    f_statistic = (between_sum / degrees_between) / (within_sum / degrees_within)
    eta_squared = between_sum / (between_sum + within_sum) if (between_sum + within_sum) > 0 else None
    return f_statistic, eta_squared


def _layout_permutation_p_value(groups: dict[str, list[float]], iterations: int = PERMUTATION_ITERATIONS, seed: int = 0) -> float | None:
    observed_statistic, _ = _anova_components(groups)
    if observed_statistic is None:
        return None
    rng = Random(seed)
    group_names = list(groups)
    group_sizes = [len(groups[name]) for name in group_names]
    pooled_values = [value for name in group_names for value in groups[name]]
    exceed_count = 0
    for _ in range(iterations):
        shuffled = list(pooled_values)
        rng.shuffle(shuffled)
        permuted = {}
        cursor = 0
        for name, size in zip(group_names, group_sizes, strict=True):
            permuted[name] = shuffled[cursor : cursor + size]
            cursor += size
        permuted_statistic, _ = _anova_components(permuted)
        if permuted_statistic is not None and permuted_statistic >= observed_statistic:
            exceed_count += 1
    return (exceed_count + 1) / (iterations + 1)


def _pairwise_agent_results(
    observations: list[dict],
    metric: str,
    metric_func,
    seed_offset: int,
    include_permutation: bool,
    alpha: float = 0.05,
) -> dict[str, dict]:
    by_cluster = _clustered_values(observations, metric)
    agents = sorted({str(observation["agent"]) for observation in observations})
    results = {}
    for pair_index, (left, right) in enumerate(combinations(agents, 2)):
        cluster_samples = []
        cluster_means = []
        for cluster_sessions in by_cluster.values():
            paired = [
                (session[left], session[right])
                for session in cluster_sessions.values()
                if left in session and right in session
            ]
            if not paired:
                continue
            cluster_samples.append(paired)
            cluster_means.append(_mean([left_value - right_value for left_value, right_value in paired]))
        if not cluster_samples:
            continue
        flattened_pairs = _flatten_cluster_samples(cluster_samples)
        estimate, ci_lower, ci_upper = _cluster_bootstrap_ci(
            cluster_samples,
            metric_func,
            alpha=alpha,
            seed=seed_offset + pair_index,
        )
        result = {
            "left_agent": left,
            "right_agent": right,
            "estimate": estimate,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "sample_count": len(flattened_pairs),
            "cluster_count": len(cluster_samples),
            "two_sided": True,
        }
        if include_permutation:
            result["p_value_two_sided"] = _sign_flip_p_value(cluster_means, seed=seed_offset + 10_000 + pair_index)
        results[f"{left}__minus__{right}"] = result
    pair_count = len(results)
    for result in results.values():
        raw_p_value = result.get("p_value_two_sided")
        if raw_p_value is not None:
            result["p_value_two_sided_bonferroni"] = min(1.0, raw_p_value * max(1, pair_count))
    return results


def analyze_profit_differences(observations: list[dict]) -> dict:
    return {
        "metric": "mean_profit",
        "method": "paired_cluster_bootstrap_with_cluster_mean_sign_flip_permutation",
        "two_sided": True,
        "pairwise": _pairwise_agent_results(
            observations,
            metric="profit",
            metric_func=_paired_mean_difference,
            seed_offset=1_000,
            include_permutation=True,
        ),
    }


def analyze_tail_risk(observations: list[dict], alpha: float = CVaR_ALPHA) -> dict:
    profits_by_agent = defaultdict(list)
    clusters_by_agent = defaultdict(lambda: defaultdict(list))
    for observation in observations:
        agent = str(observation["agent"])
        profit = float(observation["profit"])
        profits_by_agent[agent].append(profit)
        clusters_by_agent[agent][str(observation["cluster_id"])].append(profit)
    per_agent = {}
    for agent_index, agent in enumerate(sorted(profits_by_agent)):
        profits = profits_by_agent[agent]
        cluster_samples = list(clusters_by_agent[agent].values())
        estimate, ci_lower, ci_upper = _cluster_bootstrap_ci(
            [[(value, 0.0) for value in cluster] for cluster in cluster_samples],
            lambda sample: empirical_expected_shortfall([value for value, _ in sample], alpha=alpha)[0],
            seed=2_000 + agent_index,
        )
        _, tail_mass, support_count = empirical_expected_shortfall(profits, alpha=alpha)
        per_agent[agent] = {
            "estimate": estimate,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "sample_count": len(profits),
            "cluster_count": len(cluster_samples),
            "effective_tail_mass": tail_mass,
            "support_count": support_count,
            "inferential_ready": len(profits) >= MIN_CVAR_SESSION_COUNT,
            "recommended_min_sample_count": MIN_CVAR_SESSION_COUNT,
            "two_sided": True,
        }
    return {
        "metric": f"empirical_expected_shortfall_alpha_{alpha:.2f}",
        "method": "cluster_bootstrap_confidence_interval",
        "two_sided": True,
        "per_agent": per_agent,
        "pairwise": _pairwise_agent_results(
            observations,
            metric="profit",
            metric_func=lambda sample: _paired_cvar_difference(sample, alpha=alpha),
            seed_offset=3_000,
            include_permutation=False,
        ),
    }


def analyze_ruin_probability(observations: list[dict]) -> dict:
    ruin_by_agent = defaultdict(list)
    clusters_by_agent = defaultdict(lambda: defaultdict(list))
    for observation in observations:
        agent = str(observation["agent"])
        ruin_value = int(observation["ruin"])
        ruin_by_agent[agent].append(ruin_value)
        clusters_by_agent[agent][str(observation["cluster_id"])].append(ruin_value)
    per_agent = {}
    for agent in sorted(ruin_by_agent):
        ruin_values = ruin_by_agent[agent]
        event_count = int(sum(ruin_values))
        ci_lower, ci_upper = _wilson_interval(event_count, len(ruin_values))
        per_agent[agent] = {
            "estimate": _mean(ruin_values),
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "sample_count": len(ruin_values),
            "cluster_count": len(clusters_by_agent[agent]),
            "event_count": event_count,
            "inferential_ready": len(ruin_values) >= MIN_RUIN_SESSION_COUNT,
            "recommended_min_sample_count": MIN_RUIN_SESSION_COUNT,
            "two_sided": True,
        }
    return {
        "metric": "ruin_probability",
        "method": "wilson_interval_and_paired_cluster_bootstrap_difference",
        "two_sided": True,
        "per_agent": per_agent,
        "pairwise": _pairwise_agent_results(
            observations,
            metric="ruin",
            metric_func=_paired_probability_difference,
            seed_offset=4_000,
            include_permutation=False,
        ),
    }


def analyze_layout_effects(observations: list[dict]) -> dict:
    grouped = defaultdict(lambda: defaultdict(list))
    for observation in observations:
        grouped[str(observation["agent"])][str(observation["layout"])].append(float(observation["profit"]))
    per_agent = {}
    for agent_index, agent in enumerate(sorted(grouped)):
        groups = grouped[agent]
        repeat_counts = [len(values) for values in groups.values()]
        if len(groups) < 2:
            per_agent[agent] = {
                "identifiable": False,
                "reason": "layout_effect_requires_at_least_two_distinct_layouts",
                "layout_count": len(groups),
                "min_repetitions_per_layout": min(repeat_counts) if repeat_counts else 0,
            }
            continue
        if repeat_counts and min(repeat_counts) < 2:
            per_agent[agent] = {
                "identifiable": False,
                "reason": "layout_effect_requires_repeated_sessions_per_layout",
                "layout_count": len(groups),
                "min_repetitions_per_layout": min(repeat_counts),
            }
            continue
        f_statistic, eta_squared = _anova_components(groups)
        p_value = _layout_permutation_p_value(groups, seed=5_000 + agent_index)
        per_agent[agent] = {
            "identifiable": f_statistic is not None,
            "layout_count": len(groups),
            "min_repetitions_per_layout": min(repeat_counts) if repeat_counts else 0,
            "max_repetitions_per_layout": max(repeat_counts) if repeat_counts else 0,
            "f_statistic": f_statistic,
            "eta_squared": eta_squared,
            "p_value_two_sided": p_value,
            "method": "layout_permutation_anova",
        }
    return {
        "metric": "layout_effect_on_profit",
        "method": "layout_permutation_anova",
        "two_sided": True,
        "per_agent": per_agent,
    }


def _orient_pairwise_result(pairwise: dict[str, dict], agent: str, baseline: str) -> dict | None:
    direct_key = f"{agent}__minus__{baseline}"
    reverse_key = f"{baseline}__minus__{agent}"
    if direct_key in pairwise:
        record = pairwise[direct_key]
        return {
            "agent": agent,
            "baseline": baseline,
            "estimate": record["estimate"],
            "ci_lower": record["ci_lower"],
            "ci_upper": record["ci_upper"],
            "sample_count": record.get("sample_count", 0),
            "cluster_count": record.get("cluster_count", 0),
            "p_value_two_sided": record.get("p_value_two_sided"),
        }
    if reverse_key in pairwise:
        record = pairwise[reverse_key]
        return {
            "agent": agent,
            "baseline": baseline,
            "estimate": -record["estimate"],
            "ci_lower": -record["ci_upper"],
            "ci_upper": -record["ci_lower"],
            "sample_count": record.get("sample_count", 0),
            "cluster_count": record.get("cluster_count", 0),
            "p_value_two_sided": record.get("p_value_two_sided"),
        }
    return None


def build_confirmatory_assessment(
    observations: list[dict],
    inferential_statistics: dict,
    baseline_agent: str = CONFIRMATORY_BASELINE,
) -> dict:
    agents = sorted({str(observation["agent"]) for observation in observations if str(observation["agent"]) != baseline_agent})
    pair_count = max(1, len(agents))
    per_metric_alpha = CONFIRMATORY_ALPHA / CONFIRMATORY_METRIC_COUNT
    per_pair_alpha = per_metric_alpha / pair_count
    adjusted_tail_pairwise = _pairwise_agent_results(
        observations,
        metric="profit",
        metric_func=lambda sample: _paired_cvar_difference(sample, alpha=CVaR_ALPHA),
        seed_offset=30_000,
        include_permutation=False,
        alpha=per_pair_alpha,
    )
    adjusted_ruin_pairwise = _pairwise_agent_results(
        observations,
        metric="ruin",
        metric_func=_paired_probability_difference,
        seed_offset=40_000,
        include_permutation=False,
        alpha=per_pair_alpha,
    )
    mean_pairwise = inferential_statistics["rq1_mean_profit"]["pairwise"]
    per_agent = {}
    for agent in agents:
        mean_profit = _orient_pairwise_result(mean_pairwise, agent, baseline_agent)
        cvar_5 = _orient_pairwise_result(adjusted_tail_pairwise, agent, baseline_agent)
        ruin_probability = _orient_pairwise_result(adjusted_ruin_pairwise, agent, baseline_agent)
        mean_profit_supported = bool(
            mean_profit
            and mean_profit["estimate"] > 0
            and (mean_profit.get("p_value_two_sided") or 1.0) <= per_pair_alpha
        )
        cvar_5_noninferior = bool(cvar_5 and cvar_5["ci_lower"] >= 0)
        ruin_probability_noninferior = bool(ruin_probability and ruin_probability["ci_upper"] <= 0)
        per_agent[agent] = {
            "claim_supported": mean_profit_supported and cvar_5_noninferior and ruin_probability_noninferior,
            "mean_profit_supported": mean_profit_supported,
            "cvar_5_noninferior": cvar_5_noninferior,
            "ruin_probability_noninferior": ruin_probability_noninferior,
            "mean_profit": mean_profit,
            "cvar_5": cvar_5,
            "ruin_probability": ruin_probability,
        }
    return {
        "baseline": baseline_agent,
        "familywise_alpha": CONFIRMATORY_ALPHA,
        "metric_count": CONFIRMATORY_METRIC_COUNT,
        "per_metric_alpha": per_metric_alpha,
        "pairwise_agent_count": pair_count,
        "per_pair_alpha_for_interval_checks": per_pair_alpha,
        "gatekeeping_rule": "mean_profit_supported and cvar_5_noninferior and ruin_probability_noninferior",
        "per_agent": per_agent,
    }


def build_design_diagnostics(observations: list[dict]) -> dict:
    session_count_by_agent = defaultdict(int)
    cluster_count_by_agent = defaultdict(set)
    session_layouts = {}
    for observation in observations:
        session_count_by_agent[str(observation["agent"])] += 1
        cluster_count_by_agent[str(observation["agent"])].add(str(observation["cluster_id"]))
        session_layouts[int(observation["session_id"])] = str(observation["layout"])
    layout_session_counts = defaultdict(int)
    for layout in session_layouts.values():
        layout_session_counts[layout] += 1
    notes = []
    if session_count_by_agent and min(session_count_by_agent.values()) < MIN_CVAR_SESSION_COUNT:
        notes.append("CVaR inference is unstable below the recommended 100 sessions per agent.")
    if session_count_by_agent and min(session_count_by_agent.values()) < MIN_RUIN_SESSION_COUNT:
        notes.append("Ruin-probability inference is low-power below the recommended 30 sessions per agent.")
    if layout_session_counts and min(layout_session_counts.values()) < 2:
        notes.append("Layout-effect testing requires at least two repeated sessions per distinct layout.")
    return {
        "pairing_unit": "session_id",
        "tests_are_two_sided": True,
        "session_count_by_agent": dict(sorted(session_count_by_agent.items())),
        "cluster_count_by_agent": {agent: len(cluster_ids) for agent, cluster_ids in sorted(cluster_count_by_agent.items())},
        "layout_count": len(layout_session_counts),
        "layout_repetition_min": min(layout_session_counts.values()) if layout_session_counts else 0,
        "layout_repetition_max": max(layout_session_counts.values()) if layout_session_counts else 0,
        "recommended_cvar_session_count": MIN_CVAR_SESSION_COUNT,
        "recommended_ruin_session_count": MIN_RUIN_SESSION_COUNT,
        "notes": notes,
    }


def build_statistical_summary(
    cross_play_result: dict,
    confirmatory_baseline: str = CONFIRMATORY_BASELINE,
) -> dict:
    observations = build_session_observations(cross_play_result)
    inferential_statistics = {
        "rq1_mean_profit": analyze_profit_differences(observations),
        "rq2_tail_risk": analyze_tail_risk(observations),
        "rq3_ruin_probability": analyze_ruin_probability(observations),
        "rq4_layout_effect": analyze_layout_effects(observations),
    }
    return {
        "design_diagnostics": build_design_diagnostics(observations),
        "inferential_statistics": inferential_statistics,
        "confirmatory_assessment": build_confirmatory_assessment(
            observations,
            inferential_statistics,
            baseline_agent=confirmatory_baseline,
        ),
    }


def _cluster_bootstrap_metric(
    clusters: list[list[float]],
    metric_func,
    *,
    iterations: int = BOOTSTRAP_ITERATIONS,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    if not clusters:
        return 0.0, 0.0, 0.0
    rng = Random(seed)
    cluster_count = len(clusters)
    estimates = []
    flattened = [value for cluster in clusters for value in cluster]
    for _ in range(iterations):
        sampled = [clusters[rng.randrange(cluster_count)] for _ in range(cluster_count)]
        estimates.append(metric_func([value for cluster in sampled for value in cluster]))
    estimates.sort()
    lower_index = max(0, int(math.floor((iterations - 1) * (alpha / 2))))
    upper_index = min(iterations - 1, int(math.ceil((iterations - 1) * (1 - (alpha / 2)))))
    return metric_func(flattened), estimates[lower_index], estimates[upper_index]


def _group_factorial_blocks(
    observations: list[dict],
) -> tuple[list[str], list[str], dict[str, dict[str, dict[str, float]]], int]:
    blocks = defaultdict(lambda: defaultdict(dict))
    model_levels = sorted({str(observation["model_id"]) for observation in observations if observation.get("model_id")})
    strategy_levels = sorted({str(observation["strategy_id"]) for observation in observations if observation.get("strategy_id")})
    dropped = 0
    for observation in observations:
        block_id = str(observation.get("factorial_block_id") or "")
        model_id = str(observation.get("model_id") or "")
        strategy_id = str(observation.get("strategy_id") or "")
        if not block_id or not model_id or not strategy_id:
            continue
        blocks[block_id][strategy_id][model_id] = float(observation["profit"])

    complete_blocks = {}
    expected_cell_count = len(model_levels) * len(strategy_levels)
    for block_id, strategy_map in blocks.items():
        cell_count = sum(len(model_map) for model_map in strategy_map.values())
        if len(strategy_map) != len(strategy_levels) or cell_count != expected_cell_count:
            dropped += 1
            continue
        complete_blocks[block_id] = strategy_map
    return model_levels, strategy_levels, complete_blocks, dropped


def analyze_model_strategy_effects(observations: list[dict]) -> dict:
    model_levels, strategy_levels, blocks, dropped_blocks = _group_factorial_blocks(observations)
    block_ids = sorted(blocks)
    if not block_ids or not model_levels or not strategy_levels:
        return {
            "complete_block_count": 0,
            "dropped_block_count": dropped_blocks,
            "model_levels": model_levels,
            "strategy_levels": strategy_levels,
            "terms": {},
            "dominant_main_effect": {"term": "", "partial_eta_squared": 0.0},
            "dominant_effect_overall": {"term": "", "partial_eta_squared": 0.0},
        }

    values = []
    for block_id in block_ids:
        for strategy_id in strategy_levels:
            for model_id in model_levels:
                values.append((block_id, model_id, strategy_id, blocks[block_id][strategy_id][model_id]))

    grand_mean = _mean([value for _, _, _, value in values])
    block_means = {
        block_id: _mean([value for bid, _, _, value in values if bid == block_id])
        for block_id in block_ids
    }
    model_means = {
        model_id: _mean([value for _, mid, _, value in values if mid == model_id])
        for model_id in model_levels
    }
    strategy_means = {
        strategy_id: _mean([value for _, _, sid, value in values if sid == strategy_id])
        for strategy_id in strategy_levels
    }
    cell_means = {
        strategy_id: {
            model_id: _mean(
                [value for _, mid, sid, value in values if mid == model_id and sid == strategy_id]
            )
            for model_id in model_levels
        }
        for strategy_id in strategy_levels
    }

    block_count = len(block_ids)
    model_count = len(model_levels)
    strategy_count = len(strategy_levels)
    ss_block = model_count * strategy_count * sum((mean - grand_mean) ** 2 for mean in block_means.values())
    ss_model = strategy_count * block_count * sum((mean - grand_mean) ** 2 for mean in model_means.values())
    ss_strategy = model_count * block_count * sum((mean - grand_mean) ** 2 for mean in strategy_means.values())
    ss_interaction = block_count * sum(
        (
            cell_means[strategy_id][model_id]
            - model_means[model_id]
            - strategy_means[strategy_id]
            + grand_mean
        )
        ** 2
        for strategy_id in strategy_levels
        for model_id in model_levels
    )

    ss_error = 0.0
    for block_id, model_id, strategy_id, value in values:
        fitted = (
            grand_mean
            + (block_means[block_id] - grand_mean)
            + (model_means[model_id] - grand_mean)
            + (strategy_means[strategy_id] - grand_mean)
            + (cell_means[strategy_id][model_id] - model_means[model_id] - strategy_means[strategy_id] + grand_mean)
        )
        ss_error += (value - fitted) ** 2

    df_model = max(0, model_count - 1)
    df_strategy = max(0, strategy_count - 1)
    df_interaction = max(0, df_model * df_strategy)
    df_error = max(0, (block_count - 1) * ((model_count * strategy_count) - 1))
    mse_error = (ss_error / df_error) if df_error and ss_error > 0 else 0.0

    def term_record(name: str, ss_value: float, df_value: int) -> dict:
        mean_square = (ss_value / df_value) if df_value else 0.0
        f_statistic = (mean_square / mse_error) if mse_error > 0 and df_value else None
        partial_eta_squared = ss_value / (ss_value + ss_error) if (ss_value + ss_error) > 0 else 0.0
        return {
            "term": name,
            "sum_squares": ss_value,
            "df": df_value,
            "mean_square": mean_square,
            "f_statistic": f_statistic,
            "partial_eta_squared": partial_eta_squared,
        }

    terms = {
        "model": term_record("model", ss_model, df_model),
        "strategy": term_record("strategy", ss_strategy, df_strategy),
        "interaction": term_record("interaction", ss_interaction, df_interaction),
    }
    dominant_main_effect = max(
        (terms["model"], terms["strategy"]),
        key=lambda record: record["partial_eta_squared"],
    )
    dominant_effect_overall = max(
        terms.values(),
        key=lambda record: record["partial_eta_squared"],
    )
    return {
        "complete_block_count": block_count,
        "dropped_block_count": dropped_blocks,
        "model_levels": model_levels,
        "strategy_levels": strategy_levels,
        "terms": terms,
        "degrees_of_freedom": {
            "block": max(0, block_count - 1),
            "model": df_model,
            "strategy": df_strategy,
            "interaction": df_interaction,
            "error": df_error,
        },
        "mean_square_error": mse_error,
        "cell_means": cell_means,
        "dominant_main_effect": {
            "term": dominant_main_effect["term"],
            "partial_eta_squared": dominant_main_effect["partial_eta_squared"],
        },
        "dominant_effect_overall": {
            "term": dominant_effect_overall["term"],
            "partial_eta_squared": dominant_effect_overall["partial_eta_squared"],
        },
    }


def _factor_clusters(observations: list[dict], factor_key: str, metric_key: str) -> dict[str, list[list[float]]]:
    grouped = defaultdict(lambda: defaultdict(list))
    for observation in observations:
        factor_value = str(observation.get(factor_key) or "")
        block_id = str(observation.get("factorial_block_id") or "")
        if not factor_value or not block_id:
            continue
        grouped[factor_value][block_id].append(float(observation[metric_key]))
    return {
        factor_value: [cluster for _, cluster in sorted(block_map.items())]
        for factor_value, block_map in grouped.items()
    }


def _summarize_factor_metric(
    observations: list[dict],
    *,
    factor_key: str,
    metric_name: str,
    metric_func,
    seed_offset: int,
) -> dict[str, dict]:
    result = {}
    for index, (factor_value, clusters) in enumerate(sorted(_factor_clusters(observations, factor_key, metric_name).items())):
        estimate, ci_lower, ci_upper = _cluster_bootstrap_metric(
            clusters,
            metric_func,
            seed=seed_offset + index,
        )
        result[factor_value] = {
            "estimate": estimate,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "sample_count": sum(len(cluster) for cluster in clusters),
            "block_count": len(clusters),
        }
    return result


def build_factorial_statistical_summary(cross_play_result: dict) -> dict:
    observations = build_session_observations(cross_play_result)
    mean_profit_by_model = _summarize_factor_metric(
        observations,
        factor_key="model_id",
        metric_name="profit",
        metric_func=_mean,
        seed_offset=60_000,
    )
    mean_profit_by_strategy = _summarize_factor_metric(
        observations,
        factor_key="strategy_id",
        metric_name="profit",
        metric_func=_mean,
        seed_offset=61_000,
    )
    cvar_by_model = _summarize_factor_metric(
        observations,
        factor_key="model_id",
        metric_name="profit",
        metric_func=lambda values: empirical_expected_shortfall(values, alpha=CVaR_ALPHA)[0],
        seed_offset=62_000,
    )
    cvar_by_strategy = _summarize_factor_metric(
        observations,
        factor_key="strategy_id",
        metric_name="profit",
        metric_func=lambda values: empirical_expected_shortfall(values, alpha=CVaR_ALPHA)[0],
        seed_offset=63_000,
    )
    ruin_by_model = _summarize_factor_metric(
        observations,
        factor_key="model_id",
        metric_name="ruin",
        metric_func=_mean,
        seed_offset=64_000,
    )
    ruin_by_strategy = _summarize_factor_metric(
        observations,
        factor_key="strategy_id",
        metric_name="ruin",
        metric_func=_mean,
        seed_offset=65_000,
    )
    mean_profit_cells = defaultdict(dict)
    for observation in observations:
        model_id = str(observation.get("model_id") or "")
        strategy_id = str(observation.get("strategy_id") or "")
        if model_id and strategy_id:
            mean_profit_cells[strategy_id].setdefault(model_id, []).append(float(observation["profit"]))
    return {
        "design": {
            "study_type": "blocked_factorial_llm",
            "primary_metric": "mean_profit",
            "secondary_metrics": ["cvar_5", "ruin_probability"],
            "block_key": "factorial_block_id",
        },
        "effect_decomposition": analyze_model_strategy_effects(observations),
        "mean_profit": {
            "by_model": mean_profit_by_model,
            "by_strategy": mean_profit_by_strategy,
            "cell_means": {
                strategy_id: {
                    model_id: _mean(values)
                    for model_id, values in sorted(model_map.items())
                }
                for strategy_id, model_map in sorted(mean_profit_cells.items())
            },
        },
        "secondary_metrics": {
            "cvar_5": {
                "by_model": cvar_by_model,
                "by_strategy": cvar_by_strategy,
            },
            "ruin_probability": {
                "by_model": ruin_by_model,
                "by_strategy": ruin_by_strategy,
            },
        },
    }
