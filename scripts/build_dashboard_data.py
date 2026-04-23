from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _parse_args():
    parser = argparse.ArgumentParser(description="Copy evaluation artifacts into dashboard data bundles.")
    parser.add_argument("--results-dir", default="")
    parser.add_argument("--results-root", default="")
    parser.add_argument("--run-name", default="")
    parser.add_argument("--dashboard-data-root", default="dashboard/data/runs")
    parser.add_argument("--dashboard-data-dir", default="")
    return parser.parse_args()


REQUIRED_FILES = [
    "report.json",
    "manifest.json",
    "cross_play_results.json",
    "session_logs.jsonl",
    "agent_performance_table.csv",
]

OPTIONAL_FILES = [
    "session_observations.csv",
]


def _copy_required(results_dir: Path, dashboard_dir: Path, run_name: str) -> dict:
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    copied = {}
    for name in REQUIRED_FILES:
        src = results_dir / name
        if not src.exists():
            raise FileNotFoundError(f"Missing artifact: {src}")
        dst = dashboard_dir / name
        shutil.copy2(src, dst)
        copied[name] = str(dst)

    for name in OPTIONAL_FILES:
        src = results_dir / name
        if not src.exists():
            continue
        dst = dashboard_dir / name
        shutil.copy2(src, dst)
        copied[name] = str(dst)

    index = {
        "run": run_name,
        "source_results_dir": str(results_dir),
        "files": copied,
    }
    (dashboard_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def _copy_single_run(results_dir: Path, data_root: Path, run_name: str) -> dict:
    return _copy_required(results_dir, data_root / run_name, run_name)


def _write_runs_index(data_root: Path) -> dict:
    runs = []
    if data_root.exists():
        for child in sorted(path for path in data_root.iterdir() if path.is_dir()):
            index_path = child / "index.json"
            if not index_path.exists():
                continue
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            runs.append(
                {
                    "name": child.name,
                    "label": child.name,
                    "source_results_dir": payload.get("source_results_dir", ""),
                    "files": payload.get("files", {}),
                }
            )
    index = {"runs": runs}
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def main() -> None:
    args = _parse_args()

    if args.dashboard_data_dir:
        if not args.results_dir:
            raise SystemExit("--dashboard-data-dir requires --results-dir")
        results_dir = Path(args.results_dir)
        dashboard_dir = Path(args.dashboard_data_dir)
        index = _copy_required(results_dir, dashboard_dir, args.run_name or results_dir.name)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return

    data_root = Path(args.dashboard_data_root)
    copied_runs = []

    if args.results_dir:
        results_dir = Path(args.results_dir)
        run_name = args.run_name or results_dir.name
        copied_runs.append(_copy_single_run(results_dir, data_root, run_name))
    elif args.results_root:
        results_root = Path(args.results_root)
        for child in sorted(path for path in results_root.iterdir() if path.is_dir()):
            try:
                copied_runs.append(_copy_single_run(child, data_root, child.name))
            except FileNotFoundError:
                continue
    else:
        raise SystemExit("Either --results-dir or --results-root is required")

    runs_index = _write_runs_index(data_root)
    print(json.dumps({"copied_runs": copied_runs, "runs_index": runs_index}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
