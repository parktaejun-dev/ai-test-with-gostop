# 산출물 안내 | Artifact Guide

한국어가 1순위, 영어가 2순위다. 공개 웹 페이지와 공개 PDF는 한국어 우선 이중언어 버전이다.

Korean is primary and English is secondary. The public web page and public PDF are Korean-first bilingual artifacts.

## 주 원고 | Main Manuscript

- 영어 학술 원고 소스 / English academic source: `paper/arxiv_main.tex`
- PDF 복사본 / PDF copy: `paper/arxiv_main.pdf`
- 공개 PDF / Public PDF: `paper/gostop_ai_evaluation_paper.pdf`
- 결과 요약 / Result summary: `paper/remote_model_results.md`
- 이중언어 요약 / Bilingual summary: `paper/bilingual_summary.md`
- 참고문헌 / Bibliography: `paper/refs.bib`
- 메인 결과 번들은 `paper/artifacts/`가 아니라 `results/` 아래에 있다.
- Main result bundles live under `results/`, not `paper/artifacts/`.
- `paper/artifacts/`에는 이전 calibration 번들이 남아 있을 수 있으므로 현재 본문 결과 번들로 해석하지 않는다.

## Qwen 파라미터 규모 번들 | Qwen Parameter-Scale Bundle

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

## NVIDIA 제한 동일 규모 family 번들 | NVIDIA Constrained Same-Scale Family Bundle

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

## 보조 NVIDIA 소형 모델 번들 | Supplementary NVIDIA Small-Model Bundle

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

## 보조 Qwen 소형 모델 정책 스크린 | Supplementary Qwen Small-Model Policy Screen

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

## 보조 NVIDIA 정책 스크린 | Supplementary NVIDIA Policy Screen

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

## arXiv 패키징 메모 | arXiv Packaging Note

arXiv TeX source package에는 전체 결과 디렉터리나 큰 JSONL 로그를 넣지 않는다. 컴파일에 필요한 파일만 넣는다.

Do not include full result directories or large JSONL logs in the arXiv TeX source package. The package should contain only files needed to compile the manuscript:

- `arxiv_main.tex`
- `refs.bib` or a generated `arxiv_main.bbl`

결과 디렉터리는 arXiv source에 묶지 않고 저장소 산출물로 참조한다.

The result directories should be referenced as repository artifacts, not bundled into arXiv source.
