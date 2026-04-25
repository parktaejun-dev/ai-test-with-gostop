# Bilingual Summary | 이중언어 요약

This paper package centers two main remote-model Go-Stop evaluation panels and supplementary small-model/policy screens collected from Qwen/DashScope and NVIDIA Build NIM.

이 논문 패키지는 Qwen/DashScope와 NVIDIA Build NIM에서 수집한 4인 고스톱 원격 모델 평가 주 패널 2개와 소형 모델/정책 보조 실험을 중심에 둔다.

## Abstract | 초록

English:
The manuscript evaluates fixed remote LLM policies in a reproducible four-player Go-Stop harness. Go-Stop is used as a compact stochastic decision environment with hidden information, uncertain draws, combinatorial scoring, stop-or-continue risk, and multi-agent interaction. The first main panel compares four Qwen-labeled DashScope models at 30B, 122B, 397B, and 480B nominal total parameters. The second main panel compares four roughly 100B-122B NVIDIA Build models from Qwen, Mistral, Nemotron, and Stockmark under a one-call, one-hand constraint. Supplementary screens compare small NVIDIA models and four prompt-policy framings. The results are descriptive: the Qwen panel is not monotone in nominal parameter scale, the constrained NVIDIA panel ranks Nemotron highest on mean profit and empirical CVaR, and policy effects are model-specific.

Korean:
원고는 재현 가능한 4인 고스톱 하네스에서 고정 원격 LLM 정책을 평가한다. 고스톱은 숨은 정보, 불확실한 드로우, 조합적 점수 계산, 고/스톱 위험, 다중 에이전트 상호작용이 짧은 에피소드 안에 들어 있는 확률적 의사결정 환경으로 사용된다. 첫 번째 주 패널은 DashScope의 Qwen 계열 모델 4개를 30B, 122B, 397B, 480B 명목 총 파라미터 규모로 비교한다. 두 번째 주 패널은 NVIDIA Build의 Qwen, Mistral, Nemotron, Stockmark 모델 4개를 100B-122B 전후 규모에서 비교하되, 한 세션 한 손과 에이전트당 원격 호출 1회 제약을 둔다. 보조 실험은 NVIDIA 소형 모델과 네 가지 prompt-policy framing을 비교한다. 결과는 기술통계다. Qwen 패널은 명목 파라미터 규모에 대해 단조적이지 않았고, 제한된 NVIDIA 패널에서는 Nemotron이 mean profit과 empirical CVaR 기준으로 가장 높았으며, 정책 효과는 모델별로 다르게 나타났다.

## Main Reading Rule | 메인 읽기 규칙

English:
- RQ1: Go-Stop as a compact risk-sensitive sequential decision environment.
- RQ2: observed monotonicity in the Qwen-labeled DashScope panel.
- RQ3: descriptive cross-family differences in the constrained NVIDIA Build panel.
- RQ4: exploratory small-model and policy-framing effects.
- Main result bundles:
  - `results/paper_qwen_4model_param_2h_2rep`
  - `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`
- Supplementary result bundles:
  - `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542`
  - `results/policy_screen_qwen_tiny_*_1h_1rep_20260425_102731`
  - `results/policy_screen_nvidia_*_1h_1rep_20260425_075542`
- Heuristic baseline artifacts are appendix calibration only.

Korean:
- RQ1: 고스톱을 위험 민감적 순차 의사결정 평가 환경으로 볼 수 있는가.
- RQ2: Qwen/DashScope 패널에서 관측 성능이 파라미터 규모에 대해 단조적인가.
- RQ3: 제한된 NVIDIA Build 패널에서 family별 기술통계 차이가 보이는가.
- RQ4: 소형 모델과 정책 framing 효과가 탐색적으로 관찰되는가.
- 본문 결과 번들:
  - `results/paper_qwen_4model_param_2h_2rep`
  - `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`
- 보조 결과 번들:
  - `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542`
  - `results/policy_screen_qwen_tiny_*_1h_1rep_20260425_102731`
  - `results/policy_screen_nvidia_*_1h_1rep_20260425_075542`
- 휴리스틱 baseline 산출물은 appendix calibration 전용이다.

## Artifact Reminder | 아티팩트 안내

English:
- `paper/arxiv_main.tex`: manuscript source.
- `paper/remote_model_results.md`: compact result summary.
- `paper/ARTIFACTS.md`: artifact guide.
- Main result directories are under `results/`, not `paper/artifacts/`.
- `paper/artifacts/` may contain older calibration bundles and should not be treated as the current main result bundle.

Korean:
- `paper/arxiv_main.tex`: 본문 소스.
- `paper/remote_model_results.md`: 압축 결과 요약.
- `paper/ARTIFACTS.md`: 산출물 안내.
- 메인 결과 디렉터리는 `paper/artifacts/`가 아니라 `results/` 아래에 있다.
- `paper/artifacts/`에는 이전 calibration 번들이 남아 있을 수 있으므로 현재 본문 결과 번들로 해석하지 않는다.
