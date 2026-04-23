from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from analysis.statistics import build_session_observations
from logs.recorder import LogRecorder


def _serialize(value: Any):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def export_experiment_bundle(
    output_dir: str | Path,
    *,
    config: dict[str, Any],
    report: dict[str, Any],
    cross_play_result: dict[str, Any],
) -> dict[str, str]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    session_observations = build_session_observations(cross_play_result)

    report_path = root / "report.json"
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(_serialize(report), handle, ensure_ascii=False, indent=2, sort_keys=True)

    manifest_path = root / "manifest.json"
    manifest_payload = {
        "config": _serialize(config),
        "lineup_count": len(cross_play_result.get("lineups", {})),
        "agents": sorted(report.get("agent_performance_table", {}).keys()),
        "session_observation_count": len(session_observations),
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest_payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

    table_path = root / "agent_performance_table.csv"
    _write_agent_table(table_path, report.get("agent_performance_table", {}))

    observations_path = root / "session_observations.csv"
    _write_session_observations(observations_path, session_observations)

    cross_play_path = root / "cross_play_results.json"
    with cross_play_path.open("w", encoding="utf-8") as handle:
        json.dump(_serialize(report.get("cross_play_results", {})), handle, ensure_ascii=False, indent=2, sort_keys=True)

    logs_path = root / "session_logs.jsonl"
    all_logs = []
    for payload in cross_play_result.get("lineups", {}).values():
        all_logs.extend(payload["session"].get("logs", []))
    LogRecorder().dump_jsonl(all_logs, logs_path)

    artifact_paths = {
        "report": report_path,
        "manifest": manifest_path,
        "agent_table_csv": table_path,
        "session_observations_csv": observations_path,
        "cross_play_json": cross_play_path,
        "session_logs_jsonl": logs_path,
    }
    manifest_payload["artifacts"] = {
        name: {
            "path": str(path),
            "sha256": _sha256(path) if name != "manifest" else None,
        }
        for name, path in artifact_paths.items()
    }
    manifest_payload["environment"] = {
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest_payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

    return {
        name: str(path) for name, path in artifact_paths.items()
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_agent_table(path: Path, table: dict[str, dict[str, Any]]) -> None:
    fields = [
        "agent",
        "mean_profit",
        "cvar_5",
        "cvar_5_tail_size",
        "cvar_5_is_fallback",
        "cvar_5_low_support",
        "cvar_5_method",
        "cvar_5_effective_sample_size",
        "ruin_probability",
        "ruin_event_count",
        "variance",
        "win_rate",
        "profit_per_hand",
        "sample_count",
        "hands_survived",
        "session_completed_rate",
        "early_exit_rate",
        "forced_gwang_sell_rate",
        "showdown_frequency",
        "proposal_rate",
        "accept_rate",
        "reject_rate",
        "showdown_ev_gain",
        "showdown_misplay_rate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for agent_name, summary in table.items():
            row = {"agent": agent_name}
            row.update({field: summary.get(field, 0) for field in fields if field != "agent"})
            writer.writerow(row)


def _write_session_observations(path: Path, observations: list[dict[str, Any]]) -> None:
    fields = [
        "session_id",
        "layout_id",
        "layout_repeat",
        "layout",
        "seed",
        "seat",
        "agent",
        "model_id",
        "strategy_id",
        "strategy_label",
        "prompt_sha256",
        "factorial_block_id",
        "profit",
        "ruin",
        "win_rate",
        "total_hands",
        "hands_survived",
        "session_completed",
        "early_exit_rate",
        "showdown_frequency",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for observation in observations:
            writer.writerow({field: observation.get(field, "") for field in fields})
