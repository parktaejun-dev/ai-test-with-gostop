# Artifact Guide

This paper package now centers two remote-model result bundles.

## Main manuscript
- Source: `paper/arxiv_main.tex`
- PDF copy: `paper/arxiv_main.pdf`
- Generated bibliography: `paper/arxiv_main.bbl`
- Generated PDF, if present: `paper/gostop_ai_evaluation_paper.pdf` (regenerate after manuscript edits)
- Summary: `paper/remote_model_results.md`
- Bibliography: `paper/refs.bib`
- Main result bundles live under `results/`, not `paper/artifacts/`.
- `paper/artifacts/` may contain older heuristic calibration bundles and is not the current main-result source.

## Qwen parameter-scale bundle
- Path: `results/paper_qwen_4model_param_2h_2rep/`
- Purpose: Qwen-labeled parameter-scale comparison.
- Models:
  - `qwen3-coder-30b-a3b-instruct`
  - `qwen3.5-122b-a10b`
  - `qwen3.5-397b-a17b`
  - `qwen3-coder-480b-a35b-instruct`
- Configuration:
  - `session_hands=2`
  - `layout_repetitions=2`
  - `remote_eval_hands=2`
  - `sample_count=48` per model
  - CVaR effective 5% tail mass is 2.4 sessions per model
- Required files:
  - `manifest.json`
  - `report.json`
  - `agent_performance_table.csv`
  - `session_observations.csv`
  - `session_logs.jsonl`
  - `cross_play_results.json`

## NVIDIA constrained same-scale family bundle
- Path: `results/paper_nvidia_120b_4model_family_1h_2rep_budget1/`
- Purpose: Rate-limited roughly same-scale cross-family comparison on NVIDIA Build NIM.
- Models:
  - `qwen/qwen3.5-122b-a10b`
  - `mistralai/mistral-small-4-119b-2603`
  - `nvidia/nemotron-3-super-120b-a12b`
  - `stockmark/stockmark-2-100b-instruct`
- Configuration:
  - `session_hands=1`
  - `layout_repetitions=2`
  - `remote_eval_hands=1`
  - `max_remote_calls_per_agent=1`
  - `sample_count=48` per model
  - CVaR effective 5% tail mass is 2.4 sessions per model
- Required files:
  - `manifest.json`
  - `report.json`
  - `agent_performance_table.csv`
  - `session_observations.csv`
  - `session_logs.jsonl`
  - `cross_play_results.json`

## Supplementary NVIDIA small-model bundle
- Path: `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542/`
- Purpose: Small-model comparison under the same constrained NVIDIA Build setup.
- Models:
  - `ibm/granite-3.0-3b-a800m-instruct`
  - `meta/llama-3.2-1b-instruct`
  - `google/gemma-2-2b-it`
  - `microsoft/phi-4-mini-instruct`
- Configuration:
  - `session_hands=1`
  - `layout_repetitions=2`
  - `remote_eval_hands=1`
  - `max_remote_calls_per_agent=1`
  - `sample_count=48` per model

## Supplementary Qwen small-model policy screen
- Paths:
  - `results/policy_screen_qwen_tiny_balanced_1h_1rep_20260425_102731/`
  - `results/policy_screen_qwen_tiny_analytic_1h_1rep_20260425_102731/`
  - `results/policy_screen_qwen_tiny_conservative_1h_1rep_20260425_102731/`
  - `results/policy_screen_qwen_tiny_aggressive_1h_1rep_20260425_102731/`
- Purpose: Exploratory prompt-policy sensitivity for small Qwen models.
- Models:
  - `qwen3-1.7b`
  - `qwen3-4b`
  - `qwen3-8b`
  - `qwen3-14b`
- Configuration:
  - `session_hands=1`
  - `layout_repetitions=1`
  - `remote_eval_hands=1`
  - `sample_count=24` per model-policy cell

## Supplementary NVIDIA policy screen
- Paths:
  - `results/policy_screen_nvidia_balanced_1h_1rep_20260425_075542/`
  - `results/policy_screen_nvidia_analytic_1h_1rep_20260425_075542/`
  - `results/policy_screen_nvidia_conservative_1h_1rep_20260425_075542/`
  - `results/policy_screen_nvidia_aggressive_1h_1rep_20260425_075542/`
- Purpose: Exploratory prompt-policy sensitivity for the roughly same-scale NVIDIA Build panel.
- Models:
  - `qwen/qwen3.5-122b-a10b`
  - `mistralai/mistral-small-4-119b-2603`
  - `nvidia/nemotron-3-super-120b-a12b`
  - `stockmark/stockmark-2-100b-instruct`
- Configuration:
  - `session_hands=1`
  - `layout_repetitions=1`
  - `remote_eval_hands=1`
  - `max_remote_calls_per_agent=1`
  - `sample_count=24` per model-policy cell

## arXiv packaging note
Do not include full result directories or large JSONL logs in the arXiv TeX source package.
The arXiv source package should contain only files needed to compile the manuscript:

- `arxiv_main.tex`
- `refs.bib` or a generated `arxiv_main.bbl`

The result directories should be referenced as repository artifacts, not bundled into arXiv source.
