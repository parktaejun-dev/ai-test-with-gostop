from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER_ROOT = REPO_ROOT / "paper"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish results bundles into paper/ for the manuscript and archive viewer.")
    parser.add_argument("--main-results-dir", required=True)
    parser.add_argument("--appendix-results-dir", required=True)
    return parser.parse_args()


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run_figure_builder(results_dir: Path, output_dir: Path) -> dict:
    ensure_clean_dir(output_dir)
    command = [
        sys.executable,
        "scripts/build_paper_figures.py",
        "--results-dir",
        str(results_dir),
        "--output-dir",
        str(output_dir),
    ]
    completed = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def copy_results_artifacts(results_dir: Path, artifacts_dir: Path) -> list[dict[str, str]]:
    artifact_links = []
    for name in [
        "report.json",
        "manifest.json",
        "agent_performance_table.csv",
        "session_observations.csv",
        "session_logs.jsonl",
        "cross_play_results.json",
    ]:
        src = results_dir / name
        if not src.exists():
            continue
        dst = artifacts_dir / name
        shutil.copy2(src, dst)
        artifact_links.append({"label": name, "path": f"../paper/artifacts/{artifacts_dir.name}/{name}"})
    return artifact_links


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def write_csv_as_tex(csv_path: Path, tex_path: Path) -> None:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    headers = rows[0].keys() if rows else []
    column_spec = "l" + "r" * (len(list(headers)) - 1)
    lines = [f"\\begin{{tabular}}{{{column_spec}}}", "\\toprule", " & ".join(headers) + r" \\", "\\midrule"]
    for row in rows:
        values = [str(row[key]) for key in headers]
        lines.append(" & ".join(values) + r" \\")
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    tex_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def publish_bundle(bundle_id: str, results_dir: Path, label: str) -> dict:
    artifacts_dir = PAPER_ROOT / "artifacts" / bundle_id
    figures_dir = PAPER_ROOT / "figures" / bundle_id
    tables_dir = PAPER_ROOT / "tables" / bundle_id
    assets_dir = PAPER_ROOT / ".bundle_build" / bundle_id

    ensure_clean_dir(artifacts_dir)
    ensure_clean_dir(figures_dir)
    ensure_clean_dir(tables_dir)

    manifest = json.loads((results_dir / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((results_dir / "report.json").read_text(encoding="utf-8"))
    asset_payload = run_figure_builder(results_dir, assets_dir)
    artifact_links = copy_results_artifacts(results_dir, artifacts_dir)

    figures = []
    tables = []
    for item in sorted(assets_dir.iterdir()):
        if item.name == "paper_assets_manifest.json":
            continue
        if item.suffix.lower() == ".png":
            dst = figures_dir / item.name
            shutil.copy2(item, dst)
            figures.append({
                "key": item.stem,
                "title": figure_title(item.stem),
                "caption": figure_caption(item.stem),
                "path": f"../paper/figures/{bundle_id}/{item.name}",
            })
            artifact_links.append({"label": item.name, "path": f"../paper/figures/{bundle_id}/{item.name}"})
        elif item.suffix.lower() == ".csv":
            dst = tables_dir / item.name
            shutil.copy2(item, dst)
            tables.append({
                "key": item.stem,
                "title": item.name,
                "path": f"../paper/tables/{bundle_id}/{item.name}",
            })
            artifact_links.append({"label": item.name, "path": f"../paper/tables/{bundle_id}/{item.name}"})
            tex_path = tables_dir / f"{item.stem}.tex"
            write_csv_as_tex(dst, tex_path)
            artifact_links.append({"label": tex_path.name, "path": f"../paper/tables/{bundle_id}/{tex_path.name}"})

    extra_sources = {"report": str(results_dir / "report.json"), "session_observations": str(results_dir / "session_observations.csv")}
    if manifest.get("config", {}).get("model_panel"):
        model_panel_path = artifacts_dir / "model_panel.json"
        write_json(model_panel_path, {"model_panel": manifest["config"].get("model_panel", [])})
        artifact_links.append({"label": model_panel_path.name, "path": f"../paper/artifacts/{bundle_id}/{model_panel_path.name}"})
    if manifest.get("config", {}).get("prompt_strategies"):
        prompt_meta_path = artifacts_dir / "prompt_strategies.json"
        write_json(prompt_meta_path, {"prompt_strategies": manifest["config"].get("prompt_strategies", [])})
        artifact_links.append({"label": prompt_meta_path.name, "path": f"../paper/artifacts/{bundle_id}/{prompt_meta_path.name}"})
        prompts_dir = artifacts_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        for item in manifest["config"].get("prompt_strategies", []):
            src = Path(item.get("path", ""))
            if not src.exists():
                continue
            dst = prompts_dir / f"{item.get('strategy_id', src.stem)}.txt"
            shutil.copy2(src, dst)
            artifact_links.append({"label": f"prompts/{dst.name}", "path": f"../paper/artifacts/{bundle_id}/prompts/{dst.name}"})

    normalized_asset_manifest = {
        "bundle_id": bundle_id,
        "bundle_label": label,
        "study_type": report.get("study_type", "baseline"),
        "source_results_dir": str(results_dir),
        "figures": figures,
        "tables": tables,
        "artifact_links": artifact_links,
        "sources": extra_sources,
    }
    write_json(artifacts_dir / "paper_assets_manifest.json", normalized_asset_manifest)

    return {
        "label": label,
        "study_type": report.get("study_type", "baseline"),
        "run_name": results_dir.name,
        "source_results_dir": str(results_dir),
        "dashboard_run": results_dir.name,
        "report_path": f"../paper/artifacts/{bundle_id}/report.json",
        "manifest_path": f"../paper/artifacts/{bundle_id}/manifest.json",
        "asset_manifest_path": f"../paper/artifacts/{bundle_id}/paper_assets_manifest.json",
    }


def figure_title(key: str) -> str:
    mapping = {
        "figure_factorial_interaction": "Figure 1. Model-by-strategy interaction",
        "figure_factorial_effect_sizes": "Figure 2. Main-effect comparison",
        "figure_factorial_risk": "Figure 3. Secondary risk summaries",
        "figure_profit_ci": "Figure A1. Profit difference vs baseline",
        "figure_risk_summary": "Figure A2. Baseline-relative risk summary",
        "figure_seat_heatmap": "Figure A3. Seat effect heatmap",
    }
    return mapping.get(key, key)


def figure_caption(key: str) -> str:
    mapping = {
        "figure_factorial_interaction": "Mean session profit by model with one line per prompt strategy.",
        "figure_factorial_effect_sizes": "Partial eta-squared for model, strategy, and interaction.",
        "figure_factorial_risk": "Model- and strategy-marginal CVaR and ruin summaries.",
        "figure_profit_ci": "Baseline-relative mean profit with bootstrap intervals.",
        "figure_risk_summary": "Baseline-relative risk differences.",
        "figure_seat_heatmap": "Mean profit by seat.",
    }
    return mapping.get(key, key)


def main() -> None:
    args = parse_args()
    bundles_dir = PAPER_ROOT / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    main_bundle = publish_bundle("main", Path(args.main_results_dir), "Main factorial bundle")
    appendix_bundle = publish_bundle("appendix", Path(args.appendix_results_dir), "Appendix calibration bundle")
    index = {
        "default_bundle": "main",
        "bundles": {
            "main": main_bundle,
            "appendix": appendix_bundle,
        },
    }
    write_json(bundles_dir / "index.json", index)
    print(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
