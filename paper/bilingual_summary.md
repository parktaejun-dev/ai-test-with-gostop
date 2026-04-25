# Bilingual Summary | 이중언어 요약

This paper package centers two remote-model Go-Stop evaluation panels collected from Qwen/DashScope and NVIDIA Build NIM.

이 논문 패키지는 Qwen/DashScope와 NVIDIA Build NIM에서 수집한 4인 고스톱 원격 모델 평가 두 패널을 중심에 둔다.

## Abstract | 초록

English:
The manuscript evaluates fixed remote LLM policies in a reproducible four-player Go-Stop harness. The first panel compares four Qwen-labeled DashScope models at 30B, 122B, 397B, and 480B nominal total parameters. The second panel compares four roughly 100B-122B NVIDIA Build models from Qwen, Mistral, Nemotron, and Stockmark under a one-call, one-hand constraint. Each panel enumerates all 24 seat permutations with two layout repetitions, producing 48 session samples per model and 192 model-session observations. The results are descriptive: the Qwen panel is not monotone in nominal parameter scale, and the constrained NVIDIA panel ranks Nemotron highest on mean profit and empirical CVaR. The paper does not claim a pure scale effect, a confirmatory family effect, or universal model rankings.

Korean:
원고는 재현 가능한 4인 고스톱 하네스에서 고정 원격 LLM 정책을 평가한다. 첫 번째 패널은 DashScope의 Qwen 계열 모델 4개를 30B, 122B, 397B, 480B 명목 총 파라미터 규모로 비교한다. 두 번째 패널은 NVIDIA Build의 Qwen, Mistral, Nemotron, Stockmark 모델 4개를 100B-122B 전후 규모에서 비교하되, 한 세션 한 손과 에이전트당 원격 호출 1회 제약을 둔다. 각 패널은 24개 좌석 순열을 모두 사용하고 레이아웃을 두 번 반복해 모델당 48개 세션 표본, 패널당 192개 모델-세션 관측치를 만든다. 결과는 기술통계다. Qwen 패널은 명목 파라미터 규모에 대해 단조적이지 않았고, 제한된 NVIDIA 패널에서는 Nemotron이 mean profit과 empirical CVaR 기준으로 가장 높게 관측되었다. 이 논문은 순수 scale effect, 확증적 family effect, 보편적 모델 순위를 주장하지 않는다.

## Main Reading Rule | 메인 읽기 규칙

English:
- Main paper question 1: observed monotonicity in the Qwen-labeled DashScope panel.
- Main paper question 2: descriptive cross-family differences in the constrained NVIDIA Build panel.
- Main result bundles:
  - `results/paper_qwen_4model_param_2h_2rep`
  - `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`
- Heuristic baseline artifacts are appendix calibration only.

Korean:
- 본문 질문 1: Qwen/DashScope 패널에서 관측 성능이 파라미터 규모에 대해 단조적인가.
- 본문 질문 2: 제한된 NVIDIA Build 패널에서 family별 기술통계 차이가 보이는가.
- 본문 결과 번들:
  - `results/paper_qwen_4model_param_2h_2rep`
  - `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`
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
