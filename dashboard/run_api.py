from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = Path(os.environ.get("GODORI_RUNTIME_DIR", REPO_ROOT / "dashboard" / ".runtime"))
JOBS_DIR = RUNTIME_DIR / "jobs"
LOGS_DIR = RUNTIME_DIR / "logs"
RESULTS_ROOT = Path(os.environ.get("GODORI_RESULTS_ROOT", REPO_ROOT / "results"))
PUBLIC_ROOT = Path(os.environ.get("GODORI_PUBLIC_ROOT", REPO_ROOT / "dashboard"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, fallback: str = "run") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def make_run_name(payload: dict) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = str(payload.get("mode") or "series").strip()
    if mode == "factorial":
        return f"openrouter_factorial_{stamp}"
    if mode == "series":
        family = slugify(str(payload.get("family") or "family"), "family")
        return f"openrouter_family_{family}_{stamp}"
    seat_models = payload.get("seat_models") or []
    lead = slugify(str(seat_models[0] if seat_models else "player"), "player")
    return f"openrouter_player_{lead}_{stamp}"


def read_job(job_id: str) -> dict | None:
    job_file = JOBS_DIR / f"{job_id}.json"
    if not job_file.exists():
        return None
    return json.loads(job_file.read_text(encoding="utf-8"))


def write_job(job: dict) -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    job["updated_at"] = utc_now()
    job_file = JOBS_DIR / f"{job['id']}.json"
    job_file.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def running_job() -> dict | None:
    if not JOBS_DIR.exists():
        return None
    for job_file in sorted(JOBS_DIR.glob("*.json"), reverse=True):
        payload = json.loads(job_file.read_text(encoding="utf-8"))
        if payload.get("status") in {"queued", "running"}:
            return payload
    return None


def validate_origin(headers) -> bool:
    origin = headers.get("Origin")
    host = headers.get("Host")
    if not origin or not host:
        return True
    parsed = urlparse(origin)
    return parsed.netloc == host


def parse_payload(raw: bytes) -> tuple[dict, dict]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("JSON 본문이 아니다.") from exc

    if not isinstance(payload, dict):
        raise ValueError("JSON 객체만 받을 수 있다.")

    mode = str(payload.get("mode") or "series").strip()
    if mode not in {"series", "manual", "random", "factorial"}:
        raise ValueError("지원하지 않는 실행 모드다.")

    api_key = str(payload.get("api_key") or os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY가 비어 있다.")

    family = str(payload.get("family") or "").strip()
    seat_models = payload.get("seat_models") or []
    if mode == "series":
        if not family:
            raise ValueError("family가 비어 있다.")
    elif mode in {"manual", "random"}:
        if not isinstance(seat_models, list) or len(seat_models) != 4:
            raise ValueError("seat_models는 4개여야 한다.")
        seat_models = [str(item).strip() for item in seat_models]
        if not all(seat_models):
            raise ValueError("seat_models에 빈 값이 있다.")
    else:
        seat_models = []

    run_name = make_run_name({"mode": mode, "family": family, "seat_models": seat_models})
    output_dir = RESULTS_ROOT / run_name
    log_file = LOGS_DIR / f"{run_name}.log"

    job_request = {
        "mode": mode,
        "family": family,
        "seat_models": seat_models,
        "run_name": run_name,
        "output_dir": str(output_dir),
        "base_url": str(payload.get("base_url") or "https://openrouter.ai/api/v1").strip(),
        "referer": str(payload.get("referer") or "").strip(),
        "app_title": str(payload.get("app_title") or "").strip(),
        "selector_url": str(payload.get("selector_url") or "").strip(),
    }

    worker_env = {
        "OPENROUTER_API_KEY": api_key,
        "OPENROUTER_BASE_URL": job_request["base_url"],
        "OPENROUTER_HTTP_REFERER": job_request["referer"],
        "OPENROUTER_APP_TITLE": job_request["app_title"],
    }
    selector_token = str(payload.get("selector_token") or "").strip()
    if job_request["selector_url"]:
        worker_env["OPENROUTER_SELECTOR_URL"] = job_request["selector_url"]
    if selector_token:
        worker_env["OPENROUTER_SELECTOR_TOKEN"] = selector_token

    job = {
        "id": uuid.uuid4().hex,
        "status": "queued",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "request": job_request,
        "log_file": str(log_file),
        "dashboard_url": f"/index.html?run={run_name}",
    }
    return job, worker_env


class Handler(BaseHTTPRequestHandler):
    server_version = "GodoriRunAPI/0.1"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.write_json(HTTPStatus.OK, {"ok": True})
            return

        if self.path.startswith("/api/jobs/"):
            job_id = self.path.removeprefix("/api/jobs/").strip("/")
            if job_id.endswith("/log"):
                job_id = job_id.removesuffix("/log")
                job = read_job(job_id)
                if not job:
                    self.write_json(HTTPStatus.NOT_FOUND, {"error": "job not found"})
                    return
                log_path = Path(job["log_file"])
                if not log_path.exists():
                    self.write_plain(HTTPStatus.OK, "")
                    return
                self.write_plain(HTTPStatus.OK, log_path.read_text(encoding="utf-8", errors="replace"))
                return

            job = read_job(job_id)
            if not job:
                self.write_json(HTTPStatus.NOT_FOUND, {"error": "job not found"})
                return
            self.write_json(HTTPStatus.OK, job)
            return

        self.write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/api/run":
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        if not validate_origin(self.headers):
            self.write_json(HTTPStatus.FORBIDDEN, {"error": "origin mismatch"})
            return

        active = running_job()
        if active:
            self.write_json(
                HTTPStatus.CONFLICT,
                {
                    "error": "already running",
                    "job_id": active["id"],
                    "status": active["status"],
                    "dashboard_url": active.get("dashboard_url", ""),
                },
            )
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            job, worker_env = parse_payload(self.rfile.read(length))
        except ValueError as exc:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
        write_job(job)

        log_handle = Path(job["log_file"]).open("a", encoding="utf-8")
        env = os.environ.copy()
        env.update(worker_env)
        env["GODORI_RUNTIME_DIR"] = str(RUNTIME_DIR)
        env["GODORI_RESULTS_ROOT"] = str(RESULTS_ROOT)
        env["GODORI_PUBLIC_ROOT"] = str(PUBLIC_ROOT)
        worker = subprocess.Popen(
            [sys.executable, str(REPO_ROOT / "dashboard" / "run_worker.py"), "--job-id", job["id"]],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log_handle.close()
        job["worker_pid"] = worker.pid
        write_job(job)
        self.write_json(
            HTTPStatus.ACCEPTED,
            {
                "job_id": job["id"],
                "run_name": job["request"]["run_name"],
                "status": job["status"],
                "dashboard_url": job["dashboard_url"],
            },
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def write_json(self, status: HTTPStatus, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def write_plain(self, status: HTTPStatus, text: str) -> None:
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    host = os.environ.get("GODORI_API_HOST", "127.0.0.1")
    port = int(os.environ.get("GODORI_API_PORT", "3220"))
    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
