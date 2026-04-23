#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

python3 main.py \
  --initial-bankroll 1000 \
  --stake-per-point 1 \
  --output-dir results/paper_baseline
