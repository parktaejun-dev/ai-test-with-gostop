# Artifact Guide

This paper package now publishes two separate bundles.

## Main bundle
- Path roots:
  - `paper/artifacts/main/`
  - `paper/figures/main/`
  - `paper/tables/main/`
- Purpose:
  - factorial main paper bundle
  - consumed by `paper/arxiv_main.tex`
  - consumed by `dashboard/paper.html?bundle=main`
- Required files:
  - `report.json`
  - `manifest.json`
  - `agent_performance_table.csv`
  - `session_observations.csv`
  - `session_logs.jsonl`
  - `cross_play_results.json`
  - `paper_assets_manifest.json`
- Published figures:
  - `figure_factorial_interaction.png`
  - `figure_factorial_effect_sizes.png`
  - `figure_factorial_risk.png`
- Published tables:
  - `table_main_effects.csv`
  - `table_main_effects.tex`
- Extra reproducibility files:
  - `model_panel.json`
  - `prompt_strategies.json`
  - `prompts/*.txt`

## Appendix bundle
- Path roots:
  - `paper/artifacts/appendix/`
  - `paper/figures/appendix/`
  - `paper/tables/appendix/`
- Purpose:
  - heuristic baseline calibration bundle
  - consumed by `dashboard/paper.html?bundle=appendix`
- Published figures:
  - `figure_profit_ci.png`
  - `figure_risk_summary.png`
  - `figure_seat_heatmap.png`
- Published tables:
  - `table_main_metrics.csv`
  - `table_main_metrics.tex`

## Bundle index
- `paper/bundles/index.json` is the canonical registry for the paper viewer.
- It declares the default bundle, report path, manifest path, asset manifest path, and linked dashboard run.

## Join keys
- `session_observations.csv` is the main re-analysis table for the factorial bundle.
- Factorial-only columns:
  - `model_id`
  - `strategy_id`
  - `strategy_label`
  - `prompt_sha256`
  - `factorial_block_id`
- `factorial_block_id` aligns repeated-layout initial conditions across strategies.

## Checked-in status
- The repository currently ships `results/factorial_smoke` as the published main bundle because live OpenRouter credentials are not bundled.
- The same publishing path is used for real runs. Replacing the smoke bundle with a live pinned run does not require changing the paper or viewer contract.
