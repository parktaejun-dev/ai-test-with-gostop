from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = Path(os.environ.get("GODORI_RUNTIME_DIR", REPO_ROOT / "dashboard" / ".runtime"))
JOBS_DIR = RUNTIME_DIR / "jobs"
PUBLIC_ROOT = Path(os.environ.get("GODORI_PUBLIC_ROOT", REPO_ROOT / "dashboard"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_job(job_id: str) -> dict:
    job_file = JOBS_DIR / f"{job_id}.json"
    return json.loads(job_file.read_text(encoding="utf-8"))


def write_job(job: dict) -> None:
    job["updated_at"] = utc_now()
    job_file = JOBS_DIR / f"{job['id']}.json"
    job_file.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def run_step(command: list[str], log_handle) -> None:
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}")


def build_eval_command(request_payload: dict) -> list[str]:
    output_dir = request_payload["output_dir"]
    mode = request_payload["mode"]
    if mode == "factorial":
        return [
            sys.executable,
            "-m",
            "experiments.openrouter_factorial_study",
            "--output-dir",
            output_dir,
        ]
    if mode == "series":
        return [
            sys.executable,
            "-m",
            "experiments.openrouter_family_eval",
            "--family",
            request_payload["family"],
            "--output-dir",
            output_dir,
        ]
    return [
        sys.executable,
        "-m",
        "experiments.openrouter_player_eval",
        "--seat-models",
        ",".join(request_payload["seat_models"]),
        "--output-dir",
        output_dir,
    ]


def publish_results(request_payload: dict, log_handle) -> None:
    run_name = request_payload["run_name"]
    output_dir = request_payload["output_dir"]
    runs_root = PUBLIC_ROOT / "data" / "runs"
    latest_dir = PUBLIC_ROOT / "data" / "latest"
    run_step(
        [
            sys.executable,
            "scripts/build_dashboard_data.py",
            "--results-dir",
            output_dir,
            "--run-name",
            run_name,
            "--dashboard-data-root",
            str(runs_root),
        ],
        log_handle,
    )
    run_step(
        [
            sys.executable,
            "scripts/build_dashboard_data.py",
            "--results-dir",
            output_dir,
            "--run-name",
            run_name,
            "--dashboard-data-dir",
            str(latest_dir),
        ],
        log_handle,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()

    job = read_job(args.job_id)
    job["status"] = "running"
    job["started_at"] = utc_now()
    write_job(job)

    log_path = Path(job["log_file"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with log_path.open("a", encoding="utf-8") as log_handle:
            log_handle.write(f"[{utc_now()}] start {job['request']['run_name']}\n")
            run_step(build_eval_command(job["request"]), log_handle)
            publish_results(job["request"], log_handle)
            log_handle.write(f"[{utc_now()}] completed {job['request']['run_name']}\n")
        job["status"] = "completed"
        job["completed_at"] = utc_now()
    except Exception as exc:  # noqa: BLE001
        with log_path.open("a", encoding="utf-8") as log_handle:
            log_handle.write(f"[{utc_now()}] failed {exc}\n")
        job["status"] = "failed"
        job["completed_at"] = utc_now()
        job["error"] = str(exc)
    write_job(job)


if __name__ == "__main__":
    main()
