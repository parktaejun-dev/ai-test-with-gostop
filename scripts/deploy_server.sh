#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -z "${GOSTOP_DEPLOY_HOST:-}" ]]; then
  echo "GOSTOP_DEPLOY_HOST is required." >&2
  echo "Set it in environment (예: export GOSTOP_DEPLOY_HOST=your-ssh-target)." >&2
  exit 1
fi

DEPLOY_HOST="${GOSTOP_DEPLOY_HOST}"
DEPLOY_DIR="${GOSTOP_DEPLOY_DIR:-/home/ubuntu/projects/gostop_ai_evaluation}"
DEPLOY_KEY="${GOSTOP_DEPLOY_KEY:-}"
RUN_TESTS="${GOSTOP_RUN_TESTS:-0}"
DRY_RUN="${GOSTOP_DRY_RUN:-0}"

if [[ "${DRY_RUN}" == "1" ]]; then
  DRY_OPT="--dry-run"
else
  DRY_OPT=""
fi

SSH_OPTIONS=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o UserKnownHostsFile=/dev/null
  -o StrictHostKeyChecking=no
)

if [[ -n "${DEPLOY_KEY}" ]]; then
  SSH_OPTIONS+=( -i "${DEPLOY_KEY}" )
fi

printf '%s\n' "배포 대상: ${DEPLOY_HOST}:${DEPLOY_DIR}"
printf '%s\n' "동기화 모드: $([ "${DRY_RUN}" == "1" ] && echo "dry-run" || echo "실행")"

ssh "${SSH_OPTIONS[@]}" "${DEPLOY_HOST}" "mkdir -p ${DEPLOY_DIR}"

export RSYNC_RSH="ssh ${SSH_OPTIONS[*]}"
rsync -avz ${DRY_OPT} \
  --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude ".pytest_cache" \
  --exclude ".mypy_cache" \
  --exclude ".ruff_cache" \
  --exclude "__pycache__" \
  --exclude ".DS_Store" \
  --exclude "results" \
  --exclude "logs" \
  "${REPO_ROOT}/" \
  "${DEPLOY_HOST}:${DEPLOY_DIR}/"

if [[ "${RUN_TESTS}" == "1" ]]; then
  ssh "${SSH_OPTIONS[@]}" "${DEPLOY_HOST}" "cd ${DEPLOY_DIR} && python3 -m unittest -q"
fi

printf '%s\n' "배포 완료: ${DEPLOY_HOST}:${DEPLOY_DIR}"
