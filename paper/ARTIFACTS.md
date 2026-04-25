# 산출물 안내 | Artifact Guide

## 한국어

### 주 원고

- 영어 학술 원고 소스: `paper/arxiv_main.tex`
- PDF 복사본: `paper/arxiv_main.pdf`
- 공개 PDF: `paper/gostop_ai_evaluation_paper.pdf`
- 결과 요약: `paper/remote_model_results.md`
- 이중언어 요약: `paper/bilingual_summary.md`
- 참고문헌: `paper/refs.bib`
- 메인 결과 번들은 `paper/artifacts/`가 아니라 `results/` 아래에 있다.
- `paper/artifacts/`에는 이전 calibration 번들이 남아 있을 수 있으므로 현재 본문 결과 번들로 해석하지 않는다.

### 주 결과 번들

- Qwen 파라미터 규모 번들: `results/paper_qwen_4model_param_2h_2rep/`
  - 모델당 48 표본
  - `session_hands=2`
  - `layout_repetitions=2`
  - `remote_eval_hands=2`
- NVIDIA 제한 동일 규모 family 번들: `results/paper_nvidia_120b_4model_family_1h_2rep_budget1/`
  - 모델당 48 표본
  - `session_hands=1`
  - `layout_repetitions=2`
  - `remote_eval_hands=1`
  - `max_remote_calls_per_agent=1`

### 보조 결과 번들

- NVIDIA 소형 모델 번들: `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542/`
  - 모델당 48 표본
  - `max_remote_calls_per_agent=1`
- Qwen 소형 모델 정책 스크린: `results/policy_screen_qwen_tiny_*_1h_1rep_20260425_102731/`
  - model-policy cell당 24 표본
- NVIDIA 정책 스크린: `results/policy_screen_nvidia_*_1h_1rep_20260425_075542/`
  - model-policy cell당 24 표본
  - `max_remote_calls_per_agent=1`

### arXiv 패키징 메모

arXiv TeX source package에는 전체 결과 디렉터리나 큰 JSONL 로그를 넣지 않는다. 컴파일에 필요한 `arxiv_main.tex`와 `refs.bib` 또는 생성된 `arxiv_main.bbl`만 넣는다. 결과 디렉터리는 저장소 산출물로 참조한다.

## English

### Main Manuscript

- English academic source: `paper/arxiv_main.tex`
- PDF copy: `paper/arxiv_main.pdf`
- Public PDF: `paper/gostop_ai_evaluation_paper.pdf`
- Result summary: `paper/remote_model_results.md`
- Bilingual summary: `paper/bilingual_summary.md`
- Bibliography: `paper/refs.bib`
- Main result bundles live under `results/`, not `paper/artifacts/`.
- `paper/artifacts/` may contain older calibration bundles and should not be treated as the current main-result source.

### Main Result Bundles

- Qwen parameter-scale bundle: `results/paper_qwen_4model_param_2h_2rep/`
  - 48 samples per model
  - `session_hands=2`
  - `layout_repetitions=2`
  - `remote_eval_hands=2`
- NVIDIA constrained same-scale family bundle: `results/paper_nvidia_120b_4model_family_1h_2rep_budget1/`
  - 48 samples per model
  - `session_hands=1`
  - `layout_repetitions=2`
  - `remote_eval_hands=1`
  - `max_remote_calls_per_agent=1`

### Supplementary Result Bundles

- NVIDIA small-model bundle: `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542/`
  - 48 samples per model
  - `max_remote_calls_per_agent=1`
- Qwen small-model policy screen: `results/policy_screen_qwen_tiny_*_1h_1rep_20260425_102731/`
  - 24 samples per model-policy cell
- NVIDIA policy screen: `results/policy_screen_nvidia_*_1h_1rep_20260425_075542/`
  - 24 samples per model-policy cell
  - `max_remote_calls_per_agent=1`

### arXiv Packaging Note

Do not include full result directories or large JSONL logs in the arXiv TeX source package. Include only `arxiv_main.tex` and `refs.bib` or a generated `arxiv_main.bbl`. Result directories should be referenced as repository artifacts.
