from __future__ import annotations

from statistics import fmean, variance
import math


def _mean(values):
    return fmean(values) if values else 0.0


def _variance(values):
    return variance(values) if len(values) > 1 else 0.0


def _cvar_5(values):
    if not values:
        return 0.0, 0, False
    sorted_values = sorted(values)
    sample_count = len(sorted_values)
    cutoff = len(sorted_values) * 0.05
    base_count = int(math.floor(cutoff))
    fractional = cutoff - base_count
    weighted_total = sum(sorted_values[:base_count])
    support_count = base_count
    if fractional > 0 and base_count < sample_count:
        weighted_total += sorted_values[base_count] * fractional
        support_count += 1
    elif base_count == 0:
        weighted_total += sorted_values[0] * cutoff
        support_count = 1
    cvar_5 = weighted_total / cutoff if cutoff > 0 else 0.0
    low_support = support_count < 3
    return cvar_5, support_count, low_support


def summarize_lineup(layout, result: dict) -> dict:
    seats = result["seats"]
    hand_outcomes = result["hand_outcomes"]
    logs = result["logs"]
    initial_bankroll = result.get("initial_bankroll", 1000)
    seat_to_name = {seat: state.agent_name for seat, state in seats.items()}
    profits = {seat: state.bankroll - initial_bankroll for seat, state in seats.items()}
    wins = {seat: 0 for seat in seats}
    showdown_success_hands = set()
    showdown_proposals = {seat: 0 for seat in seats}
    showdown_accepts = {seat: 0 for seat in seats}
    showdown_rejects = {seat: 0 for seat in seats}
    showdown_ev_gains = {seat: [] for seat in seats}
    showdown_misplays = {seat: [] for seat in seats}
    forced_gwang_sell = {seat: 0 for seat in seats}
    early_exits = {seat: 0 for seat in seats}
    for entry in logs:
        event_name = str(entry["event"])
        if "FORCED_GWANG_SELL" in event_name:
            forced_gwang_sell[entry["seat"]] += 1
        if "SHOWDOWN_PROPOSED" in event_name:
            showdown_proposals[entry["seat"]] += 1
        elif "SHOWDOWN_ACCEPTED" in event_name:
            showdown_accepts[entry["seat"]] += 1
        elif "SHOWDOWN_REJECTED" in event_name:
            showdown_rejects[entry["seat"]] += 1
        elif "SHOWDOWN_EVAL" in event_name:
            showdown_ev_gains[entry["seat"]].append(float(entry.get("ev_gain", 0.0)))
            showdown_misplays[entry["seat"]].append(float(entry.get("misplay", 0.0)))
        elif "NAGARI" in event_name and entry.get("reason") == "showdown_success":
            showdown_success_hands.add(entry["hand_id"])
        if "DIE" in event_name:
            early_exits[entry["seat"]] += 1
    for hand_index, outcome in enumerate(hand_outcomes, start=1):
        if outcome.winner is not None:
            wins[outcome.winner] += 1
        if outcome.showdown_success:
            showdown_success_hands.add(hand_index)
    return {
        "layout": layout,
        "profit_by_seat": profits,
        "win_by_seat": wins,
        "showdown_success_count": len(showdown_success_hands),
        "showdown_proposals": showdown_proposals,
        "showdown_accepts": showdown_accepts,
        "showdown_rejects": showdown_rejects,
        "showdown_ev_gains": showdown_ev_gains,
        "showdown_misplays": showdown_misplays,
        "forced_gwang_sell": forced_gwang_sell,
        "early_exits": early_exits,
        "seat_to_name": seat_to_name,
    }


