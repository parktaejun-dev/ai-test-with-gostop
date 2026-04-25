# Artifact Guide

This paper package now centers two remote-model result bundles.

## Main manuscript
- Source: `paper/arxiv_main.tex`
- Public PDF: `paper/gostop_ai_evaluation_paper.pdf`
- Summary: `paper/remote_model_results.md`
- Bibliography: `paper/refs.bib`

## Qwen parameter-scale bundle
- Path: `results/paper_qwen_4model_param_2h_2rep/`
- Purpose: Qwen-family parameter-scale comparison.
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
- Required files:
  - `manifest.json`
  - `report.json`
  - `agent_performance_table.csv`
  - `session_observations.csv`
  - `session_logs.jsonl`
  - `cross_play_results.json`

## NVIDIA same-scale family bundle
- Path: `results/paper_nvidia_120b_4model_family_1h_2rep_budget1/`
- Purpose: Same-scale cross-family comparison on NVIDIA Build NIM.
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
- Required files:
  - `manifest.json`
  - `report.json`
  - `agent_performance_table.csv`
  - `session_observations.csv`
  - `session_logs.jsonl`
  - `cross_play_results.json`

## arXiv packaging note
Do not include full result directories or large JSONL logs in the arXiv TeX source package.
The arXiv source package should contain only files needed to compile the manuscript:

- `arxiv_main.tex`
- `refs.bib` or a generated `arxiv_main.bbl`

The result directories should be referenced as repository artifacts, not bundled into arXiv source.
