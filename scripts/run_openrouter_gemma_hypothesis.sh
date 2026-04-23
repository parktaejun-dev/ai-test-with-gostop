#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 scripts/run_openrouter_family_study.py \
  --family gemma \
  --base-seeds 7,11,13,17,19 \
  --output-dir results/openrouter_gemma_family_study