def summarize_agent_results(lineups: dict) -> dict[str, dict]:
    by_agent: dict[str, dict[str, list[float] | int]] = {}
    for _, payload in lineups.items():
        summary = payload["summary"]
        for seat, name in summary["seat_to_name"].items():
            agent = by_agent.setdefault(
                name,
                {
                    "profits": [],
                    "win_rates": [],
                    "hands_survived": [],
                    "session_completed": [],
                    "early_exit_rate": [],
                    "forced_gwang_sell_rate": [],
                    "showdown_frequency": [],
                    "proposal_rate": [],
                    "accept_rate": [],
                    "reject_rate": [],
                    "showdown_ev_gain": [],
                    "showdown_misplay_rate": [],
                    "ruin": [],
                },
            )
            profit = summary["profit_by_seat"][seat]
            agent["profits"].append(profit)
            total_hands = max(1, len(payload["session"]["hand_outcomes"]))
            wins = summary["win_by_seat"][seat]
            agent["win_rates"].append(wins / total_hands)
            survived = total_hands - summary["early_exits"][seat]
            agent["hands_survived"].append(float(survived))
            agent["session_completed"].append(1.0 if survived == total_hands else 0.0)
            agent["early_exit_rate"].append(summary["early_exits"][seat] / total_hands)
            agent["forced_gwang_sell_rate"].append(summary["forced_gwang_sell"][seat] / total_hands)
            showdown_success_count = summary.get("showdown_success_count", 0)
            showdown_proposals = summary.get("showdown_proposals", {seat: 0 for seat in summary["seat_to_name"]})
            showdown_accepts = summary.get("showdown_accepts", {seat: 0 for seat in summary["seat_to_name"]})
            showdown_rejects = summary.get("showdown_rejects", {seat: 0 for seat in summary["seat_to_name"]})
            showdown_ev_gains = summary.get("showdown_ev_gains", {seat: [] for seat in summary["seat_to_name"]})
            showdown_misplays = summary.get("showdown_misplays", {seat: [] for seat in summary["seat_to_name"]})
            agent["showdown_frequency"].append(showdown_success_count / total_hands)
            agent["proposal_rate"].append(showdown_proposals[seat] / total_hands)
            response_total = showdown_accepts[seat] + showdown_rejects[seat]
            if response_total:
                agent["accept_rate"].append(showdown_accepts[seat] / response_total)
                agent["reject_rate"].append(showdown_rejects[seat] / response_total)
            else:
                agent["accept_rate"].append(0.0)
                agent["reject_rate"].append(0.0)
            if showdown_ev_gains[seat]:
                agent["showdown_ev_gain"].append(_mean(showdown_ev_gains[seat]))
                agent["showdown_misplay_rate"].append(_mean(showdown_misplays[seat]))
            else:
                agent["showdown_ev_gain"].append(0.0)
                agent["showdown_misplay_rate"].append(0.0)
            agent["ruin"].append(1.0 if payload["session"]["seats"][seat].bankroll <= 0 else 0.0)

    formatted = {}
    for agent_name, values in by_agent.items():
        profits = values["profits"]
        total_hands = max(1.0, _mean(values["hands_survived"]))
        cvar_5, cvar_support_count, cvar_low_support = _cvar_5(profits)
        sample_count = len(profits)
        formatted[agent_name] = {
            "mean_profit": _mean(profits),
            "variance": _variance(profits),
            "cvar_5": cvar_5,
            "cvar_5_tail_size": cvar_support_count,
            "cvar_5_is_fallback": cvar_low_support,
            "cvar_5_low_support": cvar_low_support,
            "cvar_5_method": "empirical_expected_shortfall",
            "cvar_5_effective_sample_size": sample_count * 0.05,
            "ruin_probability": _mean(values["ruin"]),
            "ruin_event_count": int(sum(values["ruin"])),
            "win_rate": _mean(values["win_rates"]),
            "profit_per_hand": _mean(profits) / total_hands,
            "hands_survived": _mean(values["hands_survived"]),
            "session_completed_rate": _mean(values["session_completed"]),
            "early_exit_rate": _mean(values["early_exit_rate"]),
            "forced_gwang_sell_rate": _mean(values["forced_gwang_sell_rate"]),
            "showdown_frequency": _mean(values["showdown_frequency"]),
            "proposal_rate": _mean(values["proposal_rate"]),
            "accept_rate": _mean(values["accept_rate"]),
            "reject_rate": _mean(values["reject_rate"]),
            "showdown_ev_gain": _mean(values["showdown_ev_gain"]),
            "showdown_misplay_rate": _mean(values["showdown_misplay_rate"]),
            "sample_count": sample_count,
        }
    return formatted
